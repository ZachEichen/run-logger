from contextlib import contextmanager

from run_logger.haura_logger import HasuraLogger
from run_logger.jsonlines_logger import JSONLinesLogger
from run_logger.logger import Logger, ParamChoice, SweepMethod
from run_logger.logger import ParamChoice

__all__ = [
    "Logger",
    "SweepMethod",
    "ParamChoice",
    "HasuraLogger",
    "JSONLinesLogger",
    "get_logger",
]


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
