# data/database/load_simple.py
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import time
from pathlib import Path

class DatabaseLoader:
    """Chargeur simplifié pour la base de données MovieRec"""
    
    def __init__(self, db_config=None):
        # Configuration par défaut
        self.db_config = db_config or {
            'host': 'localhost',
            'database': 'movierec',
            'user': 'admin',
            'password': 'admin123',
            'port': '5432'
        }
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Établit la connexion à PostgreSQL"""
        try:
            print("Connexion à la base de données...")
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            print("✅ Connecté avec succès")
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False
    
    def disconnect(self):
        """Ferme la connexion"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("Connexion fermée")
    
    def execute_sql_file(self, file_path):
        """Exécute un fichier SQL"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            self.cursor.execute(sql)
            self.conn.commit()
            print(f"✅ Fichier SQL exécuté: {file_path}")
            return True
        except Exception as e:
            print(f"❌ Erreur SQL: {e}")
            self.conn.rollback()
            return False
    
    def load_movies(self, file_path):
        """Charge les films depuis movies.csv"""
        print("Chargement des films...")
        
        try:
            # Lire les données
            movies_df = pd.read_csv(file_path)
            print(f"  {len(movies_df)} films trouvés")
            
            # Nettoyage
            movies_df = movies_df.drop_duplicates(subset=['movieId'])
            movies_df['genres'] = movies_df['genres'].fillna('(no genres listed)')
            
            # Ajouter les liens si disponibles
            links_path = file_path.parent / 'links.csv'
            if links_path.exists():
                links_df = pd.read_csv(links_path)
                movies_df = pd.merge(movies_df, links_df, on='movieId', how='left')
                print("  Liens TMDB/IMDB ajoutés")
            
            # Préparer les données pour insertion
            movies_data = []
            for _, row in movies_df.iterrows():
                movies_data.append((
                    int(row['movieId']),
                    str(row['title']),
                    str(row['genres']),
                    int(row['tmdbId']) if 'tmdbId' in row and not pd.isna(row['tmdbId']) else None,
                    str(int(row['imdbId'])) if 'imdbId' in row and not pd.isna(row['imdbId']) else None
                ))
            
            # Insertion par batch
            batch_size = 1000
            inserted = 0
            
            for i in range(0, len(movies_data), batch_size):
                batch = movies_data[i:i+batch_size]
                execute_batch(self.cursor, """
                    INSERT INTO dim_movies (movie_id, title, genres, tmdb_id, imdb_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (movie_id) DO NOTHING
                """, batch)
                inserted += len(batch)
            
            self.conn.commit()
            print(f"✅ {inserted} films chargés")
            return True
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            self.conn.rollback()
            return False
    
    def load_users(self, ratings_file):
        """Charge les utilisateurs uniques depuis ratings.csv"""
        print("Chargement des utilisateurs...")
        
        try:
            # Extraire les utilisateurs uniques
            ratings_df = pd.read_csv(ratings_file, usecols=['userId'])
            unique_users = ratings_df['userId'].unique()
            print(f"  {len(unique_users)} utilisateurs uniques trouvés")
            
            # Préparer les données
            user_data = [(int(user_id),) for user_id in unique_users]
            
            # Insertion par batch
            batch_size = 5000
            
            for i in range(0, len(user_data), batch_size):
                batch = user_data[i:i+batch_size]
                execute_batch(self.cursor, """
                    INSERT INTO dim_users (user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING
                """, batch)
            
            self.conn.commit()
            print(f"✅ {len(user_data)} utilisateurs chargés")
            return True
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            self.conn.rollback()
            return False
    
    def load_ratings(self, file_path):
        """Charge les notes/évaluations"""
        print("Chargement des notes...")
        
        try:
            # Lire les données
            ratings_df = pd.read_csv(file_path)
            total_rows = len(ratings_df)
            print(f"  {total_rows:,} notes trouvées")
            
            # Nettoyage
            ratings_df = ratings_df.drop_duplicates(subset=['userId', 'movieId', 'timestamp'])
            ratings_df = ratings_df[ratings_df['rating'].between(0.5, 5.0)]
            print(f"  {len(ratings_df):,} notes valides après nettoyage")
            
            # Chargement par batch
            batch_size = 2000
            inserted = 0
            
            for i in range(0, len(ratings_df), batch_size):
                batch_df = ratings_df.iloc[i:i+batch_size]
                
                # Préparer les données
                batch_data = []
                for _, row in batch_df.iterrows():
                    batch_data.append((
                        float(row['rating']),   # rating
                        int(row['timestamp']),  # timestamp
                        int(row['userId']),     # user_id
                        int(row['movieId'])     # movie_id
                    ))
                
                # Insertion avec jointure aux tables de dimension
                execute_batch(self.cursor, """
                    INSERT INTO fact_ratings (rating, timestamp, user_key, movie_key)
                    SELECT %s, %s, u.user_key, m.movie_key
                    FROM dim_users u, dim_movies m
                    WHERE u.user_id = %s AND m.movie_id = %s
                    ON CONFLICT (user_key, movie_key) DO NOTHING
                """, batch_data)
                
                inserted += len(batch_data)
                
                # Afficher la progression
                progress = min(i + batch_size, total_rows)
                if (i + batch_size) % 25000 == 0 or progress == total_rows:
                    percent = (progress / total_rows) * 100
                    print(f"  Progression: {progress:,}/{total_rows:,} ({percent:.1f}%)")
            
            self.conn.commit()
            print(f"✅ {inserted} notes chargées")
            return True
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            self.conn.rollback()
            return False
    
    def show_stats(self):
        """Affiche les statistiques de la base"""
        print("\n📊 Statistiques de la base:")
        print("-" * 30)
        
        queries = [
            ("Films", "SELECT COUNT(*) FROM dim_movies"),
            ("Utilisateurs", "SELECT COUNT(*) FROM dim_users"),
            ("Notes", "SELECT COUNT(*) FROM fact_ratings"),
            ("Note moyenne", "SELECT ROUND(AVG(rating), 2) FROM fact_ratings"),
        ]
        
        for label, query in queries:
            self.cursor.execute(query)
            result = self.cursor.fetchone()[0]
            print(f"  {label}: {result}")
    
    def run(self, data_dir='data/raw/ml-25m'):
        """Exécute le chargement complet"""
        print("\n" + "=" * 50)
        print("Chargement des données MovieLens")
        print("=" * 50)
        
        start_time = time.time()
        
        # Vérifier le dossier de données
        data_path = Path(data_dir)
        if not data_path.exists():
            print(f"❌ Dossier introuvable: {data_path}")
            return False
        
        # Vérifier les fichiers nécessaires
        required = ['ratings.csv', 'movies.csv']
        for file in required:
            if not (data_path / file).exists():
                print(f"❌ Fichier manquant: {file}")
                return False
        
        # Connexion
        if not self.connect():
            return False
        
        try:
            # 1. Créer le schéma
            print("\nÉtape 1/4: Création du schéma")
            schema_file = 'data/database/schema.sql'
            if not self.execute_sql_file(schema_file):
                return False
            
            # 2. Charger les films
            print("\nÉtape 2/4: Chargement des films")
            if not self.load_movies(data_path / 'movies.csv'):
                return False
            
            # 3. Charger les utilisateurs
            print("\nÉtape 3/4: Chargement des utilisateurs")
            if not self.load_users(data_path / 'ratings.csv'):
                return False
            
            # 4. Charger les notes
            print("\nÉtape 4/4: Chargement des notes")
            if not self.load_ratings(data_path / 'ratings.csv'):
                return False
            
            # Afficher les statistiques
            self.show_stats()
            
            # Temps d'exécution
            elapsed = time.time() - start_time
            print(f"\n✅ Chargement terminé en {elapsed:.1f} secondes")
            return True
            
        except KeyboardInterrupt:
            print("\n⚠️  Chargement interrompu")
            self.conn.rollback()
            return False
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            self.conn.rollback()
            return False
        finally:
            self.disconnect()


def main():
    """Point d'entrée principal"""
    print("Chargement de la base de données MovieRec")
    
    # Demander confirmation
    confirm = input("Ce processus va charger les données dans PostgreSQL. Continuer ? (o/n): ")
    if confirm.lower() not in ['o', 'oui', 'y', 'yes']:
        print("Opération annulée")
        return
    
    # Configuration (à adapter selon votre environnement)
    db_config = {
        'host': 'localhost',
        'database': 'movierec',
        'user': 'admin',
        'password': 'admin123',
        'port': '5432'
    }
    
    # Lancer le chargement
    loader = DatabaseLoader(db_config)
    success = loader.run()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ Base de données prête pour l'étape suivante")
        print("=" * 50)
    else:
        print("\n❌ Le chargement a échoué")


if __name__ == "__main__":
    main()