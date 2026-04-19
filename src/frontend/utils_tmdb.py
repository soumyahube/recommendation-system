import requests
import os
import logging

logger = logging.getLogger(__name__)

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "ce703cbcc8da689c5aa6a69369787ed9")  # Mettez votre clé API
BASE_URL = "https://image.tmdb.org/t/p/w500"

def search_movie_ids(title, year=None):
    """Retourne TMDb ID pour un film donné par son titre et éventuellement année"""
    if not TMDB_API_KEY or TMDB_API_KEY == "ce703cbcc8da689c5aa6a69369787ed9":
        logger.warning("TMDB_API_KEY non configurée")
        return None, None
        
    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
        if year:
            url += f"&year={year}"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results")
        if results and len(results) > 0:
            tmdb_id = results[0]["id"]
            # Récupérer IMDB ID via le détail du film
            detail_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
            detail_response = requests.get(detail_url, timeout=5)
            detail_response.raise_for_status()
            detail_data = detail_response.json()
            imdb_id = detail_data.get("imdb_id")
            return tmdb_id, imdb_id
    except Exception as e:
        logger.error(f"Erreur récupération IDs: {e}")
    return None, None

def get_movie_poster(tmdb_id=None, imdb_id=None, title=None, year=None):
    """Retourne l'URL du poster TMDb"""
    if not TMDB_API_KEY or TMDB_API_KEY == "ce703cbcc8da689c5aa6a69369787ed9":
        return None
        
    try:
        # Si on a un titre mais pas d'ID
        if not tmdb_id and not imdb_id and title:
            tmdb_id, imdb_id = search_movie_ids(title, year)

        # Recherche par TMDb ID
        if tmdb_id:
            url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            poster_path = data.get("poster_path")
            if poster_path:
                return f"{BASE_URL}{poster_path}"

        # Recherche par IMDB ID
        if imdb_id:
            url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={TMDB_API_KEY}&external_source=imdb_id"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            movie_results = data.get("movie_results", [])
            if movie_results:
                poster_path = movie_results[0].get("poster_path")
                if poster_path:
                    return f"{BASE_URL}{poster_path}"
                    
    except Exception as e:
        logger.error(f"Erreur récupération poster: {e}")
        return None

    return None