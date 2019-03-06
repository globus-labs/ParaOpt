import abc

class StorageBase(abc.ABC):
  @abc.abstractmethod
  def getPreviousTrials():
    pass
  
  @abc.abstractmethod
  def saveResult():
    pass