"""
Dashboard Streamlit pour le système de recommandation de films
Communique avec l'API FastAPI backend
"""

import streamlit as st
import requests
import pandas as pd
from typing import List, Dict
import time
import re
import os
from utils_tmdb import get_poster_url, get_movie_details_tmdb
import re

# Configuration de la page - DOIT ÊTRE LA PREMIÈRE COMMANDE STREAMLIT
st.set_page_config(
    page_title="CineMatch - Recommandation de Films",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL de l'API FastAPI (à adapter selon votre configuration)
API_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000/api/v1")

# IMPORTANT: Définir toutes les fonctions AVANT de les utiliser
# =============================================================

def check_api_health():
    """Vérifie si l'API est accessible"""
    try:
        response = requests.get(f"{API_URL.replace('/api/v1', '')}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

@st.cache_data(ttl=300)
def get_movies(limit=100, genre=None):
    """Récupère la liste des films depuis l'API"""
    try:
        params = {"limit": limit}
        if genre:
            params["genre"] = genre
        
        response = requests.get(f"{API_URL}/movies", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des films: {e}")
        return []

@st.cache_data(ttl=300)
def get_genres():
    """Récupère la liste des genres disponibles"""
    try:
        response = requests.get(f"{API_URL}/genres", timeout=5)
        response.raise_for_status()
        return response.json()["genres"]
    except Exception as e:
        st.error(f"Erreur lors de la récupération des genres: {e}")
        return []

def get_recommendations(user_id, n=10, genre=None):
    """Récupère les recommandations pour un utilisateur"""
    try:
        params = {"n": n}
        if genre:
            params["genre"] = genre
        
        with st.spinner(f"🎬 Génération de {n} recommandations personnalisées..."):
            response = requests.get(
                f"{API_URL}/recommend/{user_id}",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération des recommandations: {e}")
        return None

def predict_rating(user_id, movie_id):
    """Prédit la note pour un couple (utilisateur, film)"""
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json={"user_id": user_id, "movie_id": movie_id},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors de la prédiction: {e}")
        return None

def get_movie_details(movie_id):
    """Récupère les détails d'un film"""
    try:
        response = requests.get(f"{API_URL}/movies/{movie_id}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors de la récupération du film: {e}")
        return None

def search_movie_ids(title, year=None):
    """Retourne TMDb ID et IMDB ID pour un film donné par son titre et éventuellement année"""
    TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
    if not TMDB_API_KEY:
        return None, None
        
    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
        if year:
            url += f"&year={year}"
        resp = requests.get(url, timeout=5).json()
        results = resp.get("results")
        if results and len(results) > 0:
            tmdb_id = results[0]["id"]
            # Récupérer IMDB ID via le détail du film
            detail = requests.get(f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}", timeout=5).json()
            imdb_id = detail.get("imdb_id")
            return tmdb_id, imdb_id
    except Exception as e:
        print(f"Erreur récupération IDs: {e}")
    return None, None

def get_movie_poster(tmdb_id=None, imdb_id=None, title=None, year=None):
    """Retourne l'URL du poster TMDb"""
    TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
    BASE_URL = "https://image.tmdb.org/t/p/w500"
    
    if not TMDB_API_KEY:
        return None
        
    try:
        # Si on n'a ni TMDb ID ni IMDB ID mais qu'on a un titre
        if not tmdb_id and not imdb_id and title:
            tmdb_id, imdb_id = search_movie_ids(title, year)

        # Recherche par TMDb ID
        if tmdb_id:
            resp = requests.get(f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}", timeout=5).json()
            poster_path = resp.get("poster_path")
            if poster_path:
                return f"{BASE_URL}{poster_path}"

        # Recherche par IMDB ID
        if imdb_id:
            resp = requests.get(
                f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={TMDB_API_KEY}&external_source=imdb_id",
                timeout=5
            ).json()
            movie_results = resp.get("movie_results", [])
            if movie_results:
                poster_path = movie_results[0].get("poster_path")
                if poster_path:
                    return f"{BASE_URL}{poster_path}"
    except Exception as e:
        print(f"Erreur récupération poster: {e}")

    return None

def rate_movie(user_id, movie_id, rating):
    """Envoie une note dans Kafka via le producer"""
    try:
        # Note: Cette fonction nécessite que kafka_producer soit accessible
        # Si vous êtes dans Streamlit, vous devrez peut-être ajuster l'import
        from api.services.kafka_producer import get_kafka_producer
        producer = get_kafka_producer()
        producer.send_rating(user_id, movie_id, rating)
        return {"message": "Notation envoyée avec succès", 
                "data": {"user_id": user_id, "movie_id": movie_id, "rating": rating}}
    except ImportError:
        # Fallback si l'import échoue - utiliser l'API directement
        try:
            response = requests.post(
                f"{API_URL}/rate",
                json={"user_id": user_id, "movie_id": movie_id, "rating": rating},
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"❌ Erreur lors de l'envoi à Kafka: {e}")
            return None
    except Exception as e:
        st.error(f"❌ Erreur lors de l'envoi à Kafka: {e}")
        return None



def display_movie_card(movie, show_prediction=False):
    """Affiche une carte de film avec poster TMDb"""
    
    title = movie.get("title", "")
    
    # Extraire l'année du titre
    year = None
    year_match = re.search(r'\((\d{4})\)', title)
    if year_match:
        year = year_match.group(1)
    
    # Récupérer les détails TMDb
    tmdb_data = get_movie_details_tmdb(title, year)
    poster_url = tmdb_data.get("poster_url")
    overview = tmdb_data.get("overview", "")
    tmdb_rating = tmdb_data.get("vote_average", 0)
    
    # Genres
    genres = movie.get("genres", "").split("|")[:3]
    genres_html = " ".join([
        f'<span style="background:#E50914;color:white;padding:3px 10px;'
        f'border-radius:20px;margin:2px;font-size:11px;">{g}</span>'
        for g in genres if g
    ])
    
    # Note prédite
    prediction_html = ""
    if show_prediction and "predicted_rating" in movie:
        rating = movie["predicted_rating"]
        stars = "⭐" * int(rating)
        prediction_html = f"""
        <div style='margin-top:8px;padding-top:8px;border-top:1px solid #333;'>
            <span style='color:#FFD700;font-weight:bold;'>
                {stars} {rating:.1f}/5.0
            </span>
        </div>
        """
    
    # TMDb rating
    tmdb_html = ""
    if tmdb_rating:
        tmdb_html = f"""
        <div style='color:#b3b3b3;font-size:12px;margin-top:4px;'>
            🎬 TMDb: {tmdb_rating:.1f}/10
        </div>
        """
    
    # Overview
    overview_html = ""
    if overview:
        short_overview = overview[:100] + "..." if len(overview) > 100 else overview
        overview_html = f"""
        <div style='color:#b3b3b3;font-size:12px;margin-top:8px;
                    font-style:italic;'>
            {short_overview}
        </div>
        """
    
    # Carte complète
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if poster_url:
            st.image(poster_url, width=120)
        else:
            st.markdown("""
            <div style='width:120px;height:180px;background:#2d2d2d;
                        border-radius:8px;display:flex;align-items:center;
                        justify-content:center;border:2px solid #E50914;'>
                <span style='font-size:40px;'>🎬</span>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='padding:5px;'>
            <h4 style='color:white;margin:0 0 8px 0;font-size:14px;'>
                {title}
            </h4>
            <div>{genres_html}</div>
            {tmdb_html}
            {overview_html}
            {prediction_html}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<hr style='border-color:#2d2d2d;margin:5px 0;'>", 
                unsafe_allow_html=True)
# CSS personnalisé Netflix (global)
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

# =============================================================
# DÉBUT DE L'INTERFACE UTILISATEUR
# =============================================================

# Sidebar - Navigation
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #E50914;'>🎬 CineMatch</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #b3b3b3;'>Système de Recommandation Intelligent</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Vérifier l'état de l'API
    api_status = check_api_health()
    if api_status:
        st.success("✅ API Connectée")
    else:
        st.error("❌ API Non Disponible")
        st.warning("Assurez-vous que FastAPI est lancé")
    
    st.markdown("---")
    
    page = st.radio(
        "Navigation",
        ["🏠 Accueil",  "👤 Mon Profil","🎯 Recommandations", "🎬 Catalogue", "🔮 Prédiction"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #b3b3b3; font-size: 12px;'>
        <p>Architecture:</p>
        <p>FastAPI + Streamlit + SVD</p>
        <p style='margin-top: 20px;'>© 2024 CineMatch</p>
    </div>
    """, unsafe_allow_html=True)

# PAGE: ACCUEIL
if page == "🏠 Accueil":
    st.markdown("<h1 style='text-align: center; font-size: 56px;'>🎬 Bienvenue sur CineMatch</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 20px; color: #b3b3b3; margin-bottom: 40px;'>Système de recommandation avec Machine Learning (SVD)</p>", unsafe_allow_html=True)
    
    if not api_status:
        st.error("⚠️ L'API FastAPI n'est pas accessible.")
        st.stop()
    
    # Statistiques
    with st.spinner("Chargement des données..."):
        movies = get_movies(limit=500)
        genres = get_genres()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number'>{len(movies)}</div>
            <div class='stat-label'>Films</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number'>{len(genres)}</div>
            <div class='stat-label'>Genres</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number'>SVD</div>
            <div class='stat-label'>Modèle ML</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='stat-card'>
            <div class='stat-number'>API</div>
            <div class='stat-label'>Architecture</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Quelques films
    st.markdown("<h2>🎬 Aperçu du Catalogue</h2>", unsafe_allow_html=True)
    
    if movies:
        cols = st.columns(3)
        for idx, movie in enumerate(movies[:6]):
            with cols[idx % 3]:
                display_movie_card(movie)

# PAGE: RECOMMANDATIONS
elif page == "👤 Mon Profil":
    st.markdown("<h1>👤 Crée ton Profil Cinéma</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#b3b3b3'>Note quelques films pour recevoir des recommandations 100% personnalisées</p>", unsafe_allow_html=True)

    # ── ÉTAPE 1 : Genres préférés ──────────────────────────────
    st.markdown("<h2>🎭 Tes genres préférés</h2>", unsafe_allow_html=True)

    all_genres = [
        "Action", "Adventure", "Animation", "Comedy", "Crime",
        "Documentary", "Drama", "Fantasy", "Horror", "Mystery",
        "Romance", "Sci-Fi", "Thriller", "War", "Western"
    ]

    selected_genres = st.multiselect(
        "Choisis jusqu'à 5 genres",
        all_genres,
        max_selections=5,
        default=["Action", "Comedy"]
    )

    # ── ÉTAPE 2 : Noter des films populaires ──────────────────
    st.markdown("<h2>⭐ Note quelques films que tu connais</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#b3b3b3'>Laisse 0 si tu ne l'as pas vu</p>", unsafe_allow_html=True)

    popular_movies = {
        1:      "Toy Story (1995)",
        260:    "Star Wars (1977)",
        296:    "Pulp Fiction (1994)",
        318:    "Shawshank Redemption (1994)",
        356:    "Forrest Gump (1994)",
        480:    "Jurassic Park (1993)",
        2571:   "Matrix, The (1999)",
        58559:  "Dark Knight (2008)",
        79132:  "Inception (2010)",
        122882: "Interstellar (2014)"
    }

    user_ratings = {}
    cols = st.columns(2)
    for idx, (movie_id, title) in enumerate(popular_movies.items()):
        with cols[idx % 2]:
            rating = st.select_slider(
                title,
                options=[0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
                value=0,
                key=f"rating_{movie_id}"
            )
            if rating > 0:
                user_ratings[movie_id] = rating

    # ── ÉTAPE 3 : Préférences supplémentaires ─────────────────
    st.markdown("<h2>🎬 Dernières préférences</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        era = st.radio(
            "Époque préférée",
            ["Peu importe", "Classiques (avant 1990)",
             "Années 90-2000", "Films récents (après 2010)"]
        )

    with col2:
        mood = st.radio(
            "Humeur du moment",
            ["Peu importe", "Quelque chose de fun 😄",
             "Film intense 😮", "Histoire touchante 😢",
             "Faire peur 😱"]
        )

    # ── BOUTON GÉNÉRER ─────────────────────────────────────────
    if st.button("🎯 Générer mes recommandations personnalisées",
                 type="primary", use_container_width=True):

        if not selected_genres and not user_ratings:
            st.warning("⚠️ Choisis au moins un genre ou note un film !")
        else:
            with st.spinner("🤖 Analyse de tes préférences en cours..."):

                # Choisir le user_id de référence selon les genres
                genre_to_user = {
                    "Action": 1, "Adventure": 2, "Animation": 3,
                    "Comedy": 4, "Crime": 5, "Documentary": 6,
                    "Drama": 7, "Fantasy": 8, "Horror": 9,
                    "Mystery": 10, "Romance": 11, "Sci-Fi": 12,
                    "Thriller": 13, "War": 14, "Western": 15
                }
                base_user = genre_to_user.get(
                    selected_genres[0] if selected_genres else "Drama", 7
                )

                # Filtrer par époque
                era_filter = None
                if era == "Classiques (avant 1990)":
                    era_filter = lambda t: any(
                        str(y) in t for y in range(1900, 1990)
                    )
                elif era == "Années 90-2000":
                    era_filter = lambda t: any(
                        str(y) in t for y in range(1990, 2001)
                    )
                elif era == "Films récents (après 2010)":
                    era_filter = lambda t: any(
                        str(y) in t for y in range(2010, 2030)
                    )

                # Récupérer recommandations pour chaque genre choisi
                all_reco = []
                genres_to_search = selected_genres[:3] if selected_genres else ["Drama"]

                for genre in genres_to_search:
                    try:
                        response = requests.get(
                            f"{API_URL}/recommend/{base_user}",
                            params={"n": 15, "genre": genre},
                            timeout=15
                        )
                        if response.status_code == 200:
                            data = response.json()
                            all_reco.extend(data.get("recommendations", []))
                    except Exception as e:
                        st.warning(f"Erreur pour le genre {genre}: {e}")

                # Dédupliquer
                seen = set()
                unique_reco = []
                for movie in all_reco:
                    mid = movie['movie_id']
                    if mid not in seen and mid not in user_ratings:
                        seen.add(mid)
                        # Appliquer filtre époque
                        if era_filter is None or era_filter(movie.get('title', '')):
                            unique_reco.append(movie)

                # Boost des films selon l'humeur
                mood_genres = {
                    "Quelque chose de fun 😄": ["Comedy", "Animation"],
                    "Film intense 😮": ["Thriller", "Action"],
                    "Histoire touchante 😢": ["Drama", "Romance"],
                    "Faire peur 😱": ["Horror", "Mystery"]
                }
                if mood in mood_genres:
                    boost_genres = mood_genres[mood]
                    def boost_score(m):
                        bonus = 0.3 if any(
                            g in m.get('genres', '') for g in boost_genres
                        ) else 0
                        return m['predicted_rating'] + bonus
                    unique_reco.sort(key=boost_score, reverse=True)
                else:
                    unique_reco.sort(
                        key=lambda x: x['predicted_rating'], reverse=True
                    )

            # ── AFFICHAGE DES RÉSULTATS ────────────────────────
            if unique_reco:
                st.success(f"✅ {len(unique_reco)} films trouvés rien que pour toi !")

                # Résumé du profil
                st.markdown(f"""
                <div style='background:#1a1a1a;border:1px solid #E50914;
                            border-radius:12px;padding:20px;margin:15px 0;'>
                    <h3 style='color:#E50914;margin:0 0 10px 0;'>🎭 Ton profil</h3>
                    <p style='color:#b3b3b3;margin:4px 0;'>
                        Genres : <b style='color:white'>{', '.join(selected_genres) if selected_genres else 'Non spécifié'}</b>
                    </p>
                    <p style='color:#b3b3b3;margin:4px 0;'>
                        Films notés : <b style='color:white'>{len(user_ratings)}</b>
                    </p>
                    <p style='color:#b3b3b3;margin:4px 0;'>
                        Humeur : <b style='color:white'>{mood}</b>
                    </p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<h2>🎬 Tes recommandations personnalisées</h2>",
                            unsafe_allow_html=True)

                cols = st.columns(3)
                for idx, movie in enumerate(unique_reco[:12]):
                    with cols[idx % 3]:
                        display_movie_card(movie, show_prediction=True)
            else:
                st.warning("Aucune recommandation trouvée. Essaie d'autres genres ou une autre époque.")
                
                             
elif page == "🎯 Recommandations":
    st.markdown("<h1>🎯 Recommandations Personnalisées</h1>", unsafe_allow_html=True)
    
    if not api_status:
        st.error("⚠️ L'API n'est pas accessible")
        st.stop()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        user_id = st.number_input(
            "ID Utilisateur",
            min_value=1,
            max_value=100000,
            value=1,
            help="Entrez l'ID de l'utilisateur"
        )
    
    with col2:
        n_reco = st.slider(
            "Nombre de recommandations",
            min_value=5,
            max_value=50,
            value=12
        )
    
    with col3:
        genres = get_genres()
        genre_filter = st.selectbox(
            "Filtrer par genre",
            ["Tous"] + genres
        )
    
    if st.button("🎬 Générer les Recommandations", type="primary", use_container_width=True):
        genre_param = None if genre_filter == "Tous" else genre_filter
        
        recommendations = get_recommendations(user_id, n=n_reco, genre=genre_param)
        
        if recommendations:
            st.success(f"✅ {recommendations['total_count']} recommandations générées !")
            
            st.markdown("<h2>🎬 Vos Films Recommandés</h2>", unsafe_allow_html=True)
            
            # Afficher en grille de 3 colonnes
            reco_list = recommendations['recommendations']
            cols = st.columns(3)
            for idx, movie in enumerate(reco_list):
                with cols[idx % 3]:
                    display_movie_card(movie, show_prediction=True)

    st.markdown("<br><h2>⭐ Tester la Notation en Temps Réel (Kafka)</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
       test_user_id = st.number_input("User ID", min_value=1, value=7, key="test_user")

    with col2:
       test_movie_id = st.number_input("Movie ID", min_value=1, value=1, key="test_movie")

    with col3:
       test_rating = st.slider("Note", min_value=0.5, max_value=5.0, value=4.0, step=0.5, key="test_rating")

    if st.button("📤 Envoyer la Notation à Kafka", type="primary"):
        result = rate_movie(test_user_id, test_movie_id, test_rating)
    
        if result:
          st.success(f"✅ {result['message']}")
          st.json(result['data'])
          st.info("💡 Vérifiez Kafka UI (http://localhost:8080) pour voir le message !")

# PAGE: CATALOGUE
elif page == "🎬 Catalogue":
    st.markdown("<h1>🎬 Catalogue de Films</h1>", unsafe_allow_html=True)
    
    if not api_status:
        st.error("⚠️ L'API n'est pas accessible")
        st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        genres = get_genres()
        genre_filter = st.selectbox("Filtrer par genre", ["Tous"] + genres)
    
    with col2:
        limit = st.slider("Nombre de films", 10, 500, 100)
    
    with st.spinner("Chargement des films..."):
        genre_param = None if genre_filter == "Tous" else genre_filter
        movies = get_movies(limit=limit, genre=genre_param)
    
    st.markdown(f"<h2>📊 {len(movies)} Films Trouvés</h2>", unsafe_allow_html=True)
    
    if movies:
        # Afficher en grille
        cols = st.columns(4)
        for idx, movie in enumerate(movies):
            with cols[idx % 4]:
                display_movie_card(movie)

# PAGE: PRÉDICTION
elif page == "🔮 Prédiction":
    st.markdown("<h1>🔮 Prédire une Note</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #b3b3b3;'>Prédisez la note qu'un utilisateur donnerait à un film</p>", unsafe_allow_html=True)
    
    if not api_status:
        st.error("⚠️ L'API n'est pas accessible")
        st.stop()
    
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
            max_value=100000,
            value=1
        )
    
    if st.button("🔮 Prédire la Note", type="primary", use_container_width=True):
        with st.spinner("Calcul de la prédiction..."):
            prediction = predict_rating(user_id, movie_id)
        
        if prediction:
            rating = prediction['predicted_rating']
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
                        {prediction.get('movie_title', f'Film #{movie_id}')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # Récupérer les détails du film
            movie_details = get_movie_details(movie_id)
            if movie_details:
                st.markdown("<br><h3>📝 Détails du Film</h3>", unsafe_allow_html=True)
                display_movie_card(movie_details)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #b3b3b3; padding: 20px;'>
    <p style='font-size: 16px;'>🎬 CineMatch - Système de Recommandation avec SVD</p>
    <p style='font-size: 14px;'>FastAPI Backend + Streamlit Frontend + PostgreSQL</p>
</div>
""", unsafe_allow_html=True)