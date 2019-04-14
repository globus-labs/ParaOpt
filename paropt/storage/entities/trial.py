from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.sql.expression import func


from .orm_base import ORMBase

class Trial(ORMBase):
  __tablename__ = 'trials'

  id = Column(Integer, primary_key=True)
  experiment_id = Column(Integer, ForeignKey('experiments.id'), nullable=False)
  run_number = Column(Integer, nullable=False)
  outcome = Column(Float, nullable=False)
  parameter_configs = relationship("ParameterConfig")
  timestamp = Column(TIMESTAMP, server_default=func.now(), onupdate=func.current_timestamp())

  def __repr__(self):
    return (
      f'Trial('
      f'experiment_id={self.experiment_id}, run_number={self.run_number}, outcome={self.outcome}, '
      f'timestamp={self.timestamp!r}, parameter_configs={self.parameter_configs!r})'
    )

  def asdict(self):
    return {
      'experiment_id': self.experiment_id,
      'run_number': self.run_number,
      'outcome': self.outcome,
      'parameter_configs': [config.asdict() for config in self.parameter_configs],
      'timestamp': self.timestamp
    }