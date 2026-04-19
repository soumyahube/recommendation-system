"""
Schemas Pydantic
"""

from .models import (
    Movie,
    MovieWithStats,
    Recommendation,
    RecommendationRequest,
    RecommendationResponse,
    Rating,
    RatingCreate,
    PredictionRequest,
    PredictionResponse,
    HealthResponse,
    ErrorResponse
)

__all__ = [
    'Movie',
    'MovieWithStats',
    'Recommendation',
    'RecommendationRequest',
    'RecommendationResponse',
    'Rating',
    'RatingCreate',
    'PredictionRequest',
    'PredictionResponse',
    'HealthResponse',
    'ErrorResponse'
]