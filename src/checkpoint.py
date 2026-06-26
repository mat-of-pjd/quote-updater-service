import json
from pathlib import Path
from datetime import datetime
from json import JSONDecodeError


class CheckpointManager:

    def __init__(self, filename):
        self.filename = Path(filename)

    def load(self):

        if not self.filename.exists():
            return datetime(2000, 1, 1)

        try:
            content = self.filename.read_text().strip()

            if not content:
                return datetime(2000, 1, 1)

            data = json.loads(content)

            return datetime.fromisoformat(
                data["last_updated"]
            )

        except (
            JSONDecodeError,
            KeyError,
            ValueError
        ):
            return datetime(2000, 1, 1)
        
    def save(self, timestamp):
        self.filename.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.filename.write_text(
            json.dumps(
                {
                    "last_updated":
                        timestamp.isoformat()
                }
            )
        )