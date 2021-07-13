import abc
from typing import List, Optional

from run_logger.params import ParamChoice, SweepMethod


class Logger(abc.ABC):
    @abc.abstractmethod
    def create_sweep(
        self,
        method: SweepMethod,
        metadata: dict,
        choices: List[ParamChoice],
    ) -> int:
        pass

    @abc.abstractmethod
    def create_run(
        self,
        metadata: dict,
        charts: List[dict],
        sweep_id: int = None,
    ) -> Optional[dict]:
        pass

    @abc.abstractmethod
    def update_metadata(self, metadata: dict):
        pass

    @abc.abstractmethod
    def log(self, log: dict) -> None:
        pass

    @abc.abstractmethod
    def blob(self, blob: bytes) -> None:
        pass

    @property
    @abc.abstractmethod
    def run_id(self):
        return
