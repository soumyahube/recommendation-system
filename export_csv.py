# export_fixed.py
import pandas as pd
import subprocess
import os
import time
import sys
from sqlalchemy import create_engine, text  # AJOUT: text

def export_with_ram_safety():
    """Export optimisé pour 3.2GB RAM"""
    
    print("🚀 EXPORT OPTIMISÉ POUR 3.2GB R    import psycopg2
    import pandas as pd
    import time
    from pathlib import Path
    from psycopg2.extras import execute_batch
    
    class CompleteDataLoader:
        """Chargeur complet et fonctionnel"""
        
        def __init__(self):
            self.db_config = {
                'host': 'localhost',
                'database': 'movierec',
                'user': 'admin',
                'password': 'admin123',
                'port': '5432'
            }
            self.conn = None
            self.cursor = None
        
        def connect(self):
            """Connexion à PostgreSQL"""
            try:
                self.conn = psycopg2.connect(**self.db_config)
                self.cursor = self.conn.cursor()
                print("✅ Connecté à PostgreSQL")
                return True
            except Exception as e:
                print(f"❌ Erreur connexion: {e}")
                return False
        
        def disconnect(self):
            """Fermeture"""
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        
        def load_movies(self):
            """Charge les films"""
            print("\n📽️  Chargement des FILMS...")
            try:
                df = pd.read_csv('data/raw/ml-25m/movies.csv')
                print(f"   {len(df)} films lus")
                
                # Supprimer les doublons
                df = df.drop_duplicates(subset=['movieId'])
                df['genres'] = df['genres'].fillna('(no genres listed)')
                
                # Insertion
                data = [
                    (row['movieId'], row['title'], row['genres'])
                    for _, row in df.iterrows()
                ]
                
                execute_batch(
                    self.cursor,
                    """INSERT INTO dim_movies (movie_id, title, genres) 
                       VALUES (%s, %s, %s) 
                       ON CONFLICT (movie_id) DO NOTHING""",
                    data,
                    page_size=1000
                )
                
                self.conn.commit()
                print(f"   ✅ {len(data)} films chargés")
                return True
                
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
                self.conn.rollback()
                return False
        
        def load_users(self):
            """Charge les utilisateurs uniques depuis ratings.csv"""
            print("\n👥 Chargement des UTILISATEURS...")
            try:
                df = pd.read_csv('data/raw/ml-25m/ratings.csv', usecols=['userId'])
                users = df['userId'].unique()
                print(f"   {len(users)} utilisateurs uniques trouvés")
                
                data = [(int(uid),) for uid in users]
                
                execute_batch(
                    self.cursor,
                    """INSERT INTO dim_users (user_id) 
                       VALUES (%s) 
                       ON CONFLICT (user_id) DO NOTHING""",
                    data,
                    page_size=5000
                )
                
                self.conn.commit()
                print(f"   ✅ {len(data)} utilisateurs chargés")
                return True
                
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
                self.conn.rollback()
                return False
        
        def load_ratings(self):
            """Charge les notes avec COPY (très rapide)"""
            print("\n⭐ Chargement des NOTES (ceci peut prendre 1-2h)...")
            try:
                # Créer table temporaire
                self.cursor.execute("""
                    CREATE TEMP TABLE temp_ratings (
                        user_id INTEGER,
                        movie_id INTEGER,
                        rating DECIMAL(2,1),
                        timestamp BIGINT
                    )
                """)
                
                # COPY depuis CSV
                with open('data/raw/ml-25m/ratings.csv', 'r') as f:
                    next(f)  # Sauter l'en-tête
                    self.cursor.copy_from(f, 'temp_ratings', sep=',')
                
                print("   ✅ CSV importé")
                
                # Insérer dans fact_ratings
                self.cursor.execute("""
                    INSERT INTO fact_ratings (user_key, movie_key, rating, timestamp)
                    SELECT u.user_key, m.movie_key, tr.rating, tr.timestamp
                    FROM temp_ratings tr
                    JOIN dim_users u ON tr.user_id = u.user_id
                    JOIN dim_movies m ON tr.movie_id = m.movie_id
                """)
                
                self.conn.commit()
                
                # Compter
                self.cursor.execute("SELECT COUNT(*) FROM fact_ratings")
                count = self.cursor.fetchone()[0]
                print(f"   ✅ {count:,} notes chargées")
                return True
                
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
                self.conn.rollback()
                return False
        
        def show_stats(self):
            """Affiche les stats finales"""
            print("\n" + "="*50)
            print("📊 STATISTIQUES FINALES")
            print("="*50)
            
            queries = [
                ("Films", "SELECT COUNT(*) FROM dim_movies"),
                ("Utilisateurs", "SELECT COUNT(*) FROM dim_users"),
                ("Notes", "SELECT COUNT(*) FROM fact_ratings"),
                ("Note moyenne", "SELECT ROUND(AVG(rating), 2) FROM fact_ratings"),
                ("Min/Max rating", "SELECT MIN(rating), MAX(rating) FROM fact_ratings"),
            ]
            
            for label, query in queries:
                self.cursor.execute(query)
                result = self.cursor.fetchone()
                print(f"{label:20} : {result[0]:,}")
        
        def run(self):
            """Exécute tout"""
            start = time.time()
            
            if not self.connect():
                return False
            
            try:
                # Vérifier les fichiers
                files = ['data/raw/ml-25m/movies.csv', 'data/raw/ml-25m/ratings.csv']
                for f in files:
                    if not Path(f).exists():
                        print(f"❌ Fichier manquant: {f}")
                        return False
                
                # Charger
                if not self.load_movies():
                    return False
                if not self.load_users():
                    return False
                if not self.load_ratings():
                    return False
                
                self.show_stats()
                
                elapsed = time.time() - start
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                print(f"\n⏱️  Temps total: {hours}h{minutes:02d}m")
                
                return True
                
            finally:
                self.disconnect()
    
    if __name__ == "__main__":
        loader = CompleteDataLoader()
        success = loader.run()
        exit(0 if success else 1)AM")
    print("=" * 60)
    
    # Paramètres
    CHUNK_SIZE = 60000
    
    # Connexion PostgreSQL
    engine = create_engine('postgresql://admin:admin123@localhost:5432/movierec')
    
    # Vérifier le total - SYNTAXE CORRIGÉE
    with engine.connect() as conn:
        # CORRECTION: Utiliser text() pour les requêtes SQL
        result = conn.execute(text("SELECT COUNT(*) FROM fact_ratings"))
        total_rows = result.scalar()
        print(f"📊 Total à exporter: {total_rows:,} lignes")
    
    offset = 0
    chunk_num = 0
    total_exported = 0
    
    print(f"\n🎯 Configuration:")
    print(f"   • Chunk size: {CHUNK_SIZE:,} lignes")
    print(f"   • RAM disponible: 3.2 GB")
    print(f"\n⏳ Début de l'export...")
    
    start_time = time.time()
    
    # Créer dossiers Google Drive
    subprocess.run(["rclone", "mkdir", "gdrive:movie_data_25m"], capture_output=True)
    subprocess.run(["rclone", "mkdir", "gdrive:movie_data_25m/chunks"], capture_output=True)
    
    try:
        while True:
            # Requête - SYNTAXE CORRIGÉE
            query = text(f"""
                SELECT rating_id, user_key, movie_key, rating
                FROM fact_ratings 
                ORDER BY rating_id 
                LIMIT {CHUNK_SIZE} OFFSET {offset}
            """)
            
            # Lire chunk - CORRECTION: utiliser text() dans read_sql
            df = pd.read_sql(query, engine.connect())
            
            if len(df) == 0:
                print("\n✅ Plus de données")
                break
            
            # Optimiser types
            for col in ['rating_id', 'user_key', 'movie_key']:
                if col in df.columns:
                    df[col] = df[col].astype('int32')
            if 'rating' in df.columns:
                df['rating'] = df['rating'].astype('float32')
            
            # Sauvegarder dans RAM
            temp_file = f"/dev/shm/chunk_{chunk_num:05d}.csv.gz"
            df.to_csv(temp_file, index=False, compression='gzip')
            
            file_size_mb = os.path.getsize(temp_file) / (1024**2)
            total_exported += len(df)
            
            # Upload
            print(f"📦 {chunk_num:03d}: {len(df):,}l → {file_size_mb:.1f}MB → ", end="", flush=True)
            
            try:
                result = subprocess.run(
                    ["rclone", "copyto", temp_file, 
                     f"gdrive:movie_data_25m/chunks/chunk_{chunk_num:05d}.csv.gz"],
                    capture_output=True,
                    text=True,
                    timeout=45
                )
                print("Google Drive ✓" if result.returncode == 0 else "❌")
            except Exception as e:
                print(f"⏱️ {str(e)[:20]}")
            
            # Supprimer immédiatement
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            
            # Mettre à jour
            offset += CHUNK_SIZE
            chunk_num += 1
            
            # Progression
            if chunk_num % 5 == 0:
                elapsed = time.time() - start_time
                percent = (total_exported / total_rows) * 100
                rate = total_exported / elapsed if elapsed > 0 else 0
                
                # ETA
                remaining = total_rows - total_exported
                if rate > 0:
                    eta_seconds = remaining / rate
                    eta_hours = eta_seconds / 3600
                    print(f"   • {total_exported:,}l [{percent:.1f}%] - {rate:,.0f}l/s")
                    print(f"   • ETA: {eta_hours:.1f}h restantes")
                else:
                    print(f"   • {total_exported:,}l [{percent:.1f}%]")
            
            # Libérer mémoire
            del df
            
            # Pause occasionnelle pour éviter surcharge
            if chunk_num % 50 == 0:
                import gc
                gc.collect()
                time.sleep(2)
                
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrompu - {total_exported:,} lignes exportées")
    
    finally:
        engine.dispose()
    
    # Rapport final
    total_time = time.time() - start_time
    
    print(f"\n" + "=" * 60)
    print("✅ EXPORT TERMINÉ !")
    print("=" * 60)
    print(f"📊 Résultats:")
    print(f"   • Lignes: {total_exported:,}")
    print(f"   • Chunks: {chunk_num}")
    print(f"   • Temps: {total_time/3600:.1f} heures")
    
    if total_time > 0:
        print(f"   • Vitesse: {total_exported/total_time:,.0f} l/s")
    
    # Vérifier Google Drive
    print(f"\n🔍 Google Drive:")
    try:
        result = subprocess.run(["rclone", "lsf", "gdrive:movie_data_25m/chunks/"], 
                              capture_output=True, text=True)
        files = [f for f in result.stdout.strip().split('\n') if f]
        print(f"   • Fichiers: {len(files)}/{chunk_num}")
    except:
        print(f"   • Vérification échouée")
    
    print("\n🎯 DONNÉES DISPONIBLES SUR GOOGLE DRIVE !")
    print("=" * 60)

if __name__ == "__main__":
    print("🎬 EXPORT MOVIELENS 25M")
    print("=" * 60)
    
    # Vérifier imports
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sqlalchemy"])
        from sqlalchemy import create_engine, text
    
    # Lancer
    export_with_ram_safety()