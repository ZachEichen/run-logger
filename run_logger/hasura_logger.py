import time
from dataclasses import dataclass
from itertools import cycle, islice
from pathlib import Path
from typing import List, Optional

import numpy as np
from gql import Client as GQLClient, gql
from gql.transport.requests import RequestsHTTPTransport

from run_logger.logger import Logger
from run_logger.params import param_generator, param_sampler


def jsonify(value):
    """
    Convert a value to a JSON-compatible type.
    In addition to standard JSON types, handles

    - ``pathlib.Path`` (converts to ``str``)
    - ``np.nan`` (converts to ``null``)
    - ``np.ndarray`` (converts to ``list``)

    :param value: a ``str``, ``Path``, ``np.ndarray``, ``dict``, or ``Iterable``.
    :return: value converted to JSON-serializable object
    """
    if isinstance(value, str):
        return value
    elif isinstance(value, Path):
        return str(value)
    elif np.isscalar(value):
        if np.isnan(value):
            return None
        try:
            return value.item()
        except AttributeError:
            return value
    elif isinstance(value, np.ndarray):
        return jsonify(value.tolist())
    elif isinstance(value, dict):
        return {jsonify(k): jsonify(v) for k, v in value.items()}
    else:
        try:
            return [jsonify(v) for v in value]
        except TypeError:
            return value


@dataclass
class Client:
    graphql_endpoint: str

    def __post_init__(self):
        transport = RequestsHTTPTransport(url=self.graphql_endpoint)
        self.client = GQLClient(transport=transport)

    def execute(self, query: str, variable_values: dict):
        sleep_time = 1
        while True:
            try:
                return self.client.execute(
                    query,
                    variable_values=jsonify(variable_values),
                )
            except Exception as e:
                print(e)
                breakpoint()
                time.sleep(sleep_time)
                sleep_time *= 2


