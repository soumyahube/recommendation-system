import psycopg2
import pandas as pd
import time
from pathlib import Path
from psycopg2.extras import execute_batch

class CompleteDataLoader:
    """Chargeur complet et fonctionnel"""
    
    def __init__(self):
        self.db_config = {
            'host': 'db',
            'database': 'movierec',
            'user': 'admin',
            'password': 'admin123',
            'port': '5432',
            'connect_timeout': 30,      # ✅ AJOUTER
            'keepalives': 1,            # ✅ AJOUTER
            'keepalives_idle': 30,            
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
            self.cursor.execute("SET statement_timeout = 0")
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
    exit(0 if success else 1)