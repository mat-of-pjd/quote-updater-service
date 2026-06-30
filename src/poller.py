import logging
import time

class Poller:

    def __init__(
        self,
        repository,
        checkpoint,
        processor,
        interval=1
    ):
        self.repository = repository
        self.checkpoint = checkpoint
        self.processor = processor
        self.interval = interval

    def run(self):
        last_seen = self.checkpoint.load()
        while True:
            try:
                changes = (
                    self.repository.get_changes(last_seen)
                )
                latest = last_seen
                for order in changes:
                    self.processor.process(order)
                    if (order.last_updated > latest):
                        latest = (order.last_updated)
                self.checkpoint.save(latest)
                last_seen = latest
            except Exception:
                logging.exception(
                    "Poller failure"
                )
            time.sleep(
                self.interval
            )