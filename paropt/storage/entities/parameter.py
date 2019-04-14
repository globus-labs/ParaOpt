from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship, backref

from .orm_base import ORMBase

class Parameter(ORMBase):
  __tablename__ = 'parameters'

  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
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
      'maximum': self.maximum
    }

  @staticmethod
  def parametersToDict(parameterList):
    return {param.name: [param.minimum, param.maximum] for param in parameterList}
