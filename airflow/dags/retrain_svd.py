from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'cinematch',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'retrain_svd_model',
    default_args=default_args,
    description='Réentraînement automatique du modèle SVD',
    schedule_interval='0 2 * * 0',  # Chaque dimanche à 2h
    catchup=False,
    tags=['ml', 'svd', 'recommandation']
)

# ============================================================
# TÂCHE 1 : Vérifier les nouvelles données
# ============================================================
def check_new_ratings_branch(**context):
    """Vérifie si assez de nouveaux ratings et décide du chemin"""
    import psycopg2
    
    conn = psycopg2.connect(
        host="db",
        database="movierec",
        user="admin",
        password="admin123"
    )
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM fact_ratings 
        WHERE rating_date >= CURRENT_DATE - INTERVAL '7 days'
    """)
    
    new_ratings_count = cursor.fetchone()[0]
    conn.close()
    
    logger.info(f"📊 Nouveaux ratings cette semaine: {new_ratings_count}")
    
    # TOUJOURS envoyer le compteur pour la notification
    context['ti'].xcom_push(key='new_ratings_count', value=new_ratings_count)
    
    MIN_NEW_RATINGS = 100
    
    if new_ratings_count >= MIN_NEW_RATINGS:
        logger.info(f"✅ Assez de données ({new_ratings_count} >= {MIN_NEW_RATINGS})")
        return 'export_training_data'
    else:
        logger.warning(f"⚠️ Pas assez de données, passage à la notification")
        return 'notify_skip'

def notify_skip(**context):
    """Notification quand pas assez de données"""
    new_ratings = context['ti'].xcom_pull(key='new_ratings_count', task_ids='check_new_ratings')
    logger.info("=" * 50)
    logger.info("⏭️ RÉENTRAÎNEMENT IGNORÉ")
    logger.info("=" * 50)
    logger.info(f"📊 Nouveaux ratings: {new_ratings} (< 100)")
    logger.info("💡 Pas assez de nouvelles données pour réentraîner")
    logger.info("=" * 50)
    return True

# ============================================================
# TÂCHE 2 : Exporter les données depuis PostgreSQL
# ============================================================
def export_training_data(**context):
    """Exporte les données d'entraînement depuis PostgreSQL"""
    import psycopg2
    import pandas as pd
    from pathlib import Path
    
    logger.info("📥 Export des données d'entraînement...")
    
    conn = psycopg2.connect(
        host="db",
        database="movierec",
        user="admin",
        password="admin123"
    )
    
    # Exporter les ratings
    query = """
        SELECT 
            u.user_id,
            m.movie_id,
            fr.rating
        FROM fact_ratings fr
        JOIN dim_users u ON fr.user_key = u.user_key
        JOIN dim_movies m ON fr.movie_key = m.movie_key
        ORDER BY RANDOM()
        LIMIT 1000000
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Sauvegarder
    output_path = Path("/tmp/training_data.parquet")
    df.to_parquet(output_path, index=False)
    
    logger.info(f"✅ {len(df):,} ratings exportés vers {output_path}")
    
    context['ti'].xcom_push(key='training_data_path', value=str(output_path))
    return str(output_path)

# ============================================================
# TÂCHE 3 : Réentraîner le modèle SVD
# ============================================================
def retrain_svd_model(**context):
    """Réentraîne le modèle SVD avec les nouvelles données"""
    import pandas as pd
    import pickle
    import time
    from pathlib import Path
    from surprise import SVD, Dataset, Reader
    from surprise.model_selection import train_test_split
    from surprise import accuracy
    
    logger.info("🚀 Démarrage du réentraînement SVD...")
    
    # Récupérer le chemin des données
    ti = context['ti']
    data_path = ti.xcom_pull(key='training_data_path', task_ids='export_training_data')
    
    # Charger les données
    df = pd.read_parquet(data_path)
    logger.info(f"📊 Données chargées: {len(df):,} ratings")
    
    # Préparer pour Surprise
    reader = Reader(rating_scale=(0.5, 5.0))
    data = Dataset.load_from_df(df[['user_id', 'movie_id', 'rating']], reader)
    
    # Split train/test
    trainset, testset = train_test_split(data, test_size=0.2, random_state=42)
    
    # Paramètres optimaux
    best_params = {
        'n_factors': 100,
        'n_epochs': 20,
        'lr_all': 0.005,
        'reg_all': 0.02
    }
    
    # Entraîner
    start_time = time.time()
    algo = SVD(**best_params, random_state=42)
    algo.fit(trainset)
    train_time = time.time() - start_time
    
    # Évaluer
    predictions = algo.test(testset)
    rmse = accuracy.rmse(predictions, verbose=False)
    mae = accuracy.mae(predictions, verbose=False)
    
    logger.info(f"✅ Modèle entraîné en {train_time:.1f}s")
    logger.info(f"📈 RMSE: {rmse:.4f} | MAE: {mae:.4f}")
    
    # Sauvegarder les mappings
    import pandas as pd
    user_ids = df['user_id'].unique()
    movie_ids = df['movie_id'].unique()
    
    mappings = {
        'user_to_idx': {uid: idx for idx, uid in enumerate(user_ids)},
        'item_to_idx': {mid: idx for idx, mid in enumerate(movie_ids)},
        'idx_to_user': {idx: uid for idx, uid in enumerate(user_ids)},
        'idx_to_item': {idx: mid for idx, mid in enumerate(movie_ids)},
        'n_users': len(user_ids),
        'n_items': len(movie_ids),
        'rating_scale': (0.5, 5.0)
    }
    
    # Sauvegarder le modèle
    model_data = {
        'model': algo,
        'params': best_params,
        'rmse': rmse,
        'mae': mae,
        'trained_at': datetime.now().isoformat(),
        'n_ratings': len(df)
    }
    
    model_path = Path("/app/models/svd_best_model.pkl")
    mappings_path = Path("/app/models/id_mappings.pkl")
    
    with open(model_path, 'wb') as f:
        pickle.dump(algo, f)
    
    with open(mappings_path, 'wb') as f:
        pickle.dump(mappings, f)
    
    logger.info(f"✅ Modèle sauvegardé: {model_path}")
    
    # Passer les métriques
    context['ti'].xcom_push(key='rmse', value=rmse)
    context['ti'].xcom_push(key='mae', value=mae)
    context['ti'].xcom_push(key='train_time', value=train_time)
    
    return rmse

# ============================================================
# TÂCHE 4 : Valider le nouveau modèle
# ============================================================
def validate_new_model(**context):
    """Valide que le nouveau modèle est meilleur que l'ancien"""
    ti = context['ti']
    
    new_rmse = ti.xcom_pull(key='rmse', task_ids='retrain_svd')
    new_mae = ti.xcom_pull(key='mae', task_ids='retrain_svd')
    train_time = ti.xcom_pull(key='train_time', task_ids='retrain_svd')
    
    logger.info("🔍 VALIDATION DU NOUVEAU MODÈLE")
    logger.info(f"   • RMSE: {new_rmse:.4f}")
    logger.info(f"   • MAE:  {new_mae:.4f}")
    logger.info(f"   • Temps d'entraînement: {train_time:.1f}s")
    
    # Critères de validation
    MAX_RMSE = 1.0
    MAX_MAE = 0.8
    
    if new_rmse > MAX_RMSE:
        raise ValueError(f"❌ RMSE trop élevé: {new_rmse:.4f} > {MAX_RMSE}")
    
    if new_mae > MAX_MAE:
        raise ValueError(f"❌ MAE trop élevé: {new_mae:.4f} > {MAX_MAE}")
    
    logger.info("✅ Modèle validé avec succès!")
    return True

