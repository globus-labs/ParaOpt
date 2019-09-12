## Paropt
Paropt enables automating the process of finding optimal tool configurations using [Parsl](https://github.com/Parsl/parsl) and [BayesianOptimization](https://github.com/fmfn/BayesianOptimization).

See [paropt-service](https://github.com/globus-labs/ParaOpt/paropt-service) for using this package in a RESTful API to launch optimization tasks.

### Setup
```bash
pip install git+https://git@github.com/globus-labs/ParaOpt
```

### Usage
Optimizing a tool requires a few things. First, is the experiment which describes the tool we are testing and provides it's context. An experiment is composed of a name, parameters that you will tune to optimize the tool, and a script which uses those parameters to actually run the tool. Notice that the template script and parameters have matching names - this is required for them to get used in the script at runtime. Information about these classes can be found in the `storage/entities` directory.
```python
from paropt.storage.entities import Parameter, PARAMETER_TYPE_INT, PARAMETER_TYPE_FLOAT, Experiment, LocalCompute

# This is a template script for running the tool to be optimized
command_template_string = """
#! /bin/bash

echo "Sleeping for ${foo} + ${bar} seconds"
sleep $(echo ${foo} + ${bar} | bc)
"""

experiment = Experiment(
  tool_name='my-tool',
  parameters=[
    Parameter(name="foo", type=PARAMETER_TYPE_INT, minimum=0, maximum=10),
    Parameter(name="bar", type=PARAMETER_TYPE_FLOAT, minimum=0, maximum=10)
  ],
  command_template_string=command_template_string,
  compute=LocalCompute(max_threads=8)
)
```

To persist the results after running trials we need storage. Right now we support any database that SQLAlchemy can use.
```python
from paropt.storage import RelationalDB

storage = RelationalDB(
  dialect='postgresql',
  username=os.environ['DB_USERNAME'],
  password=os.environ['DB_PASSWORD'],
  host_url=os.environ['DB_HOSTNAME'],
  dbname=os.environ['DB_NAME'],
)
```

An optimizer is used to determine which configurations of the tool to test. Right now we just have grid search and bayesian optimization - both of which only accept numeric types.
```python
from paropt.optimizer import BayesianOptimizer

bayesian_optimizer = BayesianOptimizer(
  n_init=2,
  n_iter=2,
)
```

This is all tied together by a runner, which we use Parsl for. Note that we need to provide a Parsl app that will wrap our template script. For jobs that run on the order of hours, you can use the provided `timeCmd`.
```python
from paropt.runner import ParslRunner
from paropt.runner.parsl import timeCmd


po = ParslRunner(
  parsl_app=timeCmd,
  optimizer=bayesian_optimizer,
  storage=storage,
  experiment=experiment)

po.run()
print(f'Run result: {po.run_result}')
```
