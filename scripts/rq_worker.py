#!/usr/bin/env python
"""RQ worker entrypoint"""
import os
from rq import Worker, Queue

from app.core.redis import get_redis_client


def main():
    redis_conn = get_redis_client()
    queues = [Queue(name, connection=redis_conn) for name in os.getenv("RQ_QUEUES", "webhooks").split(",")]
    worker = Worker(queues, connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    main()
