FROM apache/airflow:2.8.0

USER root

# Installer les dépendances système pour scikit-surprise
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Installer les packages Python nécessaires (versions compatibles)
RUN pip install --no-cache-dir \
    scikit-surprise==1.1.3 \
    numpy==1.24.4 \
    pandas==2.0.3 \
    psycopg2-binary==2.9.9 \
    sqlalchemy==1.4.54