from .storage_base import StorageBase

class LocalFile():
  def __init__(self, file_path):
    self.file_path = file_path
  
  def getPreviousTrials(self):
    with open(self.file_path, 'r') as f:
      return f.readlines()
  
  def saveResult(self, config, result):
    with open(self.file_path, 'a') as f:
      f.write(str(config) + str(result) + '\n')
