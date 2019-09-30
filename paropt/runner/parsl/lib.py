from parsl.app.app import python_app

@python_app
def timeCommand(runConfig, **kwargs):
    """Time the main command script. Exits early on failure at any step (setup, main, finish)
    with timeout

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', and 'obj_output' to indicate the result of the run
        If returncode is not 0, obj_output must be ignored.
    """
    import os
    import subprocess
    import time
    import sys

    if 'timeout' in kwargs:
        timeout = kwargs['timeout']
    else:
        timeout = sys.maxsize
    def timeScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)

        timeout_returncode = 0
        obj_parameters = {'running_time': timeout}
        try:
            start_time = time.time()
            proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            timeout_returncode = proc.wait(timeout=timeout)
            outs, errs = proc.communicate()
            total_time = time.time() - start_time
            obj_parameters = {'running_time': total_time}

            return {'returncode': proc.returncode, 'stdout': outs.decode(), 'obj_output': total_time, 'obj_parameters': obj_parameters}
        except subprocess.TimeoutExpired:
            return {'returncode': timeout_returncode, 'stdout': f'Timeout', 'obj_output': timeout, 'obj_parameters': obj_parameters} # run time = -1 means timeout


    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = timeScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['obj_output'] = 0
                res['obj_parameters'] = {}
                return res

        res = timeScript('mainScript', runConfig.command_script_content)

        # if res['stdout'] == 'Timeout':
        #     return res

        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        res['obj_output'] = -float(res['obj_output']) / 86400
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = timeScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['obj_output'] = main_res['obj_output']
                res['obj_parameters'] = main_res['obj_parameters']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return {'returncode': -1,
                'stdout': "(BUG) Exception occurred during execution: {}".format(e),
                'obj_output': 0}



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
        Contains 'returncode', 'stdout', and 'obj_output' to indicate the result of the run
        If returncode is not 0, obj_output must be ignored.
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
        obj_parameters = {'running_time': res}
        return {'returncode': proc.returncode, 'stdout': outs.decode(), 'obj_output': res, 'obj_parameters': obj_parameters}

    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = runScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['obj_output'] = 0
                res['obj_parameters'] = {}
                return res
        
        # time command script
        res = runScript('mainScript', runConfig.command_script_content)
        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        res['obj_output'] = -res['obj_output']
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = runScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['obj_output'] = main_res['obj_output']
                res['obj_parameters'] = main_res['obj_parameters']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return {'returncode': -1,
                'stdout': "(BUG) Exception occurred during execution: {}".format(e),
                'obj_output': 0}


@python_app
def variantCallerAccu(runConfig, **kwargs):
    """Time the main command script. Exits early on failure at any step (setup, main, finish)
    with timeout

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', and 'obj_output' to indicate the result of the run
        If returncode is not 0, obj_output must be ignored.
    """
    import os
    import subprocess
    import time
    import sys
    import math

    if 'timeout' in kwargs and kwargs['timeout'] != 0:
        timeout = kwargs['timeout']
    else:
        timeout = sys.maxsize

    def sigmoid(x):
        return 1/(1+math.exp(-x))
    def func(accu, time):
        return sigmoid(accu/(1-accu)/time)

    def objective(time, accu):
        # change time to half an hour
        time = time/60/30
        return sigmoid(accu/(1-accu)/time)

    def f1_obj(precision, recall):
        if precision + recall == 0:
            return 0
        return 2*precision*recall/(precision+recall)

    def timeScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)

        timeout_returncode = 0
        obj_parameters = {'running_time': timeout}
        ret_dic = {'returncode': None, 'stdout': None, 'obj_output': None, 'obj_parameters': None}
        try:
            start_time = time.time()
            proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            timeout_returncode = proc.wait(timeout=timeout)
            outs, errs = proc.communicate()
            total_time = time.time() - start_time
            
            ret_dic['returncode'] = proc.returncode
            # ret_dic['obj_output'] = total_time
            ret_dic['stdout'] = outs.decode('utf-8')

            # caller time here in sec
            str_res = outs.decode('utf-8')
            res = str_res.strip().split()
            # obj_parameters = {'running_time': total_time, 'precision': float(res[1]), 'recall': float(res[2]), 'caller_time': float(res[0])/1000}
            
            # the output of utility, which is used by optimizer
            # obj_output = objective(obj_parameters['caller_time'], obj_parameters['precision'])

            # obj_output = f1_obj(obj_parameters['precision'], obj_parameters['recall'])
            # ret_dic['obj_parameters'] = obj_parameters
            ret_dic['obj_output'] = obj_output
            
            # timeout_output = objective(timeout, 0)
            return ret_dic
            # return {'returncode': proc.returncode, 'stdout': outs.decode(), 'obj_output': total_time, 'obj_parameters': obj_parameters}
        except subprocess.TimeoutExpired:
            obj_parameters = {'running_time': timeout, 'precision': 0, 'recall': 0, 'caller_time': timeout}
            # obj_output = objective(obj_parameters['caller_time'], obj_parameters['precision'])
            obj_output = f1_obj(obj_parameters['precision'], obj_parameters['recall'])

            ret_dic['obj_output'] = obj_output
            ret_dic['obj_parameters'] = obj_parameters
            ret_dic['returncode'] = timeout_returncode
            return ret_dic
            # return {'returncode': timeout_returncode, 'stdout': f'Timeout', 'obj_output': timeout_output, 'obj_parameters': obj_parameters} # run time = -1 means timeout
        except:
            return ret_dic
            # return {'returncode': proc.returncode, 'stdout': outs.decode('utf-8'), 'obj_output': total_time, 'obj_parameters': obj_parameters}


    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = timeScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['obj_output'] = 0
                res['obj_parameters'] = {}
                return res

        res = timeScript('mainScript', runConfig.command_script_content)
        if res['stdout'] == 'Timeout':
            return res
        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        # res['obj_output'] = -res['obj_output'] / 86400
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = timeScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['obj_output'] = main_res['obj_output']
                res['obj_parameters'] = main_res['obj_parameters']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return {'returncode': -1,
                'stdout': "(BUG) Exception occurred during execution: {}".format(e),
                'obj_output': 0}
                