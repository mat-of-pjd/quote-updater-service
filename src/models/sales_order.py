from dataclasses import dataclass
from datetime import datetime

@dataclass
class SalesOrder:
    id: int
    number: str
    #workflow_status: str
    last_updated: datetime
#    processed_once: datetime | None