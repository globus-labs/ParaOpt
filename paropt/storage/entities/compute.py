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
  
  def asdict(self):
    return {
      'type': self.type,
      'instance_family': self.instance_family,
      'instance_model': self.instance_model,
      'ami': self.ami
    }

class LocalCompute(Compute):
  max_threads = Column(Integer)

  __mapper_args__ = {'polymorphic_identity': 'local'}

  def __repr__(self):
    return (
      f'LocalCompute('
      f'max_threads={self.max_threads}'
      f')'
    )
  
  def asdict(self):
    return {
      'type': self.type,
      'max_threads': self.max_threads
    }


class PBSProCompute(Compute):
  cpus_per_node = Column(String(5))
  walltime = Column(String(10))
  scheduler_options = Column(String(100))
  worker_init = Column(String(100))

  __mapper_args__ = {'polymorphic_identity': 'PBSPro'}

  def __repr__(self):
    return (
      f'PBSProCompute('
      f'cpus_per_node={self.cpus_per_node}'
      f'walltime={self.walltime}'
      f'scheduler_options={self.scheduler_options}'
      f'worker_init={self.worker_init}'
      f')'
    )
  
  def asdict(self):
    return {
      'type': self.type,
      'cpus_per_node': self.cpus_per_node,
      'walltime': self.walltime,
      'scheduler_options': self.scheduler_options,
      'worker_init': self.worker_init
    }