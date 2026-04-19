-- data/database/schema_simple.sql
-- ============================================
-- SCHÉMA MINIMAL POUR DÉMARRER RAPIDEMENT
-- ============================================

-- Supprimer les tables si elles existent (pour reprise)
DROP TABLE IF EXISTS fact_ratings CASCADE;
DROP TABLE IF EXISTS dim_users CASCADE;
DROP TABLE IF EXISTS dim_movies CASCADE;

-- 1. TABLE DIMENSION : FILMS
CREATE TABLE dim_movies (
    movie_key SERIAL PRIMARY KEY,
    movie_id INT UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    genres TEXT,
    -- Colonnes réservées pour extensions futures
    tmdb_id INT,
    imdb_id VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABLE DIMENSION : UTILISATEURS
CREATE TABLE dim_users (
    user_key SERIAL PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. TABLE DE FAITS : NOTES
CREATE TABLE fact_ratings (
    rating_id BIGSERIAL PRIMARY KEY,
    user_key INT NOT NULL REFERENCES dim_users(user_key),
    movie_key INT NOT NULL REFERENCES dim_movies(movie_key),
    rating DECIMAL(2,1) NOT NULL CHECK (rating >= 0.5 AND rating <= 5.0),
    timestamp BIGINT NOT NULL,
    -- Pour analyses temporelles simples
    rating_date DATE GENERATED ALWAYS AS (
        DATE '1970-01-01' + (timestamp / 86400) * INTERVAL '1 day'
    ) STORED,
    -- Un utilisateur ne peut noter un film qu'une fois
    UNIQUE(user_key, movie_key)
);

-- ============================================
-- INDEX POUR PERFORMANCES
-- ============================================

-- Pour les jointures rapides
CREATE INDEX idx_ratings_user ON fact_ratings(user_key);
CREATE INDEX idx_ratings_movie ON fact_ratings(movie_key);
CREATE INDEX idx_ratings_timestamp ON fact_ratings(timestamp);
CREATE INDEX idx_ratings_date ON fact_ratings(rating_date);

-- Pour les recherches
CREATE INDEX idx_movies_title ON dim_movies(title);
CREATE INDEX idx_movies_genres ON dim_movies(genres);

-- ============================================
-- VUES UTILES POUR ANALYSES SIMPLES
-- ============================================

-- Vue : Statistiques utilisateurs
CREATE OR REPLACE VIEW vw_user_stats AS
SELECT 
    u.user_id,
    COUNT(r.rating_id) as total_ratings,
    ROUND(AVG(r.rating), 2) as avg_rating,
    MIN(r.rating_date) as first_rating,
    MAX(r.rating_date) as last_rating
FROM dim_users u
LEFT JOIN fact_ratings r ON u.user_key = r.user_key
GROUP BY u.user_id;

-- Vue : Statistiques films
CREATE OR REPLACE VIEW vw_movie_stats AS
SELECT 
    m.movie_id,
    m.title,
    m.genres,
    COUNT(r.rating_id) as total_ratings,
    ROUND(AVG(r.rating), 2) as avg_rating,
    MIN(r.rating_date) as first_rating,
    MAX(r.rating_date) as last_rating
FROM dim_movies m
LEFT JOIN fact_ratings r ON m.movie_key = r.movie_key
GROUP BY m.movie_id, m.title, m.genres;