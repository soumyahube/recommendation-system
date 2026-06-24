"""
Router pour les endpoints de recommandation
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from schemas.models import (
    RecommendationResponse,
    Recommendation,
    PredictionRequest,
    PredictionResponse,
    RatingCreate
)

from services.ml_service import ml_service
from services.db_service import db_service
from services.kafka_producer import get_kafka_producer

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/recommend/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: int,
    n: int = Query(10, ge=1, le=100, description="Nombre de recommandations"),
    genre: Optional[str] = Query(None, description="Filtrer par genre")
):
    """
    Obtient des recommandations personnalisées pour un utilisateur
    
    Args:
        user_id: ID de l'utilisateur
        n: Nombre de recommandations (1-100)
        genre: Genre optionnel pour filtrer
        
    Returns:
        Liste de films recommandés avec leurs notes prédites
    """
    try:
        logger.info(f"Génération de {n} recommandations pour l'utilisateur {user_id}")
        
        # Récupérer tous les films disponibles
        if genre:
            movies = db_service.get_movies_by_genre(genre, limit=500)
            logger.info(f"Filtrage par genre: {genre} ({len(movies)} films)")
        else:
            movies = db_service.get_all_movies(limit=500)
        
        if not movies:
            raise HTTPException(
                status_code=404,
                detail="Aucun film trouvé dans la base de données"
            )
        
        # Extraire les IDs de films
        movie_ids = [movie['movie_id'] for movie in movies]
        
        # Obtenir les recommandations du modèle ML
        predictions = ml_service.get_top_n_recommendations(
            user_id=user_id,
            movie_ids=movie_ids,
            n=n
        )
        
        if not predictions:
            raise HTTPException(
                status_code=500,
                detail="Impossible de générer des recommandations"
            )
        
        # Créer un dictionnaire pour un accès rapide aux films
        movies_dict = {movie['movie_id']: movie for movie in movies}
        
        # Construire la réponse avec les détails des films
        recommendations = []
        for movie_id, predicted_rating in predictions:
            if movie_id in movies_dict:
                movie_data = movies_dict[movie_id]
                recommendations.append(
                    Recommendation(
                        movie_id=movie_id,
                        title=movie_data['title'],
                        genres=movie_data['genres'],
                        predicted_rating=predicted_rating,
                        release_year=movie_data.get('release_year')
                    )
                )
        
        logger.info(f"✅ {len(recommendations)} recommandations générées avec succès")
        
        return RecommendationResponse(
            user_id=user_id,
            recommendations=recommendations,
            total_count=len(recommendations)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération des recommandations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )

@router.post("/predict", response_model=PredictionResponse)
async def predict_rating(request: PredictionRequest):
    """
    Prédit la note qu'un utilisateur donnerait à un film
    
    Args:
        request: Contient user_id et movie_id
        
    Returns:
        Note prédite pour le couple (utilisateur, film)
    """
    try:
        logger.info(f"Prédiction pour user {request.user_id}, movie {request.movie_id}")
        
        # Prédire la note
        predicted_rating = ml_service.predict_rating(
            user_id=request.user_id,
            movie_id=request.movie_id
        )
        
        # Récupérer les infos du film
        movie = db_service.get_movie_by_id(request.movie_id)
        movie_title = movie['title'] if movie else None
        
        logger.info(f"✅ Prédiction: {predicted_rating}/5.0")
        
        return PredictionResponse(
            user_id=request.user_id,
            movie_id=request.movie_id,
            predicted_rating=predicted_rating,
            movie_title=movie_title
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la prédiction: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )

@router.get("/user/{user_id}/history")
async def get_user_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=200, description="Nombre de notations")
):
    """
    Récupère l'historique des notations d'un utilisateur
    
    Args:
        user_id: ID de l'utilisateur
        limit: Nombre maximum de notations à retourner
        
    Returns:
        Liste des films notés par l'utilisateur
    """
    try:
        logger.info(f"Récupération de l'historique pour l'utilisateur {user_id}")
        
        ratings = db_service.get_user_ratings(user_id, limit=limit)
        
        if not ratings:
            return {
                "user_id": user_id,
                "ratings": [],
                "total_count": 0,
                "message": "Aucune notation trouvée pour cet utilisateur"
            }
        
        logger.info(f"✅ {len(ratings)} notations récupérées")
        
        return {
            "user_id": user_id,
            "ratings": ratings,
            "total_count": len(ratings)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération de l'historique: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )
    
@router.get("/test/users")
async def test_users():
    """Liste des 10 premiers users disponibles"""
    from services.ml_service import ml_service
    users = list(ml_service.user_to_idx.keys())[:10]
    return {"available_users": users}

@router.get("/test/available")
async def test_available():
    """Retourne users et movies disponibles pour test"""
    from services.ml_service import ml_service
    
    users = list(ml_service.user_to_idx.keys())[:10]
    movies = list(ml_service.item_to_idx.keys())[:20]
    
    return {
        "available_users": users,
        "available_movies": movies,
        "example_recommendation": f"/api/v1/recommend/{users[0]}?n=10"
    }

@router.post("/rate")
async def rate_movie(rating: RatingCreate):
    """
    Enregistre une nouvelle notation via Kafka
    
    Args:
        rating: Données de notation (user_id, movie_id, rating)
    
    Returns:
        Confirmation d'envoi
    """
    try:
        logger.info(f"📝 Nouvelle notation: User {rating.user_id}, Movie {rating.movie_id}, Rating {rating.rating}")
        
        # Envoyer à Kafka
        producer = get_kafka_producer()
        success = producer.send_rating(
            user_id=rating.user_id,
            movie_id=rating.movie_id,
            rating=rating.rating
        )
        
        if success:
            return {
                "status": "success",
                "message": "Notation envoyée à Kafka avec succès",
                "data": {
                    "user_id": rating.user_id,
                    "movie_id": rating.movie_id,
                    "rating": rating.rating
                }
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Impossible d'envoyer la notation à Kafka"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'enregistrement: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )