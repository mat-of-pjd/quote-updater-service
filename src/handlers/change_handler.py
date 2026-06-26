import logging
logger = logging.getLogger(__name__)

class ChangeHandler:
    def process(self, order):
        logger.info(f"[CHANGE] {order.number}")
