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
    return (
      f'Experiment('
      f'id={self.id}, '
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
    """Get hash of experiment
    IMPORTANT: columns/attributes used in hash used should either implement a getHashAttrs() method,
    or have a string representation where the result does NOT contain any database id's!
    If Id's are included, the hash will break

    This is used to identify unique experiments, specifically by the storage method
    getOrCreateExperiment(), which uses this to check if the experiment already exists.
    """
    hash_attrs = [
      'tool_name',
      'parameters',
      'command_template_string',
      'setup_template_string',
      'compute'
    ]
    hash_strings = []
    for attr_name in hash_attrs:
      attr = getattr(self, attr_name)
      # if the attribute has the getHashAttrs() method, use that to get values
      # else, just stringify it
      if isinstance(attr, list):
        for subattr in attr:
          if getattr(subattr, 'getHashAttrs', None):
            hash_strings.append(subattr.getHashAttrs())
          else:
            hash_strings.append(str(subattr))
      elif getattr(attr, 'getHashAttrs', None):
        hash_strings.append(attr.getHashAttrs())
      else:
        hash_strings.append(str(attr))
    return md5("".join(hash_strings).encode()).hexdigest()
  
  def setHash(self):
    """Should be called when: 1) experiment is created 2) change of columns used in hash"""
    self.hash = self.getHash()
    return self.hash

def set_hash(mapper, connect, target):
  target.setHash()

listen(Experiment, 'before_insert', set_hash)