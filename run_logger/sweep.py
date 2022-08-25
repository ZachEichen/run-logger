import argparse
import copy
import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path
from pprint import pformat
from typing import Optional

from gql import gql

from run_logger.run import RunLogger


@dataclass
class SweepLogger(RunLogger):
    insert_new_sweep_mutation = gql(
        """
mutation insert_new_sweep(
    $metadata: jsonb,
) {
  insert_sweep_one(object: {
      metadata: $metadata,
      }) {
    id
    metadata
  }
}
    """
    )
    add_run_to_sweep_mutation = gql(
        """
mutation add_run_to_sweep($metadata: jsonb = {}, $sweep_id: Int!, $charts: [chart_insert_input!] = []) {
    insert_run_one(object: {charts: {data: $charts}, metadata: $metadata, sweep_id: $sweep_id}) {
        id
    }
    update_sweep(where: {id: {_eq: $sweep_id}}) {
        returning {
            id
        }
    }
}
    """
    )

    def create_sweep(
        self,
        metadata: dict,
    ) -> int:
        response = self.execute(
            self.insert_new_sweep_mutation,
            variable_values=dict(
                metadata=metadata,
            ),
        )
        sweep_id = response["insert_sweep_one"]["id"]
        return sweep_id


def compute_remaining_runs(params):
    if isinstance(params, list):
        return sum(compute_remaining_runs(param) for param in params)
    if isinstance(params, dict):
        return math.prod(map(compute_remaining_runs, params.values()))
    return 1


def create_sweep(
    config: dict,
    graphql_endpoint: str,
    log_level: str,
    name: Optional[str],
    project: Optional[str] = None,
) -> int:
    assert isinstance(config, (dict, list)), pformat(config)
    logging.getLogger().setLevel(log_level)
    metadata = dict(config=config)
    if name is not None:
        metadata.update(name=name)
    if project is not None:
        metadata.update(project=project)
    with SweepLogger(graphql_endpoint=graphql_endpoint) as logger:
        sweep_id = logger.create_sweep(metadata=metadata)
    logging.info(f"Sweep ID: {sweep_id}")
    return sweep_id


log_levels = [
    "CRITICAL",
    "FATAL",
    "ERROR",
    "WARN",
    "WARNING",
    "INFO",
    "DEBUG",
    "NOTSET",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        "-c",
        help="Path to sweep config yaml file.",
        type=Path,
        default=Path("config.yml"),
    )
    parser.add_argument("--log-level", "-ll", choices=log_levels, default="INFO")
    parser.add_argument(
        "--name", "-n", help="Name of sweep (logged in metadata).", default=None
    )
    parser.add_argument(
        "--project", "-p", help="Name of project (logged in metadata).", default=None
    )
    parser.add_argument(
        "--graphql-endpoint",
        "-g",
        default=os.getenv("GRAPHQL_ENDPOINT"),
        help="Endpoint to use for hasura.",
    )
    parser.add_argument(
        "--remaining-runs",
        "-r",
        help="Set a limit on the number of runs to launch for this sweep. If None or '', an unlimited number of runs "
        "will be launched.",
        type=lambda string: int(string)
        if string
        else None,  # handle case where string == ''
    )
    parser.set_defaults(func=create_sweep)
    args = parser.parse_args()
    _args = vars(copy.deepcopy(args))
    del _args["func"]
    args.func(**_args)


if __name__ == "__main__":
    main()
