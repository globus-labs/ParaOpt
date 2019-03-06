import os
import logging

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.sql.expression import func

from .entities.orm_base import create_all
from .storage_base import StorageBase
from .entities.trial import Trial
from .entities.parameter_config import ParameterConfig
from .entities.parameter import Parameter

logger = logging.getLogger(__name__)

class RelationalDB(StorageBase):
  def __init__(self, dialect, username, password, host_url, dbname, experiment):
    self.dialect = dialect
    self.username = username
    self.password = password
    self.host_url = host_url
    self.dbname = dbname
    self.engine_url = f'{dialect}://{username}:{password}@{host_url}/{dbname}'

    self.initialized = False
    self.engine = create_engine(self.engine_url)
    self.Session = sessionmaker(bind=self.engine)

    # TODO: replace experiment with experiment_id (default to None)
    # In setup, fetch experiment if experiment_id != None, otherwise create new experiment?
    self.experiment = experiment
    self.run_number = -1
  
  def _getNextRunNumber(self):
    if not self.initialized:
      self._setup()
    
    session = self.Session()
    max_trial = session.query(func.max(Trial.run_number)).first()
    max_run_number = max_trial[0]
    if max_run_number == None:
      return 0
    return max_run_number + 1
  
  def _setup(self):
    # initialize database
    logger.info(f'Setting up {self.engine_url}')
    # create database if it doesn't exist
    if not database_exists(self.engine.url):
      create_database(self.engine.url)
    create_all(self.engine)
    self.initialized = True

    # initialize experiment
    for parameter in self.experiment['parameters']:
      self._putParameter(parameter)
    # get next run number
    self.run_number = self._getNextRunNumber()
  
  def _putParameter(self, parameter_name):
    if not self.initialized:
      self._setup()

    session = self.Session()
    if None == session.query(Parameter).filter(Parameter.name == parameter_name).first():
      logger.info(f'Saving Parameter {parameter_name} to database')
      param = Parameter(name=parameter_name)
      session.add(param)
      session.commit()

  def saveResult(self, param_configs, result):
    if not self.initialized:
      self._setup()
    
    session = self.Session()
    param_config_objs = []
    for pc_name in param_configs:
      # get parameter from database
      # TODO: this should also filter using experiment...
      param = session.query(Parameter) \
        .filter(Parameter.name == pc_name) \
        .first()
      if param == None:
        raise Exception(f'Unable to find parameter: {pc_name}')
      new_config = ParameterConfig(parameter=param, value=param_configs[pc_name])
      param_config_objs.append(new_config)
    
    session.add_all(param_config_objs)
    trial = Trial(outcome=result[2], parameter_configs=param_config_objs, run_number=self.run_number)
    logger.info(f'Saving trial to database: {trial}')
    session.add(trial)
    session.commit()
  
  def getPreviousTrials(self):
    if not self.initialized:
      self._setup()

    session = self.Session()
    all_results = session.query(Trial) \
      .filter(Trial.run_number < self.run_number) \
      .join(ParameterConfig, Trial.parameter_configs) \
      .join(Parameter, ParameterConfig.parameter) \
      .all()
    
    return all_results
