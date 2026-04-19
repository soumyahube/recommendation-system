FROM python:3.10

WORKDIR /app

# Copier requirements
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Lancer le consumer
CMD ["python", "consumer.py"]