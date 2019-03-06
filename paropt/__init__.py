import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

default_formatter = logging.Formatter('%(asctime)s: %(name)s: %(levelname)s: %(message)s')

def setConsoleLogger():
  stream_handler = logging.StreamHandler()
  stream_handler.setFormatter(default_formatter)
  logger.addHandler(stream_handler)
  

def setFileLogger(filename):
  file_handler = logging.FileHandler(filename)
  file_handler.setFormatter(default_formatter)
  logger.addHandler(file_handler)
