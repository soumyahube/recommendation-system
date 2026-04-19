"""
Dashboard Streamlit Simple - Système de Recommandation de Films
Version sans API - Charge directement le modèle SVD
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration de la page
st.set_page_config(
    page_title="CineMatch - Recommandation de Films",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé Netflix
st.markdown("""
<style>
    .stApp {
        background-color: #141414;
        color: #ffffff;
    }
    
    [data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #2d2d2d;
    }
    
    h1, h2, h3 {
        color: #E50914 !important;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
    }
    
    .movie-card {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border: 2px solid #2d2d2d;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .movie-card:hover {
        transform: translateY(-8px) scale(1.02);
        border-color: #E50914;
        box-shadow: 0 12px 24px rgba(229, 9, 20, 0.4);
    }
    
    .stat-card {
        background: linear-gradient(135deg, #E50914 0%, #b20710 100%);
        border-radius: 12px;
        padding: 25px;
        text-align: center;
        box-shadow: 0 8px 16px rgba(229, 9, 20, 0.3);
    }
    
    .stat-number {
        font-size: 48px;
        font-weight: 700;
        color: #ffffff;
    }
    
    .stat-label {
        font-size: 18px;
        color: #ffffff;
        opacity: 0.9;
    }
    
    .genre-badge {
        display: inline-block;
        background-color: #E50914;
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        margin: 3px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .stButton>button {
        background-color: #E50914;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 12px 24px;
        font-weight: 600;
    }
    
    .stButton>button:hover {
        background-color: #b20710;
        transform: scale(1.05);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONFIGURATION - MODIFIEZ ICI VOS PARAMÈTRES
# ============================================================================

# Chemin vers votre modèle SVD (ajustez selon votre structure)
MODEL_PATH = "svd_best_model.pkl"  # Changez si nécessaire

# Configuration PostgreSQL (optionnel - laissez vide pour utiliser des données demo)
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "movielens",
    "user": "postgres",
    "password": "postgres"  # CHANGEZ ICI
}

USE_DATABASE = False  # Mettez True pour utiliser PostgreSQL, False pour données demo

# ============================================================================
# FONCTIONS DE CHARGEMENT
# ============================================================================

@st.cache_resource
def load_svd_model():
    """Charge le modèle SVD depuis le fichier pickle"""
    try:
        # Essayer différents chemins possibles
        possible_paths = [
            MODEL_PATH,
            f"models/{MODEL_PATH}",
            f"src/ml/models/{MODEL_PATH}",
            f"../models/{MODEL_PATH}",
            f"../../models/{MODEL_PATH}"
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                st.success(f"✅ Modèle trouvé : {path}")
                with open(path, 'rb') as f:
                    model = pickle.load(f)
                st.success("✅ Modèle SVD chargé avec succès !")
                return model, True
        
        st.warning("⚠️ Modèle SVD non trouvé. Mode démonstration activé.")
        return None, False
        
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement du modèle : {e}")
        return None, False

def get_db_connection():
    """Établit une connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.warning(f"⚠️ PostgreSQL non disponible : {e}")
        return None

@st.cache_data(ttl=600)
def load_movies_from_db():
    """Charge les films depuis PostgreSQL"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        query = """
            SELECT 
                movie_id,
                title,
                genres,
                release_year
            FROM dim_movies
            ORDER BY movie_id
            LIMIT 1000
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        st.success(f"✅ {len(df)} films chargés depuis PostgreSQL")
        return df
        
    except Exception as e:
        st.warning(f"⚠️ Erreur PostgreSQL : {e}")
        return None

@st.cache_data
def load_demo_movies():
    """Charge des films de démonstration"""
    movies_data = [
        {"movie_id": 1, "title": "Toy Story (1995)", "genres": "Animation|Children|Comedy", "release_year": 1995},
        {"movie_id": 2, "title": "Jumanji (1995)", "genres": "Adventure|Children|Fantasy", "release_year": 1995},
        {"movie_id": 3, "title": "Grumpier Old Men (1995)", "genres": "Comedy|Romance", "release_year": 1995},
        {"movie_id": 6, "title": "Heat (1995)", "genres": "Action|Crime|Thriller", "release_year": 1995},
        {"movie_id": 47, "title": "Seven (a.k.a. Se7en) (1995)", "genres": "Mystery|Thriller", "release_year": 1995},
        {"movie_id": 50, "title": "Usual Suspects, The (1995)", "genres": "Crime|Mystery|Thriller", "release_year": 1995},
        {"movie_id": 110, "title": "Braveheart (1995)", "genres": "Action|Drama|War", "release_year": 1995},
        {"movie_id": 260, "title": "Star Wars: Episode IV (1977)", "genres": "Action|Adventure|Sci-Fi", "release_year": 1977},
        {"movie_id": 296, "title": "Pulp Fiction (1994)", "genres": "Comedy|Crime|Drama|Thriller", "release_year": 1994},
        {"movie_id": 318, "title": "Shawshank Redemption, The (1994)", "genres": "Crime|Drama", "release_year": 1994},
        {"movie_id": 356, "title": "Forrest Gump (1994)", "genres": "Comedy|Drama|Romance|War", "release_year": 1994},
        {"movie_id": 480, "title": "Jurassic Park (1993)", "genres": "Action|Adventure|Sci-Fi|Thriller", "release_year": 1993},
        {"movie_id": 527, "title": "Schindler's List (1993)", "genres": "Drama|War", "release_year": 1993},
        {"movie_id": 589, "title": "Terminator 2: Judgment Day (1991)", "genres": "Action|Sci-Fi", "release_year": 1991},
        {"movie_id": 593, "title": "Silence of the Lambs, The (1991)", "genres": "Crime|Horror|Thriller", "release_year": 1991},
        {"movie_id": 1196, "title": "Star Wars: Episode V (1980)", "genres": "Action|Adventure|Sci-Fi", "release_year": 1980},
        {"movie_id": 1198, "title": "Raiders of the Lost Ark (1981)", "genres": "Action|Adventure", "release_year": 1981},
        {"movie_id": 1210, "title": "Star Wars: Episode VI (1983)", "genres": "Action|Adventure|Sci-Fi", "release_year": 1983},
        {"movie_id": 1270, "title": "Back to the Future (1985)", "genres": "Adventure|Comedy|Sci-Fi", "release_year": 1985},
        {"movie_id": 2571, "title": "Matrix, The (1999)", "genres": "Action|Sci-Fi|Thriller", "release_year": 1999},
        {"movie_id": 2959, "title": "Fight Club (1999)", "genres": "Action|Crime|Drama|Thriller", "release_year": 1999},
        {"movie_id": 4993, "title": "Lord of the Rings: The Fellowship (2001)", "genres": "Adventure|Fantasy", "release_year": 2001},
        {"movie_id": 5952, "title": "Lord of the Rings: The Two Towers (2002)", "genres": "Adventure|Fantasy", "release_year": 2002},
        {"movie_id": 7153, "title": "Lord of the Rings: The Return (2003)", "genres": "Action|Adventure|Drama|Fantasy", "release_year": 2003},
        {"movie_id": 58559, "title": "Dark Knight, The (2008)", "genres": "Action|Crime|Drama|IMAX", "release_year": 2008},
        {"movie_id": 79132, "title": "Inception (2010)", "genres": "Action|Crime|Drama|Mystery|Sci-Fi|Thriller|IMAX", "release_year": 2010},
        {"movie_id": 122882, "title": "Interstellar (2014)", "genres": "Sci-Fi|IMAX", "release_year": 2014},
        {"movie_id": 193565, "title": "Avengers: Infinity War (2018)", "genres": "Action|Adventure|Sci-Fi", "release_year": 2018},
    ]
    
    df = pd.DataFrame(movies_data)
    st.info(f"ℹ️ Mode démonstration : {len(df)} films chargés")
    return df

def predict_rating(model, user_id, movie_id):
    """Prédit la note pour un couple (utilisateur, film)"""
    try:
        if model is None:
            # Simulation si pas de modèle
            return round(np.random.uniform(3.0, 5.0), 2)
        
        prediction = model.predict(user_id, movie_id)
        return round(prediction.est, 2)
    except Exception as e:
        st.error(f"Erreur de prédiction : {e}")
        return 3.5

def get_recommendations(model, movies_df, user_id, n=10, genre_filter=None):
    """Génère des recommandations personnalisées"""
    try:
        # Filtrer par genre si nécessaire
        if genre_filter and genre_filter != "Tous":
            filtered_movies = movies_df[movies_df['genres'].str.contains(genre_filter, na=False)]
        else:
            filtered_movies = movies_df
        
        if filtered_movies.empty:
            st.warning("Aucun film trouvé avec ce filtre")
            return pd.DataFrame()
        
        # Prédire les notes pour tous les films
        predictions = []
        for _, movie in filtered_movies.iterrows():
            pred_rating = predict_rating(model, user_id, movie['movie_id'])
            predictions.append({
                'movie_id': movie['movie_id'],
                'title': movie['title'],
                'genres': movie['genres'],
                'release_year': movie.get('release_year'),
                'predicted_rating': pred_rating
            })
        
        # Créer un DataFrame et trier
        recommendations_df = pd.DataFrame(predictions)
        recommendations_df = recommendations_df.sort_values('predicted_rating', ascending=False)
        
        return recommendations_df.head(n)
        
    except Exception as e:
        st.error(f"Erreur lors de la génération des recommandations : {e}")
        return pd.DataFrame()

def display_movie_card(movie, show_prediction=False):
    """Affiche une carte de film stylisée"""
    genres = movie.get('genres', '').split('|')[:3]
    genres_html = ' '.join([f'<span class="genre-badge">{g}</span>' for g in genres])
    
    prediction_html = ""
    if show_prediction and 'predicted_rating' in movie:
        rating = movie['predicted_rating']
        stars = '⭐' * int(rating)
        prediction_html = f"""
        <div style='margin-top: 10px; padding-top: 10px; border-top: 1px solid #E50914;'>
            <div style='color: #FFD700; font-weight: 600;'>Note prédite: {rating:.1f}/5.0</div>
            <div style='color: #FFD700;'>{stars}</div>
        </div>
        """
    
    year_display = f" • 📅 {movie.get('release_year')}" if movie.get('release_year') else ""
    
    card_html = f"""
    <div class='movie-card'>
        <h3 style='color: #ffffff; margin-bottom: 10px;'>{movie.get('title', 'N/A')}</h3>
        <div style='margin: 10px 0;'>{genres_html}</div>
        <div style='color: #b3b3b3; margin: 8px 0;'>
            🎬 ID: {movie.get('movie_id', 'N/A')}{year_display}
        </div>
        {prediction_html}
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)

# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================

# Charger le modèle
model, model_loaded = load_svd_model()

# Charger les films
if USE_DATABASE:
    movies_df = load_movies_from_db()
    if movies_df is None:
        movies_df = load_demo_movies()
else:
    movies_df = load_demo_movies()

# Extraire les genres uniques
all_genres = set()
for genres_str in movies_df['genres']:
    if pd.notna(genres_str):
        all_genres.update(genres_str.split('|'))
all_genres = sorted(list(all_genres))

# ============================================================================
# INTERFACE STREAMLIT
# ============================================================================

# Sidebar
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #E50914;'>🎬 CineMatch</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #b3b3b3;'>Système de Recommandation</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Statut
    if model_loaded:
        st.success("✅ Modèle SVD Chargé")
    else:
        st.warning("⚠️ Mode Démonstration")
    
    if USE_DATABASE and movies_df is not None and len(movies_df) > 50:
        st.success("✅ PostgreSQL Connecté")
    else:
        st.info("ℹ️ Données Demo")
    
    st.markdown("---")
    
    page = st.radio(
        "Navigation",
        ["🏠 Accueil", "🎯 Recommandations", "🎬 Catalogue", "🔮 Prédiction"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #b3b3b3; font-size: 12px;'>
        <p>Version Simple</p>
        <p>Streamlit + SVD Direct</p>
        <p style='margin-top: 20px;'>© 2024 CineMatch</p>
    </div>
    """, unsafe_allow_html=True)

# PAGE: ACCUEIL
if page == "🏠 Accueil":
    st.markdown("<h1 style='text-align: center; font-size: 56px;'>🎬 Bienvenue sur CineMatch</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 20px; color: #b3b3b3; margin-bottom: 40px;'>Système de recommandation avec SVD</p>", unsafe_allow_html=True)
    
    # Statistiques
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number'>{len(movies_df)}</div>
            <div class='stat-label'>Films</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number'>{len(all_genres)}</div>
            <div class='stat-label'>Genres</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        status = "SVD" if model_loaded else "DEMO"
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number'>{status}</div>
            <div class='stat-label'>Modèle</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number'>DIRECT</div>
            <div class='stat-label'>Mode</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><h2>🎬 Aperçu du Catalogue</h2>", unsafe_allow_html=True)
    
    # Afficher quelques films
    cols = st.columns(3)
    for idx, (_, movie) in enumerate(movies_df.head(6).iterrows()):
        with cols[idx % 3]:
            display_movie_card(movie)

# PAGE: RECOMMANDATIONS
elif page == "🎯 Recommandations":
    st.markdown("<h1>🎯 Recommandations Personnalisées</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        user_id = st.number_input(
            "ID Utilisateur",
            min_value=1,
            max_value=100000,
            value=1,
            help="Entrez l'ID de l'utilisateur pour obtenir des recommandations"
        )
    
    with col2:
        n_reco = st.slider(
            "Nombre de recommandations",
            min_value=5,
            max_value=20,
            value=10
        )
    
    with col3:
        genre_filter = st.selectbox(
            "Filtrer par genre",
            ["Tous"] + all_genres
        )
    
    if st.button("🎬 Générer les Recommandations", type="primary", use_container_width=True):
        with st.spinner("Génération des recommandations..."):
            genre_param = None if genre_filter == "Tous" else genre_filter
            recommendations = get_recommendations(model, movies_df, user_id, n=n_reco, genre_filter=genre_param)
        
        if not recommendations.empty:
            st.success(f"✅ {len(recommendations)} recommandations générées !")
            
            st.markdown("<h2>🎬 Vos Films Recommandés</h2>", unsafe_allow_html=True)
            
            cols = st.columns(3)
            for idx, (_, movie) in enumerate(recommendations.iterrows()):
                with cols[idx % 3]:
                    display_movie_card(movie, show_prediction=True)
        else:
            st.warning("Aucune recommandation trouvée.")

# PAGE: CATALOGUE
elif page == "🎬 Catalogue":
    st.markdown("<h1>🎬 Catalogue de Films</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        genre_filter = st.selectbox("Filtrer par genre", ["Tous"] + all_genres)
    
    with col2:
        search_term = st.text_input("🔍 Rechercher un film", "")
    
    # Filtrer les films
    filtered_movies = movies_df.copy()
    
    if genre_filter != "Tous":
        filtered_movies = filtered_movies[filtered_movies['genres'].str.contains(genre_filter, na=False)]
    
    if search_term:
        filtered_movies = filtered_movies[filtered_movies['title'].str.contains(search_term, case=False, na=False)]
    
    st.markdown(f"<h2>📊 {len(filtered_movies)} Films Trouvés</h2>", unsafe_allow_html=True)
    
    if not filtered_movies.empty:
        cols = st.columns(4)
        for idx, (_, movie) in enumerate(filtered_movies.head(20).iterrows()):
            with cols[idx % 4]:
                display_movie_card(movie)
    else:
        st.warning("Aucun film trouvé avec ces critères.")

# PAGE: PRÉDICTION
elif page == "🔮 Prédiction":
    st.markdown("<h1>🔮 Prédire une Note</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #b3b3b3;'>Prédisez la note qu'un utilisateur donnerait à un film</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        user_id = st.number_input(
            "ID Utilisateur",
            min_value=1,
            max_value=100000,
            value=1
        )
    
    with col2:
        movie_id = st.number_input(
            "ID Film",
            min_value=1,
            max_value=200000,
            value=1
        )
    
    if st.button("🔮 Prédire la Note", type="primary", use_container_width=True):
        with st.spinner("Calcul de la prédiction..."):
            rating = predict_rating(model, user_id, movie_id)
        
        stars = '⭐' * int(rating)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #E50914 0%, #b20710 100%); 
                        padding: 40px; border-radius: 20px; text-align: center;
                        box-shadow: 0 12px 24px rgba(229, 9, 20, 0.5);'>
                <h2 style='color: white; margin: 0;'>Note Prédite</h2>
                <div style='font-size: 72px; color: white; margin: 20px 0;'>{rating:.2f}</div>
                <div style='font-size: 48px;'>{stars}</div>
                <p style='color: white; opacity: 0.9; margin-top: 20px;'>
                    Utilisateur #{user_id} • Film #{movie_id}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Trouver le film dans le catalogue
        movie_info = movies_df[movies_df['movie_id'] == movie_id]
        if not movie_info.empty:
            st.markdown("<br><h3>📝 Détails du Film</h3>", unsafe_allow_html=True)
            display_movie_card(movie_info.iloc[0])

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #b3b3b3; padding: 20px;'>
    <p style='font-size: 16px;'>🎬 CineMatch - Système de Recommandation Simple</p>
    <p style='font-size: 14px;'>Streamlit + SVD Direct (Sans API)</p>
</div>
""", unsafe_allow_html=True)