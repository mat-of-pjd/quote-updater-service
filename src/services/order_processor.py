import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from report_status import report_status

class OrderProcessor:
    def __init__(
        self,
        repository,
        first_handler,
        change_handler,
        emailer
    ):
        self.repository = repository
        self.first_handler = first_handler
        self.change_handler = change_handler
        self.emailer=emailer

    def process(self, order):
        today = datetime.today().strftime("%A")
        #on change
        self.change_handler.process(order)
        #Lock On Price
#        if self.repository.lock_if_below_floor(order.id):

