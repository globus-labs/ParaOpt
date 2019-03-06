from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship, backref

from .orm_base import ORMBase

class Parameter(ORMBase):
  __tablename__ = 'parameters'

  id = Column(Integer, primary_key=True)
  # tool = Column(ForeignKey) # TODO: add tool entity
  name = Column(String)
