import abc
from contextlib import contextmanager
from enum import Enum, auto
from typing import Iterable, List, Optional, Tuple

from run_logger.haura_logger import HasuraLogger
from run_logger.jsonlines_logger import JSONLinesLogger

__all__ = ["SweepMethod", "ParamChoice", "Logger", "HasuraLogger", "JSONLinesLogger"]


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


def param_generator(*key_values: ParamChoice):
    if not key_values:
        yield {}
        return
    (key, value), *key_values = key_values
    for choice in value:
        for other_choices in param_generator(*key_values):
            yield {key: choice, **other_choices}


_names = dict(
    hasura=lambda: HasuraLogger(),
    jsonl=lambda: JSONLinesLogger(),
)


@contextmanager
def get_logger(logger_type="hasura"):
    thunk = _names.get(logger_type)
    if thunk is None:
        raise RuntimeError("Invalid Config")
    with thunk() as logger:
        yield logger
