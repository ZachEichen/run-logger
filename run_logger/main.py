from dataclasses import astuple, dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union

import yaml
from gql import gql

from run_logger import HasuraLogger


@dataclass
class NewParams:
    config_params: dict
    sweep_params: dict
    load_params: dict


def get_config_params(config: Union[str, Path]) -> dict:
    if isinstance(config, str):
        config = Path(config)
    with Path(config).open() as f:
        config = yaml.load(f, yaml.FullLoader)
    return config


def get_load_params(load_id: int, logger: HasuraLogger) -> dict:
    return logger.execute(
        gql(
            """
query GetParameters($id: Int!) {
run_by_pk(id: $id) {
metadata(path: "parameters")
}
}"""
        ),
        variable_values=dict(id=load_id),
    )["run_by_pk"]["metadata"]


def create_run(
    logger: HasuraLogger = None,
    config: Union[Path, str] = None,
    charts: List[dict] = None,
    sweep_id: int = None,
    load_id: int = None,
) -> NewParams:

    config_params = None
    sweep_params = None
    load_params = None

    if config is not None:
        config_params = get_config_params(config)

    if logger is not None:
        if charts is None:
            charts = []
        sweep_params = logger.create_run(
            metadata={},
            sweep_id=sweep_id,
            charts=charts,
        )

    if load_id is not None:
        load_params = get_load_params(load_id=load_id, logger=logger)

    return NewParams(
        config_params=config_params,
        sweep_params=sweep_params,
        load_params=load_params,
    )


def update_params(
    logger: Optional[HasuraLogger],
    new_params: NewParams,
    name: str,
    **params,
) -> dict:

    for p in astuple(new_params):
        if p is not None:
            params.update(p)

    if logger is not None:
        logger.update_metadata(dict(parameters=params, run_id=logger.run_id, name=name))
    return params


def initialize(
    graphql_endpoint: str = None,
    config: Union[Path, str] = None,
    charts: List[dict] = None,
    sweep_id: int = None,
    load_id: int = None,
    use_logger: bool = False,
    **params,
) -> Tuple[dict, HasuraLogger]:
    logger = HasuraLogger(graphql_endpoint) if use_logger else None
    new_params = create_run(
        logger=logger,
        config=config,
        charts=charts,
        sweep_id=sweep_id,
        load_id=load_id,
    )
    params = update_params(
        logger=logger,
        new_params=new_params,
        **params,
    )
    return params, logger
