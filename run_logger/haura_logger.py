import base64
import time
from dataclasses import dataclass
from itertools import cycle, islice
from pathlib import Path
from typing import List, Optional

import numpy as np
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from run_logger.logger import Logger
from run_logger.params import param_generator, param_sampler


@dataclass
class HasuraLogger(Logger):
    hasura_uri: str
    seed: int = 0
    x_hasura_admin_secret: str = None
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
        self.random = np.random.RandomState(seed=0)
        assert self.hasura_uri is not None
        transport = RequestsHTTPTransport(
            url=self.hasura_uri,
            headers={"x-hasura-admin-secret": self.x_hasura_admin_secret},
        )
        self.client = Client(transport=transport)
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
        metadata: dict,
        charts: List[dict] = None,
        sweep_id: int = None,
    ) -> Optional[dict]:
        variable_values = dict(metadata=metadata)
        if charts is not None:
            variable_values.update(charts=[dict(spec=spec) for spec in charts])
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
                choice = param_sampler(param_choices)
            else:
                # grid search
                iterator = cycle(param_generator(param_choices))
                choice = next(islice(iterator, grid_index, None))

            return choice

    def update_metadata(self, metadata: dict):
        assert self.run_id is not None, "add_metadata called before create_run"
        self.execute(
            self.update_metadata_mutation,
            variable_values=dict(
                metadata=metadata,
                run_id=self.run_id,
            ),
        )

    def log(self, log: dict):
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

    def blob(self, blob: dict):
        assert self.run_id is not None, "blob called before create_run"

        self._blob_buffer.append(dict(blob=blob, run_id=self.run_id))
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

    @classmethod
    def jsonify(cls, value):
        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            return base64.b64encode(value).decode("ascii")
        elif isinstance(value, Path):
            return str(value)
        elif np.isscalar(value):
            return None if np.isnan(value) else value
        elif isinstance(value, np.ndarray):
            return cls.jsonify(value.tolist())
        elif isinstance(value, dict):
            return {cls.jsonify(k): cls.jsonify(v) for k, v in value.items()}
        else:
            try:
                return [cls.jsonify(v) for v in value]
            except TypeError:
                return value

    def execute(self, query, variable_values):
        sleep_time = 1
        while True:
            try:
                return self.client.execute(
                    query,
                    variable_values=self.jsonify(variable_values),
                )
            except Exception as e:
                print(e)
                breakpoint()
                time.sleep(sleep_time)
                sleep_time *= 2
