from paropt_sdk.utils.auth import do_login_flow, make_authorizer, logout
from paropt_sdk.config import (check_logged_in, PAROPT_SERVICE_ADDRESS, CLIENT_ID)

from globus_sdk.base import BaseClient, slash_join
from mdf_toolbox import login, logout
from tempfile import mkstemp

import pickle as pkl
import pandas as pd
import requests
import codecs
import json
import os

import warnings

# ignore SSL warnings
# b/c server is currently using self signed cert, requests with arg valid=False raise a warning
# about the security of ignoring verifying the SSL cert
warnings.filterwarnings("ignore")

_token_dir = os.path.expanduser("~/.paropt/credentials")

class ParoptClient(BaseClient):
    """Main class for interacting with the paropt service

    Holds helper operations for performing common tasks with the paropt service.
    """

    def __init__(self, authorizer=None, http_timeout=None,
                 force_login=False, **kwargs):
        """Initialize the client
        Args:
            authorizer (:class:`GlobusAuthorizer
                            <globus_sdk.authorizers.base.GlobusAuthorizer>`):
                An authorizer instance used to communicate with paropt.
                If ``None``, will be created.
            http_timeout (int): Timeout for any call to service in seconds. (default is no timeout)
            force_login (bool): Whether to force a login to get new credentials.
                A login will always occur if ``authorizer`` 
                are not provided.
        Keyword arguments are the same as for BaseClient.
        """
        if force_login or not authorizer or not search_client:
            dlhub_scope = "https://auth.globus.org/scopes/81fc4156-a623-47f2-93ad-7184118226ba/auth"
            auth_res = login(services=[dlhub_scope],
                             app_name="paropt",
                             client_id=CLIENT_ID, clear_old_tokens=force_login,
                             token_dir=_token_dir)
            dlh_authorizer = auth_res['dlhub_org']

        super(ParoptClient, self).__init__("paropt",
                                          authorizer=dlh_authorizer,
                                          http_timeout=http_timeout, base_url=PAROPT_SERVICE_ADDRESS,
                                          **kwargs)

    def logout(self):
        """Remove credentials from your local system"""
        logout()
    
    def getOrCreateExperiment(self, experiment):
        return self.post('/experiments',
                         json_body=experiment,
                         headers={'content-type': 'application/json'})

    def runTrial(self, experiment_id, optimizer):
        return self.post(f'/experiments/{experiment_id}/trials',
                         json_body=optimizer,
                         headers={'content-type': 'application/json'})

    def getTrials(self, experiment_id):
        return self.get(f'/experiments/{experiment_id}/trials')

    def getRunningExperiments(self):
        return self.get('/jobs/running')

    def getFailedExperiments(self):
        return self.get('/jobs/failed')

    def getQueuedExperiments(self):
        return self.get('/jobs/queued')
    
    def getJob(self, job_id):
        return self.get(f'/jobs/{job_id}')
    
    def getExperimentJob(self, experiment_id):
        return self.get(f'/experiments/{experiment_id}/job')