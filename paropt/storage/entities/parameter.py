from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship, backref

from .orm_base import ORMBase

PARAMETER_TYPE_FLOAT = 'float'
PARAMETER_TYPE_INT = 'int'

class Parameter(ORMBase):
  __tablename__ = 'parameters'

  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  type = Column(String(20), nullable=False, default=PARAMETER_TYPE_FLOAT)
  minimum = Column(Integer, nullable=False)
  maximum = Column(Integer, nullable=False)
  experiment_id = Column(Integer, ForeignKey('experiments.id'))
  
  def __repr__(self):
    return (
      f'Parameter('
      f'id={self.id}, name={self.name}, minimum={self.minimum}, maximum={self.maximum}, '
      f'experiment_id={self.experiment_id})'
    )
  
  def asdict(self):
    return {
      'name': self.name,
      'minimum': self.minimum,
      'maximum': self.maximum,
      'type': self.type
    }
  
  def getHashAttrs(self):
    """Return values of attributes that should be hashed. Used by Experiment.getHash()"""
    hash_attrs = [
      'name',
      'minimum',
      'maximum',
      'type',
    ]
    attr_str = ""
    for attr in hash_attrs:
      attr_str += str(getattr(self, attr))
    return attr_str
    
  @staticmethod
  def parametersToDict(parameterList):
    return {param.name: [param.minimum, param.maximum] for param in parameterList}
