import logging
logger = logging.getLogger(__name__)

class FirstTimeHandler:
    def process(self, order):
        logger.info(f"[FIRST] {order.number}")
        