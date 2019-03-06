from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref

from .orm_base import ORMBase

class Trial(ORMBase):
  __tablename__ = 'trials'

  id = Column(Integer, primary_key=True)
  run_number = Column(Integer)
  outcome = Column(Float)
  # tool_config_id = Column(Integer, ForeignKey('toolconfigs.id'))
  # tool_config = relationship('ToolConfig', backref=backref('trial', uselist=False))
  parameter_configs = relationship("ParameterConfig")
  # timestamp = Column()
