from dataclasses import astuple, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml
from gql import gql

from run_logger import HasuraLogger


@dataclass
class NewParams:
    config_params: Optional[dict]
    sweep_params: Optional[dict]
    load_params: Optional[dict]


def get_config_params(config: Union[str, Path]) -> dict:
    """
    Reads a ``yaml`` config file and returns a dictionary of parameters.
    """
    if isinstance(config, str):
        config = Path(config)
    with Path(config).open() as f:
        config = yaml.load(f, yaml.FullLoader)
    return config


def get_load_params(load_id: int, logger: HasuraLogger) -> dict:
    """
    Returns the parameters of an existing run.

    :param load_id: The ID of an existing run whose parameters you want to access.
    :param logger: A HasuraLogger object associated with the database where the run is stored.
    """
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
    logger: Optional[HasuraLogger] = None,
    config: Optional[Union[Path, str]] = None,
    charts: Optional[List[dict]] = None,
    metadata: Optional[Dict] = None,
    sweep_id: Optional[int] = None,
    load_id: Optional[int] = None,
) -> NewParams:
    """
    Creates a new run. It registers the run in the database
    (using
    :py:meth:`HasuraLogger.create_run <run_logger.hasura_logger.HasuraLogger.create_run>`)
    and returns a ``NewParams`` object, which provides parameters from three sources:

    - a config file (if provided)
    - a sweep (if the run is enrolled in a sweep)
    - the parameters from an existing run (if ``load_id`` is provided)

    :param logger: A HasuraLogger object. If ``None``, the run is not registered in the database.
    :param config: A path to a ``yaml`` config file.
    :param charts: A list of charts to be added to the database, associated with this run.
    :param sweep_id: The ID of the sweep in which the run is enrolled (if any).
    :param load_id: The ID of an existing run whose parameters you want to access.
    """

    config_params = None
    sweep_params = None
    load_params = None

    if config is not None:
        config_params = get_config_params(config)

    if logger is not None:
        if charts is None:
            charts = []
        sweep_params = logger.create_run(
            metadata=metadata,
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
    """
    This is a convenience wrapper :py:meth:`HasuraLogger.update_metadata <run_logger.hasura_logger.HasuraLogger.update_metadata>`
    Updates the existing parameters of a run (``params``) with new parameters using the Hasura
    `_append <https://hasura.io/blog/postgres-json-and-jsonb-type-support-on-graphql-41f586e47536/#mutations-append>`_
    operator.

    Parameters are updated with the following precedence:
    1. Load parameters (parameters corresponding to an existing run, specified by ``load_id``) if any.
    2. sweep parameters (parameters issued by a sweep, specified by ``sweep_id``) if any.
    3. config parameters (parameters specified in a config file, specified by ``config``) if any.

    That is, sweep parameters will overwrite config parameters and load parameters will overwrite sweep parameters.

    Note that this function does mutate the metadata stored in the database.

    :param logger: A HasuraLogger object associated with the database containing the run whose parameters need to be updated.
    :param new_params: The new parameters.
    :param name: A name to be given to the run.
    :param params: Existing parameters (e.g. command line defaults).
    :return: Updated parameters.
    """

    for p in astuple(new_params):
        if p is not None:
            params.update(p)

    if logger is not None:
        logger.update_metadata(dict(parameters=params, run_id=logger.run_id, name=name))
    return params


def initialize(
    graphql_endpoint: Optional[str] = None,
    config: Optional[Union[Path, str]] = None,
    charts: Optional[List[dict]] = None,
    metadata: Optional[Dict] = None,
    name: Optional[str] = None,
    sweep_id: Optional[int] = None,
    load_id: Optional[int] = None,
    **params,
) -> Tuple[dict, Optional[HasuraLogger]]:
    """
    The main function to initialize a run.
    It creates a new run and returns the parameters and a HasuraLogger object, which
    is a handle for accessing the database.

    :param graphql_endpoint: The endpoint of the Hasura GraphQL API, e.g. ``https://server.university.edu:1200/v1/graphql``. If this value is ``None``, the run will not be logged in the database.
    :param config: An optional path to a ``yaml`` config file file containing parameters. See the section on :ref:`Config files` for more details.
    :param charts: A list of `Vega <https://vega.github.io/>`_ or `Vega-Lite <https://vega.github.io/vega-lite/>`_ graphical specifications, to be displayed by `run-visualizer <https://github.com/run-tracker/run-visualizer>`_.
    :param metadata: Any JSON-serializable object to be stored in the database.
    :param name: An optional name to be given to the run.
    :param sweep_id: An optional sweep ID, to enroll this run in a sweep.
    :param load_id: An optional run ID, to load parameters from an existing run.
    :param params: Existing (usually default) parameters provided for the run (and updated by :py:func:`update_params <run_logger.main.update_params>`).
    :return: A tuple of parameters and a HasuraLogger object.
    """
    logger = HasuraLogger(graphql_endpoint)
    new_params = create_run(
        logger=logger,
        config=config,
        charts=charts,
        metadata=metadata,
        sweep_id=sweep_id,
        load_id=load_id,
    )
    params = update_params(
        logger=logger,
        new_params=new_params,
        name=name,
        **params,
    )
    return params, logger
