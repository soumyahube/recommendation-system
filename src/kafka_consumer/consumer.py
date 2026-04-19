from kafka import KafkaConsumer
import psycopg2
import json
import logging

logger = logging.getLogger(__name__)

consumer = KafkaConsumer(
    'new-ratings',
    bootstrap_servers=['kafka:29092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id='rating-consumers'
)

# Connexion PostgreSQL
conn = psycopg2.connect(
    host="db",
    database="movierec",
    user="admin",
    password="admin123"
)

logger.info("✅ Consumer Kafka démarré")

for message in consumer:
    rating_data = message.value
    
    logger.info(f"📥 Nouveau rating reçu: {rating_data}")
    
    # INSERT dans PostgreSQL
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fact_ratings (user_id, movie_id, rating, rating_timestamp)
            VALUES (%s, %s, %s, NOW())
            """,
            (rating_data['user_id'], rating_data['movie_id'], rating_data['rating'])
        )
        conn.commit()
        
    logger.info("✅ Rating inséré dans PostgreSQL")