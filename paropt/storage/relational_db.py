import os
import logging

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship, sessionmaker, joinedload
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.sql.expression import func

from .entities.orm_base import create_all
from .storage_base import StorageBase
from .entities import (Trial, Parameter, Experiment, ParameterConfig,
  Compute, EC2Compute, LocalCompute)

logger = logging.getLogger(__name__)

class RelationalDB(StorageBase):
  def __init__(self, dialect, username, password, host_url, dbname, experiment=None, experiment_id=None):
    self.dialect = dialect
    self.username = username
    self.password = password
    self.host_url = host_url
    self.dbname = dbname
    self.engine_url = f'{dialect}://{username}:{password}@{host_url}/{dbname}'

    self.initialized = False
    self.engine = create_engine(self.engine_url)
    self.Session = sessionmaker(bind=self.engine)

    self.experiment = experiment
    self.experiment_id = experiment_id
    self.run_number = -1

    # setup the database
    self._setup()
  
  def getLastRunNumber(self, session, experiment_id):
    if not self.initialized:
      self._setup()
    
    max_trial = session.query(func.max(Trial.run_number)) \
      .filter(Trial.experiment_id == experiment_id) \
      .first()
    max_run_number = max_trial[0]
    if max_run_number == None:
      return 0
    return max_run_number
  
  def _setup(self):
    # initialize database
    logger.info(f'Setting up db engine')
    # create database if it doesn't exist
    if not database_exists(self.engine.url):
      create_database(self.engine.url)
    create_all(self.engine)
    self.initialized = True

  def saveResult(self, session, trial):
    """
    Save Trial and parameter configurations
    """
    if not self.initialized:
      self._setup()

    logger.info(f'Saving trial and parameter configs to database: {trial}')
    session.add(trial)
    session.commit()
  
  def getTrials(self, session, experiment_id):
    if not self.initialized:
      self._setup()

    all_results = session.query(Trial) \
      .filter(Trial.experiment_id == experiment_id) \
      .join(ParameterConfig, Trial.parameter_configs) \
      .join(Parameter, ParameterConfig.parameter) \
      .all()
    
    return all_results
  
  def _assertIsInstanceOf(self, instance, clss):
    if not isinstance(instance, clss):
      raise Exception(f'Provided instance must be of type {clss.__name__}')

  def getExperiment(self, session, experiment_id):
    if not self.initialized:
      self._setup()

    experiment = session.query(Experiment) \
      .filter(Experiment.id == experiment_id) \
      .first()

    return experiment

  def getOrCreateExperiment(self, session, experiment):
    if not self.initialized:
      self._setup()

    self._assertIsInstanceOf(experiment, Experiment)
    
    # Assuming experiments are unique on these properties
    # TODO: improve this by hashing some vals for id or make this assertion in orm
    hash_attr = experiment.getHash()
    instance = session.query(Experiment) \
      .filter(Experiment.hash == hash_attr) \
      .first()
    if instance:
      last_run_number = self.getLastRunNumber(session, instance.id)
      return instance, last_run_number, False
    else:
      # create experiment
      logger.info("Creating new experiment:\n{}".format(experiment))
      session.add(experiment)
      try:
        session.commit()
      except:
        session.rollback()
        raise
      last_run_number = self.getLastRunNumber(session, experiment.id)
      return experiment, last_run_number, True
  
  def getOrCreateCompute(self, session, compute):
    if not self.initialized:
      self._setup()

    self._assertIsInstanceOf(compute, Compute)
    if isinstance(compute, EC2Compute):
      foundCompute = session.query(EC2Compute) \
        .filter(EC2Compute.instance_family == compute.instance_family) \
        .filter(EC2Compute.instance_model == compute.instance_model) \
        .filter(EC2Compute.ami == compute.ami) \
        .first()
    elif isinstance(compute, LocalCompute):
      foundCompute = session.query(LocalCompute) \
        .filter(LocalCompute.max_threads == compute.max_threads) \
        .first()

    if foundCompute:
      return foundCompute, False
    else:
      # create compute
      logger.info("Creating new compute:\n{}".format(compute))
      session.add(compute)
      try:
        session.commit()
      except:
        session.rollback()
        raise
      return compute, True
