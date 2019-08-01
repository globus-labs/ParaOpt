from parsl.app.app import python_app

@python_app
def timeCommand(runConfig):
    """Time the main command script. Exits early on failure at any step (setup, main, finish)

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', and 'run_time' to indicate the result of the run
        If returncode is not 0, run_time must be ignored.
    """
    import os
    import subprocess
    import time

    def timeScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)
        start_time = time.time()
        proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        total_time = time.time() - start_time

        return {'returncode': proc.returncode, 'stdout': outs.decode(), 'run_time': total_time}

    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = timeScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['run_time'] = 0
                return res
        # else:
        #     res = timeScript('setupScript', 'sleep 1')
        #     if res['returncode'] != 0:
        #         res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
        #         res['run_time'] = 0
        #         return res
        
        # time command script
        res = timeScript('mainScript', runConfig.command_script_content)
        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        res['run_time'] = -res['run_time'] / 86400
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = timeScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['run_time'] = main_res['run_time']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return {'returncode': -1,
                        'stdout': "(BUG) Exception occurred during execution: {}".format(e),
                        'run_time': 0}


@python_app
def timeCommandLimitTime(runConfig):
    """Time the main command script. Exits early on failure at any step (setup, main, finish)
    with timeout

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', and 'run_time' to indicate the result of the run
        If returncode is not 0, run_time must be ignored.
    """
    import os
    import subprocess
    import time

    timeout = 10
    def timeScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)

        timeout_returncode = 0
        try:
            start_time = time.time()
            proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            timeout_returncode = proc.wait(timeout=timeout)
            outs, errs = proc.communicate()
            total_time = time.time() - start_time

            return {'returncode': proc.returncode, 'stdout': outs.decode(), 'run_time': total_time}
        except subprocess.TimeoutExpired:
            return {'returncode': timeout_returncode, 'stdout': f'Timeout', 'run_time': -1} # run time = -1 means timeout


    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = timeScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['run_time'] = 0
                return res

        res = timeScript('mainScript', runConfig.command_script_content)
        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        res['run_time'] = -res['run_time'] / 86400
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = timeScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['run_time'] = main_res['run_time']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return {'returncode': -1,
                        'stdout': "(BUG) Exception occurred during execution: {}".format(e),
                        'run_time': 0}



@python_app
def searchMatrix(runConfig):
    """Time the main command script. Exits early on failure at any step (setup, main, finish)

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', and 'run_time' to indicate the result of the run
        If returncode is not 0, run_time must be ignored.
    """
    import os
    import subprocess
    import time

    def runScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)
        # start_time = time.time()
        proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        # total_time = time.time() - start_time
        res = float(outs.decode('utf-8'))

        return {'returncode': proc.returncode, 'stdout': outs.decode(), 'run_time': res}

    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = runScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['run_time'] = 0
                return res
        # else:
        #     res = timeScript('setupScript', 'sleep 1')
        #     if res['returncode'] != 0:
        #         res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
        #         res['run_time'] = 0
        #         return res
        
        # time command script
        res = runScript('mainScript', runConfig.command_script_content)
        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        res['run_time'] = -res['run_time']
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = runScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['run_time'] = main_res['run_time']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return {'returncode': -1,
                        'stdout': "(BUG) Exception occurred during execution: {}".format(e),
                        'run_time': 0}