@dataclass
class HasuraLogger(Logger):
    """
    HasuraLogger is the main logger class for this library.

    :param graphql_entrypoint:
        The endpoint of the Hasura GraphQL API, e.g. ``https://server.university.edu:1200/v1/graphql``.
    :param seed:
        The seed for the random number generator. Used for selecting random parameters
        in conjunction with sweeps. See `sweep-logger <https://github.com/run-tracker/sweep-logger>`_ for details about
        creating sweeps.
    :param debounce_time:
        If your application expects to perform many log operations in rapid succession, debouncing
        collects the log data over the course of this time interval to perform a single large API call,
        instead of several small ones which might jam the server.
    """

    graphql_endpoint: str
    seed: int = 0
    _run_id: Optional[int] = None
    debounce_time: int = 0

    insert_new_run_mutation = gql(
        """
    mutation insert_new_run($metadata: jsonb = {}, $charts: [chart_insert_input!] = []) {
      insert_run_one(object: {charts: {data: $charts}, metadata: $metadata}) {
        id
      }
    }
    """
    )
    add_run_to_sweep_mutation = gql(
        """
    mutation add_run_to_sweep($metadata: jsonb = {}, $sweep_id: Int!, $charts: [chart_insert_input!] = []) {
        insert_run_one(object: {charts: {data: $charts}, metadata: $metadata, sweep_id: $sweep_id}) {
            id
            sweep {
                parameter_choices {
                    Key
                    choice
                }
            }
        }
        update_sweep(where: {id: {_eq: $sweep_id}}, _inc: {grid_index: 1}) {
            returning {
                grid_index
            }
        }
    }
    """
    )
    update_metadata_mutation = gql(
        """
    mutation update_metadata($metadata: jsonb!, $run_id: Int!) {
        update_run(
            where: {id: {_eq: $run_id}}
            _append: {metadata: $metadata}
        ) {
            affected_rows
        }
    }
    """
    )
    insert_run_logs_mutation = gql(
        """
    mutation insert_run_logs($objects: [run_log_insert_input!]!) {
      insert_run_log(objects: $objects) {
        affected_rows
      }
    }
    """
    )
    insert_run_blobs_mutation = gql(
        """
    mutation insert_run_blobs($objects: [run_blob_insert_input!]!) {
      insert_run_blob(objects: $objects) {
        affected_rows
      }
    }
    """
    )

    def __post_init__(self):
        self.random = np.random.default_rng(seed=self.seed)
        assert self.graphql_endpoint is not None
        self.client = Client(graphql_endpoint=self.graphql_endpoint)
        self._log_buffer = []
        self._blob_buffer = []
        self._last_log_time = None
        self._last_blob_time = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def run_id(self):
        return self._run_id

    def create_run(
        self,
        metadata: Optional[dict],
        charts: Optional[List[dict]] = None,
        sweep_id: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Creates a new run in the Hasura database.

        :param metadata: Any useful data about the run being created, e.g. git commit, parameters used, etc. ``run-logger`` makes no assumptions about the content of ``metadata``, except that it is JSON-compatible (or convertible to JSON-compatible by :py:func:`jsonify <run_logger.hasura_logger.jsonify>`).
        :param charts: A list of `Vega <https://vega.github.io/>`_ or `Vega-Lite <https://vega.github.io/vega-lite/>`_ graphical specifications, to be displayed by `run-visualizer <https://github.com/run-tracker/run-visualizer>`_.
        :param sweep_id: The ID of the sweep that this run is associated with, if any.  See `sweep-logger <https://github.com/run-tracker/sweep-logger>`_ for details about creating sweeps.
        :return: A dictionary of new parameter values assigned by sweep, if run is associated with one
        (otherwise `None`).
        """
        variable_values = dict(metadata=metadata)
        if charts is not None:
            variable_values.update(
                charts=[
                    dict(spec=spec, order=order) for order, spec in enumerate(charts)
                ]
            )
        if sweep_id is None:
            mutation = self.insert_new_run_mutation
        else:
            mutation = self.add_run_to_sweep_mutation
            variable_values.update(sweep_id=sweep_id)
        data = self.execute(mutation, variable_values=variable_values)
        insert_run_response = data["insert_run_one"]
        self._run_id = insert_run_response["id"]
        if sweep_id is not None:
            param_choices = {
                d["Key"]: d["choice"]
                for d in insert_run_response["sweep"]["parameter_choices"]
            }
            grid_index = data["update_sweep"]["returning"][0]["grid_index"]
            assert param_choices, "No parameter choices found in database"
            for k, v in param_choices.items():
                assert v, f"{k} is empty"
            if grid_index is None:
                # random search
                choice = param_sampler(param_choices, self.random)
            else:
                # grid search
                iterator = cycle(param_generator(param_choices))
                choice = next(islice(iterator, grid_index, None))

            return choice

    def update_metadata(self, metadata: dict):
        """
        This will combine given metadata with existing run metadata
        using the Hasura
        `_append <https://hasura.io/blog/postgres-json-and-jsonb-type-support-on-graphql-41f586e47536/#mutations-append>`_
        operator.

        You must call :meth:`HasuraLogger.create_run` before calling this method.
        """
        assert self.run_id is not None, "add_metadata called before create_run"
        self.execute(
            self.update_metadata_mutation,
            variable_values=dict(
                metadata=metadata,
                run_id=self.run_id,
            ),
        )

    def log(self, **log):
        """
        Create a new log object to be added to the `logs` database table.
        This populates the data that `run-visualizer <https://github.com/run-tracker/run-visualizer>`_
        will pass to Vega charts specs.
        Specifically, run-visualizer will insert the array of logs into ``data: values: [...]``.

        You must call :meth:`HasuraLogger.create_run` before calling this method.
        """
        assert self.run_id is not None, "log called before create_run"

        self._log_buffer.append(dict(log=log, run_id=self.run_id))
        if (
            self._last_log_time is None
            or time.time() - self._last_log_time > self.debounce_time
        ):
            self.execute(
                self.insert_run_logs_mutation,
                variable_values=dict(objects=self._log_buffer),
            )
            self._last_log_time = time.time()
            self._log_buffer = []

    def blob(self, blob: str, metadata: dict):
        """
        Store a blob object in database. "Blobs" typically store large objects
        such as images. `Run-visualizer <https://github.com/run-tracker/run-visualizer>`_
        does not pull blobs from the Hasura database and they will not congest the
        visualizer web interface.

        You must call :py:func:`create_run <run_logger.hasura_logger.create_run>` before calling this method.

        :param blob: This is expected to be a `bytea <https://www.postgresql.org/docs/current/datatype-binary.html#:~:text=The%20bytea%20type%20supports%20two,bytea_output%3B%20the%20default%20is%20hex.>`_ datatype.
        :param metadata: any JSON-compatible metadata to be stored with blob.
        """
        assert self.run_id is not None, "blob called before create_run"

        self._blob_buffer.append(dict(blob=blob, metadata=metadata, run_id=self.run_id))
        if (
            self._last_blob_time is None
            or time.time() - self._last_blob_time > self.debounce_time
        ):
            self.execute(
                self.insert_run_blobs_mutation,
                variable_values=dict(objects=self._blob_buffer),
            )
            self._last_blob_time = time.time()
            self._blob_buffer = []

    def execute(self, *args, **kwargs):
        return self.client.execute(*args, **kwargs)
