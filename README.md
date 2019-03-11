## Paropt
Paropt enables automating the process of finding optimal tool configurations using [Parsl](https://github.com/Parsl/parsl) and [BayesianOptimization](https://github.com/fmfn/BayesianOptimization).

### Setup
```bash
pip install git+https://git@github.com/macintoshpie/paropt
```
A runner, optimizer, storage, and a template bash script for running your tool are requried to run the process. Refer to Parsl docs for instance specific configuration.  

### Example
This example optimizes a script with two parameters, `parameterA` and `parameterB`, which just sleeps for the sum of their values. All trials are run serially on the local machine in this example and results are saved in a text file.  
echoTemplate.sh:
```bash
#!/bin/bash

# paropt will template in our parameter values
echo "Sleeping for ${parameterA} + ${parameterB} seconds"
sleep $((${parameterA} + ${parameterB}))
```
runTrials.py:
```python
#!/usr/bin/env python3
import os

import paropt
from paropt.runner import ParslRunner
from paropt.storage import LocalFile
from paropt.optimizer import BayesianOptimizer
from paropt.runner.parsl import timeCmd
from paropt.runner.parsl import local_config

# log events to console for debugging
paropt.setConsoleLogger()

# experiment configuration
tool = {
  'name': 'faketool',
  'version': '1.2.3'
}
# path to our bash file
script_path = f'{os.path.dirname(os.path.realpath(__file__))}/echoTemplate.sh'
# parameters we want to optimize
command_params = {
  "parameterA": [0, 5],
  "parameterB": [0, 5]
}
experiment = {
  'id': 1234,
  'tool': tool,
  'parameters': command_params,
  'script_template_path': script_path
}

# storage for results
file_storage = LocalFile('testFile.txt')

# optimizer
bayesian_optimizer = BayesianOptimizer(
  command_params,
  n_init=2,
  n_iter=3,
  storage=file_storage
)

# runner
po = ParslRunner(experiment, local_config, timeCmd, grid_search, file_storage)

# start the optimization
po.run()
```
