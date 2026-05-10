FROM python:3.11-slim

WORKDIR /app

# JUSTE pip install (pas apt-get)
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir pandas psycopg2-binary sqlalchemy

COPY data/database/load_complete.py .

CMD ["python", "load_complete.py"]