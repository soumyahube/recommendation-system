# resume_ratings_fixed_v2.py
import psycopg2
import time
from pathlib import Path

def resume_ratings_fixed():
    """Version corrigée SANS ON CONFLICT"""
    
    print("🔄 CHARGEMENT DES NOTES (VERSION CORRIGÉE)")
    print("=" * 50)
    
    # Configuration
    db_config = {
        'host': 'localhost',
        'database': 'movierec',
        'user': 'admin',
        'password': 'admin123',
        'port': '5432'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        start_time = time.time()
        
        # 1. Vider la table fact_ratings (elle est vide de toute façon)
        print("🧹 Nettoyage de fact_ratings...")
        cursor.execute("TRUNCATE fact_ratings RESTART IDENTITY")
        conn.commit()
        
        # 2. Vérifier et supprimer les anciennes contraintes UNIQUE
        print("🔍 Vérification des contraintes...")
        cursor.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'fact_ratings' 
            AND constraint_type = 'UNIQUE'
        """)
        
        constraints = cursor.fetchall()
        for (constraint_name,) in constraints:
            print(f"   Suppression: {constraint_name}")
            cursor.execute(f"ALTER TABLE fact_ratings DROP CONSTRAINT IF EXISTS {constraint_name}")
        
        conn.commit()
        
        # 3. Méthode COPY (optimisée)
        print("\n📥 Chargement avec COPY...")
        
        # Créer table temporaire
        cursor.execute("""
            CREATE TEMP TABLE temp_ratings_all (
                user_id INTEGER,
                movie_id INTEGER,
                rating DECIMAL(2,1),
                timestamp BIGINT
            )
        """)
        
        # Copier depuis CSV
        csv_path = Path("data/raw/ml-25m/ratings.csv")
        print(f"  Lecture de {csv_path}")
        
        with open(csv_path, 'r') as f:
            # Saute l'en-tête
            next(f)
            cursor.copy_from(f, 'temp_ratings_all', sep=',', null='')
        
        print(f"  ✅ CSV chargé ({csv_path.stat().st_size / (1024**3):.1f} GB)")
        
        # 4. Insérer SANS ON CONFLICT
        print("  🔄 Insertion dans fact_ratings...")
        cursor.execute("""
            INSERT INTO fact_ratings (rating, timestamp, user_key, movie_key)
            SELECT 
                tr.rating, 
                tr.timestamp, 
                u.user_key, 
                m.movie_key
            FROM temp_ratings_all tr
            JOIN dim_users u ON tr.user_id = u.user_id
            JOIN dim_movies m ON tr.movie_id = m.movie_id
        """)
        
        conn.commit()
        print("  ✅ Insertion terminée")
        
        # 5. Supprimer les doublons (s'il y en a)
        print("  🧹 Nettoyage des doublons...")
        cursor.execute("""
            DELETE FROM fact_ratings 
            WHERE ctid NOT IN (
                SELECT MIN(ctid)
                FROM fact_ratings 
                GROUP BY user_key, movie_key
            )
        """)
        duplicates_removed = cursor.rowcount
        if duplicates_removed > 0:
            print(f"  ✅ {duplicates_removed} doublons supprimés")
        
        conn.commit()
        
        # 6. Ajouter la contrainte UNIQUE (MAINTENANT)
        print("  🔧 Ajout de la contrainte UNIQUE...")
        try:
            cursor.execute("""
                ALTER TABLE fact_ratings 
                ADD CONSTRAINT fact_ratings_user_movie_unique 
                UNIQUE (user_key, movie_key)
            """)
            conn.commit()
            print("  ✅ Contrainte UNIQUE ajoutée")
        except Exception as e:
            print(f"  ⚠️  Impossible d'ajouter la contrainte: {e}")
            conn.rollback()
        
        # 7. Créer les index
        print("  📊 Création des index...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_user ON fact_ratings(user_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_movie ON fact_ratings(movie_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_timestamp ON fact_ratings(timestamp)")
        conn.commit()
        
        # 8. Statistiques finales
        cursor.execute("SELECT COUNT(*) FROM fact_ratings")
        total = cursor.fetchone()[0]
        
        elapsed = time.time() - start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        print(f"\n" + "=" * 50)
        print("✅ CHARGEMENT TERMINÉ AVEC SUCCÈS !")
        print("=" * 50)
        print(f"📊 STATISTIQUES :")
        print(f"   • Notes chargées : {total:,}")
        print(f"   • Temps total : {hours}h{minutes:02d}m{seconds:02d}s")
        print(f"   • Vitesse : {total/elapsed:.0f} notes/sec")
        print(f"   • Doublons supprimés : {duplicates_removed}")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()
        return False
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    resume_ratings_fixed()