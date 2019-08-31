import argparse
from multiprocessing import Process
import sys

from flask import (Flask, request, flash, redirect, session, url_for)

import redis
from rq import Connection, Worker, Queue
from rq.registry import StartedJobRegistry
from rq.job import Job

from api.api import api
from api.paropt_manager import ParoptManager
from config import SECRET_KEY, _load_funcx_client, SERVER_DOMAIN, GLOBUS_CLIENT


app = Flask(__name__)
app.register_blueprint(api, url_prefix="/api/v1")

@app.route('/', methods=['GET'])
def home():
    """Display if user is authenticated"""
    return f'Authenticated: {session.get("is_authenticated")}'


# TODO: Consider using @authenticated decorator so don't need to check user.
@app.route('/login', methods=['GET'])
def login():

    """Send the user to Globus Auth."""
    return redirect(url_for('callback'))


@app.route('/callback', methods=['GET'])
def callback():
    """Handles the interaction with Globus Auth."""
    # If we're coming back from Globus Auth in an error state, the error
    # will be in the "error" query string parameter.
    if 'error' in request.args:
        flash("You could not be logged into the portal: " +
              request.args.get('error_description', request.args['error']))
        return redirect(url_for('home'))

    # Set up our Globus Auth/OAuth2 state
    # redirect_uri = url_for('callback', _external=True)
    redirect_uri = f'https://{SERVER_DOMAIN}/callback'
    client = _load_funcx_client()
    client.oauth2_start_flow(redirect_uri, refresh_tokens=False)

    # If there's no "code" query string parameter, we're in this route
    # starting a Globus Auth login flow.
    if 'code' not in request.args:
        additional_authorize_params = (
            {'signup': 1} if request.args.get('signup') else {})

        auth_uri = client.oauth2_get_authorize_url()
        # additional_params=additional_authorize_params)
        return redirect(auth_uri)
    else:
        # If we do have a "code" param, we're coming back from Globus Auth
        # and can start the process of exchanging an auth code for a token.
        code = request.args.get('code')
        tokens = client.oauth2_exchange_code_for_tokens(code)
        id_token = tokens.decode_id_token(client)
        print(id_token)
        session.update(
            tokens=tokens.by_resource_server,
            is_authenticated=True
        )

        return redirect(f'https://{SERVER_DOMAIN}')


@app.route('/logout', methods=['GET'])
def logout():
    """
    - Revoke the tokens with Globus Auth.
    - Destroy the session state.
    - Redirect the user to the Globus Auth logout page.
    """
    client = _load_funcx_client()

    # Revoke the tokens with Globus Auth
    for token, token_type in (
            (token_info[ty], ty)
            # get all of the token info dicts
            for token_info in session['tokens'].values()
            # cross product with the set of token types
            for ty in ('access_token', 'refresh_token')
            # only where the relevant token is actually present
            if token_info[ty] is not None):
        client.oauth2_revoke_token(
            token, additional_params={'token_type_hint': token_type})

    # Destroy the session state
    session.clear()

    redirect_uri = url_for('home', _external=True)

    ga_logout_url = list()
    ga_logout_url.append('https://auth.globus.org/v2/web/logout')
    ga_logout_url.append(f'?client={GLOBUS_CLIENT}')
    ga_logout_url.append('&redirect_uri={}'.format(redirect_uri))
    ga_logout_url.append(f'&redirect_name=https://{SERVER_DOMAIN}')

    # Redirect the user to the Globus Auth logout page
    return redirect(''.join(ga_logout_url))


app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['REDIS_URL'] = 'redis://redis:6379/0'
app.config['QUEUES'] = ['default']

def setupAWS():
    # launch a small parsl job on AWS to initialize parsl's AWS VPC stuff
    # If run successfully, it will create the awsproviderstate.json file on host in paropt-service/config/
    # Needs to be run each time the AWS credentials are changed for the server
    # Intended to be used with a `docker run ...` command before running production server
    import os

    import paropt
    from paropt.runner import ParslRunner
    from paropt.storage import RelationalDB
    from paropt.optimizer import BayesianOptimizer, GridSearch
    from paropt.runner.parsl import timeCommand
    from paropt.storage.entities import Parameter, PARAMETER_TYPE_INT, Experiment, LocalCompute, EC2Compute
    
    container_state_file_dir = os.getenv("CONTAINER_STATE_FILE_DIR")
    if not container_state_file_dir:
        raise Exception("Missing required env var CONTAINER_STATE_FILE_DIR which is used for copying awsproviderstate.json to host")

    paropt.setConsoleLogger()

    command_template_string = """
    #! /bin/bash

    sleep ${myParam}
    """

    experiment_inst = Experiment(
        tool_name='tmptool',
        parameters=[
            Parameter(name="myParam", type=PARAMETER_TYPE_INT, minimum=0, maximum=10),
        ],
        command_template_string=command_template_string,
        compute=EC2Compute(
            type='ec2',
            instance_model="c4.large", # using c5 b/c previously had trouble with t2 spot instances
            instance_family="c4",
            ami="ami-0257427d05c8c18ac" # parsl base ami - preinstalled apt packages
        )
    )

    # use an ephemeral database
    storage = RelationalDB(
      'sqlite',
      '',
      '',
      '',
      'tmpSqliteDB',
    )

    # run simple bayes opt
    bayesian_optimizer = BayesianOptimizer(
        n_init=1,
        n_iter=1,
    )

    po = ParslRunner(
        parsl_app=timeCommand,
        optimizer=bayesian_optimizer,
        storage=storage,
        experiment=experiment_inst,
        logs_root_dir='/var/log/paropt'
    )

    po.run(debug=True)
    po.cleanup()

    # print result
    print(po.run_result)

    # move the awsproviderstate file into expected directory
    from shutil import copyfile
    copyfile("awsproviderstate.json", f'{container_state_file_dir}/awsproviderstate.json') 

def startWorker(redis_url, queues):
    ParoptManager.start()
    redis_connection = redis.from_url(redis_url)
    with Connection(redis_connection):
        worker = Worker(queues)
        worker.work()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run paropt server or workers.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--server', action='store_true', help='run as server')
    group.add_argument('--workers', type=int, help='number of workers to start')
    group.add_argument('--setupaws', action='store_true', help='launch a single small job to setup awsproviderstate.json; intended to be used with `docker run ...` before first run of production server')
    args = parser.parse_args()

    if args.server:
        ParoptManager.start()
        app.run(debug=True, host="0.0.0.0", port=8080, use_reloader=False, ssl_context='adhoc')
    elif args.setupaws:
        # run func to configure aws provider state
        setupAWS()
    else:
        if args.workers <= 0:
            print("Error: --workers must be an integer > 0")
            sys.exit(1)
        
        redis_url = app.config['REDIS_URL']
        # clear previously started started jobs - if shut down while running a job, the job will remain in StartedJobsRegistry
        # when it's restarted, which is a problem because it's not actually running anymore
        with Connection(redis.from_url(redis_url)) as conn:
            registry = StartedJobRegistry('default', connection=conn)
            for job_id in registry.get_job_ids():
                registry.remove(Job.fetch(job_id, connection=conn))

        procs = []
        for i in range(args.workers):
            procs.append(Process(target=startWorker,
                                 args=(redis_url, app.config['QUEUES'])))
            procs[i].start()
        for proc in procs:
            proc.join()
