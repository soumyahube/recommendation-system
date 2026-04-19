"""
Services FastAPI
"""

from .ml_service import ml_service
from .db_service import db_service
from .kafka_producer import kafka_producer

__all__ = ['ml_service', 'db_service', 'kafka_producer']