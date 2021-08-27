import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import jsonlines

from run_logger.logger import Logger


@dataclass
class JSONLinesLogger(Logger):
    log_path: Optional[str] = os.getenv("LOG_PATH")
    run_name: str = "run"
    _writer: jsonlines.Writer = None

    def __enter__(self):
        if self.log_path is None:
            raise RuntimeError("The environment variable LOG_PATH must be defined.")
        log_path = Path(self.log_path).expanduser().resolve()
        self._writer = jsonlines.open(log_path / f"{self.run_name}.jsonl", mode="w")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._writer.close()

    def update_metadata(self, metadata: dict):
        pass

    def create_run(
        self,
        metadata: dict,
        charts: List[dict],
        sweep_id: int = None,
    ) -> Optional[dict]:
        self.run_name = metadata["name"]
        return

    def log(self, log: dict) -> None:
        self._writer.write(log)

    def blob(self, blob: str, metadata: dict) -> None:
        raise NotImplementedError

    @property
    def run_id(self):
        return None
