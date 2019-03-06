from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship, backref

ORMBase = declarative_base()

def create_all(engine):
  ORMBase.metadata.create_all(engine)
