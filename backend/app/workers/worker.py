"""Worker entrypoint: ``python -m app.workers.worker``."""

from rq import Worker

from app.core.logging import configure_logging, get_logger
from app.workers.queues import get_connection, get_queue

logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    queue = get_queue()
    logger.info("worker listening on queue %s", queue.name)
    Worker([queue], connection=get_connection()).work(with_scheduler=False)


if __name__ == "__main__":
    main()
