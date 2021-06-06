import abc
from enum import Enum, auto
from typing import Iterable, List, Optional, Tuple


class SweepMethod(Enum):
    grid = auto()
    random = auto()


ParamChoice = Tuple[str, Iterable]


class Logger(abc.ABC):
    @abc.abstractmethod
    def create_sweep(
        self,
        method: SweepMethod,
        metadata: dict,
        choices: List[ParamChoice],
        charts: List[dict],
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

    @property
    @abc.abstractmethod
    def run_id(self):
        return
