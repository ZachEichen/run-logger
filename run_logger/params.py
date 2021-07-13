from enum import Enum, auto
from typing import Any, Iterable, Mapping, Tuple

import numpy as np

ParamChoice = Tuple[str, Iterable]


class SweepMethod(Enum):
    grid = auto()
    random = auto()


def param_generator(params: Any):
    if isinstance(params, Mapping):
        if tuple(params.keys()) == ("",):
            yield from param_generator(params[""])
            return
        if not params:
            yield {}
        else:
            (key, value), *params = params.items()
            for choice in param_generator(value):
                for other_choices in param_generator(dict(params)):
                    yield {key: choice, **other_choices}
    elif isinstance(params, (list, tuple)):
        for choices in params:
            yield from param_generator(choices)
    else:
        yield params


def param_sampler(params: Any):
    if isinstance(params, Mapping):
        if tuple(params.keys()) == ("",):
            return param_sampler(params[""])
        return {k: param_sampler(v) for k, v in params.items()}
    elif isinstance(params, (list, tuple)):
        return param_sampler(params[np.random.choice(len(params))])
    else:
        return params
