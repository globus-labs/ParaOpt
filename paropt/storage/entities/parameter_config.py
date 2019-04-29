from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship, backref

from .orm_base import ORMBase

from .parameter import PARAMETER_TYPE_FLOAT

class ParameterConfig(ORMBase):
  __tablename__ = 'parameterconfigs'

  id = Column(Integer, primary_key=True)
  parameter_id = Column(Integer, ForeignKey('parameters.id'), nullable=False)
  parameter = relationship("Parameter")
  trial_id = Column(Integer, ForeignKey('trials.id'), nullable=False)
  value = Column(Float, nullable=False)

  def __repr__(self):
    return (
      f'ParameterConfig('
      f'parameter={self.parameter!r}, {self.value})'
    )
  
  def asdict(self):
    return {
      'parameter_name': self.parameter.name,
      'value': self.value
    }

  @staticmethod
  def configsToDict(parameter_configs):
    # TODO: Properly implement parameter typing - casting of values should not be done here
    d = {}
    for config in parameter_configs:
      v = config.value if config.parameter.type == PARAMETER_TYPE_FLOAT else int(config.value)
      d[config.parameter.name] = v
    return d