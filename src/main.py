from config import settings, get_connection_string
from checkpoint import CheckpointManager
from database import SalesOrderRepository
from handlers.first_time_handler import (
    FirstTimeHandler,
)
from handlers.change_handler import (
    ChangeHandler,
)
from services.order_processor import (
    OrderProcessor,
)
from poller import Poller
from logging_config import setup_logging
from mailer import EmailService
import logging
logger = logging.getLogger(__name__)
setup_logging()
repository = SalesOrderRepository(
    get_connection_string()
)
checkpoint = CheckpointManager(
    settings.checkpoint_file
)
emailer=EmailService(
    settings.SENDER2,
    settings.SENDER_PASSWORD2
)
processor = OrderProcessor(
    repository,
    FirstTimeHandler(),
    ChangeHandler(),
    emailer
)

poller = Poller(
    repository,
    checkpoint,
    processor,
    interval=1
)
try:
    poller.run()
except KeyboardInterrupt:
    logger.info("Shutdown requested")