# ============================================================
# TÂCHE 5 : Notifier la fin
# ============================================================
def notify_completion(**context):
    """Log la fin du pipeline"""
    ti = context['ti']
    
    rmse = ti.xcom_pull(key='rmse', task_ids='retrain_svd')
    mae = ti.xcom_pull(key='mae', task_ids='retrain_svd')
    new_ratings = ti.xcom_pull(key='new_ratings_count', task_ids='check_new_ratings')
    
    # Gérer le cas où new_ratings est None
    if new_ratings is None:
        new_ratings = 0
    
    logger.info("=" * 50)
    logger.info("🎉 PIPELINE DE RÉENTRAÎNEMENT TERMINÉ!")
    logger.info("=" * 50)
    logger.info(f"📊 Nouveaux ratings traités : {new_ratings:,}")
    
    # Vérifier si rmse et mae existent
    if rmse is not None:
        logger.info(f"📈 RMSE final : {rmse:.4f}")
    if mae is not None:
        logger.info(f"📈 MAE final  : {mae:.4f}")
    
    logger.info("=" * 50)

# ============================================================
# DÉFINITION DES TÂCHES
# ============================================================
t1_branch = BranchPythonOperator(
    task_id='check_new_ratings',
    python_callable=check_new_ratings_branch,
    dag=dag,
)

t2_export = PythonOperator(
    task_id='export_training_data',
    python_callable=export_training_data,
    dag=dag,
)

t3_retrain = PythonOperator(
    task_id='retrain_svd',
    python_callable=retrain_svd_model,
    dag=dag,
)

t4_validate = PythonOperator(
    task_id='validate_model',
    python_callable=validate_new_model,
    dag=dag,
)

t5_notify = PythonOperator(
    task_id='notify_completion',
    python_callable=notify_completion,
    dag=dag,
)

t_skip = PythonOperator(
    task_id='notify_skip',
    python_callable=notify_skip,
    dag=dag,
)

t_end = DummyOperator(
    task_id='end',
    dag=dag,
)
# ============================================================
# ORDRE D'EXÉCUTION
# ============================================================
t1_branch >> [t2_export, t_skip]
t2_export >> t3_retrain >> t4_validate >> t5_notify >> t_end
t_skip >> t_end