"""
Modèles Pydantic pour la validation des données
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Movie(BaseModel):
    """Modèle représentant un film"""
    movie_id: int = Field(..., description="ID unique du film")
    title: str = Field(..., description="Titre du film")
    genres: str = Field(..., description="Genres du film (séparés par |)")
    release_year: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "movie_id": 1,
                "title": "Toy Story (1995)",
                "genres": "Animation|Children|Comedy",
                "release_year": 1995
            }
        }

class MovieWithStats(Movie):
    """Film avec statistiques de notation"""
    avg_rating: Optional[float] = Field(None, description="Note moyenne")
    rating_count: Optional[int] = Field(None, description="Nombre de notations")

class Recommendation(BaseModel):
    """Modèle représentant une recommandation"""
    movie_id: int = Field(..., description="ID du film recommandé")
    title: str = Field(..., description="Titre du film")
    genres: str = Field(..., description="Genres du film")
    predicted_rating: float = Field(..., description="Note prédite par le modèle")
    release_year: Optional[int] = Field(None, description="Année de sortie")
    
    class Config:
        json_schema_extra = {
            "example": {
                "movie_id": 1,
                "title": "Toy Story (1995)",
                "genres": "Animation|Children|Comedy",
                "predicted_rating": 4.5,
                "release_year": 1995
            }
        }

class RecommendationRequest(BaseModel):
    """Requête pour obtenir des recommandations"""
    user_id: int = Field(..., description="ID de l'utilisateur", gt=0)
    n_recommendations: int = Field(10, description="Nombre de recommandations", ge=1, le=100)
    genre_filter: Optional[str] = Field(None, description="Filtrer par genre")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "n_recommendations": 10,
                "genre_filter": "Action"
            }
        }

class RecommendationResponse(BaseModel):
    """Réponse contenant les recommandations"""
    user_id: int = Field(..., description="ID de l'utilisateur")
    recommendations: List[Recommendation] = Field(..., description="Liste des films recommandés")
    total_count: int = Field(..., description="Nombre total de recommandations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "recommendations": [
                    {
                        "movie_id": 1,
                        "title": "Toy Story (1995)",
                        "genres": "Animation|Children|Comedy",
                        "predicted_rating": 4.5,
                        "release_year": 1995
                    }
                ],
                "total_count": 1
            }
        }

class Rating(BaseModel):
    """Modèle représentant une notation"""
    user_id: int = Field(..., description="ID de l'utilisateur")
    movie_id: int = Field(..., description="ID du film")
    rating: float = Field(..., description="Note donnée", ge=0.5, le=5.0)
    timestamp: Optional[datetime] = Field(None, description="Date de la notation")

class RatingCreate(BaseModel):
    """Modèle pour créer une nouvelle notation"""
    user_id: int = Field(..., description="ID de l'utilisateur", gt=0)
    movie_id: int = Field(..., description="ID du film", gt=0)
    rating: float = Field(..., description="Note (0.5 à 5.0)", ge=0.5, le=5.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "movie_id": 1,
                "rating": 4.5
            }
        }

class PredictionRequest(BaseModel):
    """Requête pour prédire une note"""
    user_id: int = Field(..., description="ID de l'utilisateur", gt=0)
    movie_id: int = Field(..., description="ID du film", gt=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "movie_id": 1
            }
        }

class PredictionResponse(BaseModel):
    """Réponse avec la prédiction"""
    user_id: int = Field(..., description="ID de l'utilisateur")
    movie_id: int = Field(..., description="ID du film")
    predicted_rating: float = Field(..., description="Note prédite")
    movie_title: Optional[str] = Field(None, description="Titre du film")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "movie_id": 1,
                "predicted_rating": 4.5,
                "movie_title": "Toy Story (1995)"
            }
        }

class HealthResponse(BaseModel):
    """Réponse du health check"""
    status: str = Field(..., description="État de l'API")
    service: str = Field(..., description="Nom du service")
    model_loaded: bool = Field(..., description="Modèle ML chargé")
    database_connected: bool = Field(..., description="Base de données connectée")

class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée"""
    error: str = Field(..., description="Type d'erreur")
    message: str = Field(..., description="Message d'erreur")
    detail: Optional[str] = Field(None, description="Détails supplémentaires")