from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship, backref

from .orm_base import ORMBase

class Compute(ORMBase):
  __tablename__ = 'computes'

  id = Column(Integer, primary_key=True)
  type = Column(String(20))
  experiments = relationship("Experiment", lazy=False)

  __mapper_args__ = {
    'polymorphic_on': type,
    'polymorphic_identity': 'compute'
  }

class EC2Compute(Compute):
  instance_family = Column(String(10))
  instance_model = Column(String(20))
  ami = Column(String(50))

  __mapper_args__ = {'polymorphic_identity': 'ec2'}

  def __repr__(self):
    return (
      f'EC2Compute('
      f'instance_family={self.instance_family}'
      f'instance_model={self.instance_model}'
      f'ami={self.ami}'
      f')'
    )

class LocalCompute(Compute):
  max_threads = Column(Integer)

  __mapper_args__ = {'polymorphic_identity': 'local'}

  def __repr__(self):
    return (
      f'LocalCompute('
      f'max_threads={self.max_threads}'
      f')'
    )
