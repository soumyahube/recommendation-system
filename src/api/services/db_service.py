"""
Service Base de Données
Gère la connexion et les requêtes PostgreSQL
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseService:
    """Service pour gérer les interactions avec PostgreSQL"""
    
    def __init__(
        self,
        host: str = "db",
        port: int = 5432,
        database: str = "movierec",
        user: str = "admin",
        password: str = "admin123"
    ):
        """
        Initialise la connexion à la base de données
        
        Args:
            host: Hôte PostgreSQL
            port: Port PostgreSQL
            database: Nom de la base de données
            user: Utilisateur
            password: Mot de passe
        """
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
        self.test_connection()
    
    @contextmanager
    def get_connection(self):
        """Context manager pour gérer les connexions"""
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erreur de base de données: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self):
        """Test la connexion à la base de données"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    logger.info("✅ Connexion PostgreSQL établie avec succès")
        except Exception as e:
            logger.warning(f"⚠️ Impossible de se connecter à PostgreSQL: {e}")
            logger.warning("L'API fonctionnera en mode dégradé (sans BD)")
    
    def get_all_movies(self, limit: int = 100) -> List[Dict]:
        """
        Récupère tous les films de la base de données
        
        Args:
            limit: Nombre maximum de films à retourner
            
        Returns:
            Liste de dictionnaires représentant les films
        """
        try:
            logger.info(f"📊 Tentative de récupération de {limit} films...")
            with self.get_connection() as conn:
                logger.info("✅ Connexion obtenue")

                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    logger.info("✅ Curseur créé")

                    query = """
                        SELECT 
                            movie_id,
                            title,
                            genres
                        FROM dim_movies
                        ORDER BY movie_id
                        LIMIT %s
                    """

                    logger.info(f"🔍 Exécution de la requête avec limit={limit}")
                    cur.execute(query, (limit,))

                    logger.info("✅ Requête exécutée, récupération des résultats...")
                    movies = cur.fetchall()

                    logger.info(f"✅ {len(movies)} films récupérés depuis PostgreSQL")
                    return [dict(movie) for movie in movies]
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des films: {e}")
            logger.error(f"❌ Type d'erreur: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return self._get_fallback_movies()
    
    def get_movie_by_id(self, movie_id: int) -> Optional[Dict]:
        """
        Récupère un film par son ID
        
        Args:
            movie_id: ID du film
            
        Returns:
            Dictionnaire représentant le film ou None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT 
                            movie_id,
                            title,
                            genres
                        FROM dim_movies
                        WHERE movie_id = %s
                    """
                    cur.execute(query, (movie_id,))
                    movie = cur.fetchone()
                    return dict(movie) if movie else None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du film {movie_id}: {e}")
            return None
    
    def search_movies(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Recherche des films par titre
        
        Args:
            query: Terme de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de films correspondants
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    sql_query = """
                        SELECT 
                            movie_id,
                            title,
                            genres
                        FROM dim_movies
                        WHERE LOWER(title) LIKE LOWER(%s)
                        ORDER BY title
                        LIMIT %s
                    """
                    cur.execute(sql_query, (f"%{query}%", limit))
                    movies = cur.fetchall()
                    return [dict(movie) for movie in movies]
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de films: {e}")
            return []
    
    def get_movies_by_genre(self, genre: str, limit: int = 50) -> List[Dict]:
        """
        Récupère des films par genre
        
        Args:
            genre: Genre à rechercher
            limit: Nombre maximum de films
            
        Returns:
            Liste de films du genre spécifié
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT 
                            movie_id,
                            title,
                            genres
                        FROM dim_movies
                        WHERE genres ILIKE %s
                        ORDER BY movie_id
                        LIMIT %s
                    """
                    cur.execute(query, (f"%{genre}%", limit))
                    movies = cur.fetchall()
                    return [dict(movie) for movie in movies]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des films par genre: {e}")
            return []
    
    def get_user_ratings(self, user_id: int, limit: int = 100) -> List[Dict]:
        """
        Récupère les notations d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            limit: Nombre maximum de notations
            
        Returns:
            Liste des notations de l'utilisateur
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT 
                            fr.user_id,
                            fr.movie_id,
                            fr.rating,
                            fr.rating_timestamp,
                            dm.title,
                            dm.genres
                        FROM fact_ratings fr
                        JOIN dim_movies dm ON fr.movie_id = dm.movie_id
                        WHERE fr.user_id = %s
                        ORDER BY fr.rating_timestamp DESC
                        LIMIT %s
                    """
                    cur.execute(query, (user_id, limit))
                    ratings = cur.fetchall()
                    return [dict(rating) for rating in ratings]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des notations: {e}")
            return []
    
    def get_movie_statistics(self, movie_id: int) -> Optional[Dict]:
        """
        Récupère les statistiques d'un film
        
        Args:
            movie_id: ID du film
            
        Returns:
            Statistiques du film (moyenne, nombre de notations)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT 
                            movie_id,
                            COUNT(*) as rating_count,
                            AVG(rating) as avg_rating,
                            MIN(rating) as min_rating,
                            MAX(rating) as max_rating
                        FROM fact_ratings
                        WHERE movie_id = %s
                        GROUP BY movie_id
                    """
                    cur.execute(query, (movie_id,))
                    stats = cur.fetchone()
                    return dict(stats) if stats else None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {e}")
            return None
    
    def _get_fallback_movies(self) -> List[Dict]:
        """Retourne des films de démonstration si la BD n'est pas accessible"""
        return [
            {
                "movie_id": 1,
                "title": "Toy Story (1995)",
                "genres": "Animation|Children|Co"
            },
            {
                "movie_id": 2,
                "title": "Jumanji (1995)",
                "genres": "Adventure|Children|Fan"
            },
            {
                "movie_id": 3,
                "title": "Grumpier Old Men (1995)",
                "genres": "Comedy|Rom"
            }
        ]

# Instance globale du service (singleton)
db_service = DatabaseService()