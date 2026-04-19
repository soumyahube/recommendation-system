"""
FastAPI Backend pour le système de recommandation de films
Point d'entrée principal de l'API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="Movie Recommendation API",
    description="API de recommandation de films basée sur SVD",
    version="1.0.0"
)

# Configuration CORS pour permettre Streamlit de communiquer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import des routers
from routers import recommendations, movies

# Enregistrement des routers
app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(movies.router, prefix="/api/v1", tags=["Movies"])

@app.get("/")
async def root():
    """Endpoint racine de l'API"""
    return {
        "message": "Movie Recommendation API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "recommendations": "/api/v1/recommend/{user_id}",
            "movies": "/api/v1/movies",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Vérification de l'état de l'API"""
    return {
        "status": "healthy",
        "service": "movie-recommendation-api"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload en développement
    )