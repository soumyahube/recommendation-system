import requests
import os
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
BASE_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

@lru_cache(maxsize=1000)
def get_poster_url(title: str, year: str = None) -> str:
    """
    Récupère l'URL du poster depuis TMDb
    Cache les résultats pour éviter les appels répétés
    """
    if not TMDB_API_KEY:
        return None
    
    try:
        # Nettoyer le titre (enlever l'année entre parenthèses)
        clean_title = title
        if "(" in title:
            clean_title = title[:title.rfind("(")].strip()
        
        # Rechercher le film
        search_url = "https://api.themoviedb.org/3/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "query": clean_title,
            "language": "fr-FR"
        }
        if year:
            params["year"] = year
        
        response = requests.get(search_url, params=params, timeout=5)
        response.raise_for_status()
        results = response.json().get("results", [])
        
        if not results:
            return None
        
        # Prendre le premier résultat
        poster_path = results[0].get("poster_path")
        if poster_path:
            return f"{BASE_IMAGE_URL}{poster_path}"
            
        return None
        
    except Exception as e:
        logger.error(f"Erreur TMDb pour '{title}': {e}")
        return None

@lru_cache(maxsize=1000)  
def get_movie_details_tmdb(title: str, year: str = None) -> dict:
    """
    Récupère les détails complets d'un film depuis TMDb
    """
    if not TMDB_API_KEY:
        return {}
    
    try:
        clean_title = title
        if "(" in title:
            clean_title = title[:title.rfind("(")].strip()
        
        search_url = "https://api.themoviedb.org/3/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "query": clean_title,
            "language": "fr-FR"
        }
        if year:
            params["year"] = year
            
        response = requests.get(search_url, params=params, timeout=5)
        response.raise_for_status()
        results = response.json().get("results", [])
        
        if not results:
            return {}
        
        movie = results[0]
        poster_path = movie.get("poster_path")
        
        return {
            "poster_url": f"{BASE_IMAGE_URL}{poster_path}" if poster_path else None,
            "overview": movie.get("overview", ""),
            "vote_average": movie.get("vote_average", 0),
            "release_date": movie.get("release_date", ""),
            "tmdb_id": movie.get("id")
        }
        
    except Exception as e:
        logger.error(f"Erreur TMDb détails pour '{title}': {e}")
        return {}