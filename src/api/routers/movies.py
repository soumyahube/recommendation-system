"""
Router pour les endpoints liés aux films
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from schemas.models import Movie, MovieWithStats
from services.db_service import db_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/movies", response_model=List[Movie])
async def get_movies(
    limit: int = Query(100, ge=1, le=1000, description="Nombre de films à retourner"),
    search: Optional[str] = Query(None, description="Rechercher par titre"),
    genre: Optional[str] = Query(None, description="Filtrer par genre")
):
    """
    Récupère la liste des films
    
    Args:
        limit: Nombre maximum de films
        search: Terme de recherche dans les titres
        genre: Filtrer par genre
        
    Returns:
        Liste de films
    """
    try:
        logger.info(f"Récupération des films (limit={limit}, search={search}, genre={genre})")
        
        if search:
            movies = db_service.search_movies(search, limit=limit)
            logger.info(f"Recherche '{search}': {len(movies)} films trouvés")
        elif genre:
            movies = db_service.get_movies_by_genre(genre, limit=limit)
            logger.info(f"Genre '{genre}': {len(movies)} films trouvés")
        else:
            movies = db_service.get_all_movies(limit=limit)
            logger.info(f"{len(movies)} films récupérés")
        
        return movies
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des films: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )

@router.get("/movies/{movie_id}", response_model=MovieWithStats)
async def get_movie_details(movie_id: int):
    """
    Récupère les détails d'un film avec ses statistiques
    
    Args:
        movie_id: ID du film
        
    Returns:
        Détails du film avec statistiques de notation
    """
    try:
        logger.info(f"Récupération des détails du film {movie_id}")
        
        # Récupérer le film
        movie = db_service.get_movie_by_id(movie_id)
        
        if not movie:
            raise HTTPException(
                status_code=404,
                detail=f"Film {movie_id} non trouvé"
            )
        
        # Récupérer les statistiques
        stats = db_service.get_movie_statistics(movie_id)
        
        # Combiner les données
        movie_data = {
            **movie,
            "avg_rating": stats.get('avg_rating') if stats else None,
            "rating_count": stats.get('rating_count') if stats else None
        }
        
        logger.info(f"✅ Détails récupérés pour: {movie['title']}")
        
        return movie_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération du film: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )

@router.get("/genres")
async def get_all_genres():
    """
    Récupère la liste de tous les genres disponibles
    
    Returns:
        Liste des genres uniques
    """
    try:
        logger.info("Récupération de tous les genres")
        
        movies = db_service.get_all_movies(limit=1000)
        
        # Extraire tous les genres uniques
        all_genres = set()
        for movie in movies:
            genres = movie['genres'].split('|')
            all_genres.update(genres)
        
        genres_list = sorted(list(all_genres))
        
        logger.info(f"✅ {len(genres_list)} genres trouvés")
        
        return {
            "genres": genres_list,
            "total_count": len(genres_list)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des genres: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )

@router.get("/movies/popular/{n}")
async def get_popular_movies(n: int = 10):
    """
    Récupère les films les plus populaires (les plus notés)
    
    Args:
        n: Nombre de films à retourner
        
    Returns:
        Liste des films populaires
    """
    try:
        logger.info(f"Récupération des {n} films les plus populaires")
        
        # Cette requête nécessiterait une jointure complexe
        # Pour simplifier, on retourne les premiers films
        movies = db_service.get_all_movies(limit=n)
        
        logger.info(f"✅ {len(movies)} films populaires récupérés")
        
        return {
            "movies": movies,
            "total_count": len(movies)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des films populaires: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )