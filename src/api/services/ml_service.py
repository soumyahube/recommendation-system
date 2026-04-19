"""
Service Machine Learning avec Mappings
Charge les mappings depuis id_mappings.pkl
"""

import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLService:
    """Service ML avec gestion des mappings ID"""
    
    def __init__(self, 
                 model_path: str = "models/svd_best_model.pkl",
                 mappings_path: str = "models/id_mappings.pkl"):
        
        self.model = None
        self.model_path = model_path
        self.mappings_path = mappings_path
        
        # Mappings
        self.user_to_idx = {}  # Original → Factorized
        self.item_to_idx = {}  # Original → Factorized
        self.idx_to_user = {}  # Factorized → Original
        self.idx_to_item = {}  # Factorized → Original
        
        # Charger tout
        self.load_model()
        self.load_mappings()
    
    def load_model(self):
        """Charge le modèle SVD"""
        try:
            model_file = Path("/app") / self.model_path
            logger.info(f"Chargement du modèle depuis: {model_file}")
            
            with open(model_file, 'rb') as f:
                self.model = pickle.load(f)
            
            logger.info("✅ Modèle SVD chargé avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement modèle: {e}")
            raise
    
    def load_mappings(self):
        """Charge les mappings depuis id_mappings.pkl"""
        try:
            mappings_file = Path("/app") / self.mappings_path
            logger.info(f"Chargement des mappings depuis: {mappings_file}")
            
            with open(mappings_file, 'rb') as f:
                mappings = pickle.load(f)
            
            # Extraire les dictionnaires
            self.user_to_idx = mappings['user_to_idx']
            self.item_to_idx = mappings['item_to_idx']
            self.idx_to_user = mappings['idx_to_user']
            self.idx_to_item = mappings['idx_to_item']
            
            logger.info(f"✅ Mappings chargés: {len(self.user_to_idx)} users, {len(self.item_to_idx)} items")
            
        except FileNotFoundError:
            logger.warning("⚠️ Fichier id_mappings.pkl non trouvé")
            logger.warning("   → Les prédictions ne fonctionneront pas correctement")
        except Exception as e:
            logger.error(f"❌ Erreur chargement mappings: {e}")
    
    def predict_rating(self, user_id: int, movie_id: int) -> float:
        """
        Prédit la note avec mapping automatique
        
        Args:
            user_id: ID ORIGINAL de l'utilisateur (PostgreSQL)
            movie_id: ID ORIGINAL du film (PostgreSQL)
        
        Returns:
            Note prédite (0.5 à 5.0)
        """
        if self.model is None:
            raise ValueError("Modèle non chargé")
        
        try:
            # Convertir Original → Factorized
            mapped_user = self.user_to_idx.get(user_id)
            mapped_movie = self.item_to_idx.get(movie_id)
            
            # Vérifier que les IDs existent
            if mapped_user is None:
                logger.warning(f"User {user_id} inconnu dans les mappings")
                return 3.0
            
            if mapped_movie is None:
                logger.warning(f"Movie {movie_id} inconnu dans les mappings")
                return 3.0
            
            # Prédiction avec le modèle SVD (utilise les IDs factorizés)
            prediction = self.model.predict(mapped_user, mapped_movie)
            return round(prediction.est, 2)
            
        except Exception as e:
            logger.error(f"Erreur prédiction: {e}")
            return 3.0
    
    def get_top_n_recommendations(
        self, 
        user_id: int, 
        movie_ids: List[int], 
        n: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Génère les N meilleures recommandations
        
        Args:
            user_id: ID ORIGINAL de l'utilisateur
            movie_ids: Liste des IDs ORIGINAUX des films
            n: Nombre de recommandations
        
        Returns:
            Liste de (movie_id_original, predicted_rating)
        """
        
        # Vérifier que le user existe dans les mappings
        if user_id not in self.user_to_idx:
            logger.warning(f"User {user_id} inconnu")
            return []
        
        predictions = []
        for movie_id in movie_ids:
            # Prédire seulement pour les films connus
            if movie_id in self.item_to_idx:
                rating = self.predict_rating(user_id, movie_id)
                predictions.append((movie_id, rating))
        
        # Trier par note décroissante
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        return predictions[:n]
    
    def get_similar_users_recommendations(
        self,
        user_id: int,
        movie_ids: List[int],
        n_recommendations: int = 10
    ) -> List[Tuple[int, float]]:
        """Recommandations basées sur utilisateurs similaires"""
        return self.get_top_n_recommendations(user_id, movie_ids, n_recommendations)
    
    def evaluate_model_performance(self, test_data: pd.DataFrame) -> dict:
        """Évalue les performances du modèle"""
        if self.model is None:
            raise ValueError("Modèle non chargé")
        
        predictions = []
        actuals = []
        
        for _, row in test_data.iterrows():
            try:
                # Convertir les IDs originaux en factorized
                user_id = row['user_id']
                movie_id = row['movie_id']
                
                if user_id in self.user_to_idx and movie_id in self.item_to_idx:
                    pred = self.predict_rating(user_id, movie_id)
                    predictions.append(pred)
                    actuals.append(row['rating'])
            except:
                continue
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        # Calcul des métriques
        rmse = np.sqrt(np.mean((predictions - actuals) ** 2))
        mae = np.mean(np.abs(predictions - actuals))
        
        return {
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "n_predictions": len(predictions)
        }

# Instance globale
ml_service = MLService()
