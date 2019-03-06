from parsl.config import Config
from parsl.executors import ThreadPoolExecutor

local_config = Config(
  executors=[
    ThreadPoolExecutor(
      max_threads=8,
      label='local_threads'
    )
  ]
)
