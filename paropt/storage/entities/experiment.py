from hashlib import md5

from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.event import listens_for, listen

from .orm_base import ORMBase

class Experiment(ORMBase):
  __tablename__ = 'experiments'

  id = Column(Integer, primary_key=True)
  # TODO: replace these string cols with relationships to entities
  tool_name = Column(String, nullable=False)
  command_template_string = Column(String, nullable=False)
  setup_template_string = Column(String)
  finish_template_string = Column(String)
  parameters = relationship("Parameter", lazy=False)
  trials = relationship("Trial")
  compute_id = Column(Integer, ForeignKey('computes.id'))
  compute = relationship("Compute", lazy=False)
  hash = Column(String)

  def __repr__(self):
    """IMPORTANT: Do not add id to the representation - that would break our hashing"""
    return (
      f'Experiment('
      f'tool_name={self.tool_name}, '
      f'parameters={self.parameters!r}, '
      f'command_template_string={self.command_template_string}), '
      f'setup_template_string={self.setup_template_string}, '
      f'finish_template_string={self.finish_template_string}, '
      f'compute={self.compute!r})'
    )
  
  def asdict(self):
    return {
      'id': self.id,
      'tool_name': self.tool_name, 
      'parameters': [parameter.asdict() for parameter in self.parameters],
      'command_template_string': self.command_template_string,
      'setup_template_string': self.setup_template_string,
      'finish_template_string': self.finish_template_string,
      'compute': self.compute.asdict()
    }
  
  def getHash(self):
    return md5(str(self).encode()).hexdigest()
  
  def setHash(self):
    self.hash = self.getHash()
    return self.hash

def set_hash(mapper, connect, target):
  target.setHash()

listen(Experiment, 'before_insert', set_hash)