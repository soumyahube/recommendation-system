import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import psycopg2
import pyarrow as pa
import pyarrow.parquet as pq

def export_ratings_cursor():
    """Export avec curseur serveur - OPTIMAL pour grandes tables"""
    
    print("🚀 Export fact_ratings avec curseur serveur")
    print("=" * 60)
    
    # 1. Connexion directe psycopg2 (pas SQLAlchemy)
    conn = psycopg2.connect(
        host="localhost",
        database="movierec",
        user="admin",
        password="admin123"
    )
    
    # 2. Créer dossier
    output_dir = Path("data/processed/parquet_export")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Curseur nommé (côté serveur - ne charge pas tout en mémoire)
    cursor = conn.cursor(name='fetch_large_result')
    
    # 4. Paramètres
    batch_size = 100000  # 100K lignes par batch
    batch_num = 0
    total_exported = 0
    
    print(f"📊 Configuration:")
    print(f"   • Batch size: {batch_size:,} lignes")
    print(f"   • Connexion: psycopg2 avec curseur serveur\n")
    
    try:
        # 5. Exécuter la requête (SANS charger tout en mémoire)
        cursor.execute("SELECT * FROM fact_ratings ORDER BY rating_id")
        
        # 6. Récupérer les noms de colonnes
        column_names = [desc[0] for desc in cursor.description]
        print(f"   • Colonnes: {column_names}\n")
        
        # 7. Lire par lots
        print("⏳ Lecture et export en cours...\n")
        
        while True:
            # Récupérer un lot
            rows = cursor.fetchmany(batch_size)
            
            # Si plus de données, stop
            if not rows:
                print(f"\n✅ Fin de la lecture - Plus de données")
                break
            
            # Convertir en DataFrame
            df = pd.DataFrame(rows, columns=column_names)
            
            # Sauvegarder en Parquet
            output_file = output_dir / f'ratings_{batch_num:04d}.parquet'
            df.to_parquet(
                output_file,
                index=False,
                compression='snappy',
                engine='pyarrow'
            )
            
            total_exported += len(df)
            
            # Afficher progression tous les 10 batches
            if batch_num % 10 == 0:
                print(f"   Batch {batch_num:04d}: {total_exported:,} lignes exportées")
            
            batch_num += 1
            
            # Libérer mémoire
            del df
        
        print(f"\n" + "=" * 60)
        print(f"✅ EXPORT TERMINÉ")
        print(f"   • Total exporté: {total_exported:,} lignes")
        print(f"   • Nombre de fichiers: {batch_num}")
        print(f"   • Dossier: {output_dir}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        
    finally:
        # Toujours fermer
        cursor.close()
        conn.close()
        print("\n🔌 Connexion fermée")
    
    return total_exported

if __name__ == "__main__":
    export_ratings_cursor()