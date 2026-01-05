#!/usr/bin/env python
"""RQ worker entrypoint"""
import os
from rq import Connection, Worker

from app.core.redis import get_redis_client


def main():
    redis_conn = get_redis_client()
    queues = os.getenv("RQ_QUEUES", "webhooks").split(",")
    with Connection(redis_conn):
        worker = Worker(queues)
        worker.work()


if __name__ == "__main__":
    main()
