from kafka import KafkaProducer
import json
import logging
import datetime

logger = logging.getLogger(__name__)

class KafkaProducerService:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=['kafka:29092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logger.info("✅ Kafka Producer connecté")
    
    def send_rating(self, user_id: int, movie_id: int, rating: float):
        """Envoie une nouvelle notation à Kafka"""
        message = {
            "user_id": user_id,
            "movie_id": movie_id,
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        }
        
        self.producer.send('new-ratings', value=message)
        self.producer.flush()
        logger.info(f"📤 Rating envoyé à Kafka: {message}")

kafka_producer = None

def get_kafka_producer():
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = KafkaProducerService()  # créé seulement quand nécessaire
    return kafka_producer