% run-logger documentation master file, created by
% sphinx-quickstart on Wed Apr 13 12:37:56 2022.
% You can adapt this file completely to your liking, but it should at least
% contain the root `toctree` directive.

# Welcome to run-logger's documentation!

A "run" is a long-running process that depends on a set of parameters and outputs results in the form of logs.
This library has three primary functions:

1. Storing run logs in a database.
2. Storing metadata associated with each run in a database (e.g. for the purposes of reproducibility).
3. Managing parameters.

# Installation

```bash
pip install run-logger
```

# Usage

## Setting up the database

This library is designed to work with the [Hasura GraphQL API](https://hasura.io/).
Hasura provides a set of convenient API calls for querying and mutating data in your database.
You can set up
an API with the necessary schema (for working with library) by going to
[this repository](https://github.com/run-tracker/hasura) and following the instructions.

## Initializing a run

Most users will want to initialize a run by calling the {func}`run_logger.main.initialize` function, e.g.

```python
from run_logger import initialize

_, logger = initialize(
    graphql_endpoint="https://server.university.edu:1200/v1/graphql",
    use_logger=True,
    **params
)
```

This will create a new run in the database, and return a
{class}`run_logger.main.RunLogger` object that can be used to store logs in
the database using the {meth}`run_logger.main.RunLogger.log` method. 

It will also store ``params`` in the ``parameters`` key of the run's metadata.

## Charts

One of the features of `run-logger` is that different charts can be
associated with each run. We use the highly expressive
[Vega](https://vega.github.io/) and [Vega-Lite](https://vega.github.io/vega-lite/)
visualization grammars to specify the content of these charts.
The documentation for those libraries provide a wealth of examples.

`run-logger` is designed to work with [run-visualizer](https://github.com/run-tracker/run-visualizer)
which will automatically supply the data logs for each run to the charts.
For example, suppose the user wants to plot a line chart. Per
[this example](https://vega.github.io/vega-lite/examples/line.html)
in the Vega-Lite documentation, the chart should look like this:

```python
chart = {
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Google's stock price over time.",
  "data": {"data": "data"},  # note that this line differs from the example
  "transform": [{"filter": "datum.symbol==='GOOG'"}],
  "mark": "line",
  "encoding": {
    "x": {"field": "date", "type": "temporal"},
    "y": {"field": "price", "type": "quantitative"}
  }
}
```

Unlike the example, this chart does not use a URL to specify the data 
source. Now suppose the user has logged a few data points:

```python
logger.log(symbol="GOOG", date="2020-04-01", price=100)
logger.log(symbol="GOOG", date="2020-04-02", price=110)
logger.log(symbol="GOOG", date="2020-04-03", price=120)
```

[run-visualizer](https://github.com/run-tracker/run-visualizer) will insert 
these data points into the ``data`` field of the chart so that 
it looks like this:

```python
chart = {
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Google's stock price over time.",
  "data": {
      "data": "data",
      "values": [   # inserted by run-visualizer
          {"symbol": "GOOG", "date": "2020-04-01", "price": 100},
          {"symbol": "GOOG", "date": "2020-04-02", "price": 110},
          {"symbol": "GOOG", "date": "2020-04-03", "price": 120}
      ] 
    }, 
  "transform": [{"filter": "datum.symbol==='GOOG'"}],
  "mark": "line",
  "encoding": {
    "x": {"field": "date", "type": "temporal"},
    "y": {"field": "price", "type": "quantitative"}
  }
}
```

Use the [Vega editor](https://vega.github.io/editor/#/edited) to
preview the chart. In general, this is the recommended tool for 
developing new charts before inserting them in the database.

## Config files
In many cases, users will want to store parameters in a file instead of
entering them by hand on the command line each time they launch a run.
`run-logger` offers a utility for loading parameters from [Yaml files](https://yaml.org/).

To load a config file, supply a value to the 
`config` parameter of the {func}`run_logger.main.initialize` function:

```python
parameters, logger = initialize(
    config="path/to/config.yaml",  # <-
    graphql_endpoint="https://server.university.edu:1200/v1/graphql",
    use_logger=True,
    **params
)
```

`parameters` will contain a dictionary corresponding to the contents of the config file, e.g.

```yaml
param1: value1
param2: value2
# ...
```

The parameters stored in the `"parameters":` key of the run's metadata (in the database) will reflect the content of the config file, i.e. `params.update(parameters)`.

## Sweeps

The creation of sweeps is covered in more detail by the [sweep-logger](https://github.com/run-tracker/sweep-logger) documentation.

To enroll a run in a sweep, supply a `sweep_id` parameter to the {func}`run_logger.main.initialize` function:

```python
parameters, logger = initialize(
    sweep_id=1234,  # <-
    graphql_endpoint="https://server.university.edu:1200/v1/graphql",
    use_logger=True,
    **params
)
```

`parameters` will contain a dictionary corresponding to parameters assigned to this run
by the sweep. The parameters stored in the `"parameters":` key of the run's metadata will be `params.update(parameters)` (i.e. `parameters` will take precedence over `params`).

```{admonition} Note
If both `config` and `sweep_id` are supplied, sweep parameters will override config parameters.
To customize the precedence of new parameters,
users may wish to use the {func}`run_logger.main.create_run`,
function.
```

## Loading parameters from existing runs

Suppose you want to re-launch a run with the same parameters as a run that is already in 
the database. To access these parameters, provide a `run_id` parameter to the {func}`run_logger.main.initialize` function:

```python
parameters, logger = initialize(
    load_id=1234,  # <-
    graphql_endpoint="https://server.university.edu:1200/v1/graphql",
    use_logger=True,
    **params,
)
```

`parameters` will be the parameters stored for run `1234` (the parameters stored in the `"parameters":` key of run `1234`'s metadata).
These loaded parameters will take precedence over
any parameters in `params`.

```{admonition} Note
Load parameters will override both config and sweep parameters.
To customize the precedence of new parameters,
users may wish to use the {func}`run_logger.main.create_run`,
function.
```

```{toctree}
:caption: 'Contents:'
:hidden: true
:maxdepth: 2

api
```
