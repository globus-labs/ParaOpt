import abc

class StorageBase(abc.ABC):
  @abc.abstractmethod
  def getTrials():
    pass
  
  @abc.abstractmethod
  def saveResult():
    pass