from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship, backref

from .orm_base import ORMBase

class Experiment(ORMBase):
  __tablename__ = 'experiments'

  id = Column(Integer, primary_key=True)
  # TODO: replace these string cols with relationships to entities
  tool_name = Column(String, nullable=False)
  command_template_string = Column(String, nullable=False)
  parameters = relationship("Parameter", lazy=False)
  trials = relationship("Trial")

  def __repr__(self):
    return (
      f'Experiment('
      f'id={self.id}, '
      f'tool_name={self.tool_name}, '
      f'parameters={self.parameters}, '
      f'command_template_string={self.command_template_string})'
    )
  
  def asdict(self):
    return {
      'id': self.id,
      'tool_name': self.tool_name, 
      'parameters': [parameter.asdict() for parameter in self.parameters],
      'command_template_string': self.command_template_string
    }