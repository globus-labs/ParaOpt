from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship, backref

from .orm_base import ORMBase

class ParameterConfig(ORMBase):
  __tablename__ = 'parameterconfigs'

  id = Column(Integer, primary_key=True)
  parameter_id = Column(Integer, ForeignKey('parameters.id'))
  parameter = relationship("Parameter")
  trial_id = Column(Integer, ForeignKey('trials.id'))
  value = Column(Float)
