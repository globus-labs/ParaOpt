from collections.abc import Iterable
from abc import abstractmethod

class BaseOptimizer(Iterable):
  @abstractmethod
  def getMax():
    pass
  
  @abstractmethod
  def register():
    pass
