# 🎬 Movie Recommendation System - Data Engineering Project

## 🚀 Overview
End-to-end movie recommendation system with SVD algorithm, featuring complete data engineering pipeline.

## 🏗️ Architecture
- **Data Ingestion**: MovieLens 25M → PostgreSQL (Star Schema)
- **Feature Engineering**: SQL + Python features
- **ML Pipeline**: SVD training on Parquet files
- **API**: FastAPI with Redis caching
- **Dashboard**: Streamlit visualization

## 🛠️ Setup
```bash
git clone https://github.com/yourusername/movie-recommendation-system
cd movie-recommendation-system
make setup
make run-pipeline