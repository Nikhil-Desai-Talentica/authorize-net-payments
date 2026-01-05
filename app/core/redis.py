"""Redis connection utilities"""
from redis import Redis
from rq import Queue

from app.core.config import settings


def get_redis_client() -> Redis:
    return Redis.from_url(settings.REDIS_URL)


def get_queue(name: str = "webhooks") -> Queue:
    redis_client = get_redis_client()
    return Queue(name, connection=redis_client)
