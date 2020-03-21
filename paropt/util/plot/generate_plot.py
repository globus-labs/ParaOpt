import numpy as np
import math
# import matplotlib
import matplotlib.pyplot as plt
import os
import json
import pandas as pd


def GridSearch_plot_1D(data, plot_info):
    ret = {'success': False, 'error': None}
    x_vals = sorted(list(set(data[data['parameter_names'][0]])))
    fig, axes = plt.subplot(figsize=(12, 6))
    for obj_name in data['obj_names']:
        y_val_by_x = {x: [] for x in x_vals}
        for idx, x_val in enumerate(data[data['parameter_names'][0]]):
            y_val_by_x[x_val].append(data[obj_name][idx])

        y_vals = [np.mean(y_val_by_x[x_val]) for x_val in x_vals]
        y_errs = [np.std(y_val_by_x[x_val]) for x_val in x_vals]

        axes.errorbar(x_vals, y_vals, y_errs, label=obj_name)

    plt.legend()

    plot_name = os.path.join(plot_info['plot_dir'], f'{plot_info["experiment_id"]}.png')
    plt.savefig(plot_name)
    return {'success': True, 'error': None}


def GridSearch_plot_2D(data, plot_info):
    pass


def GridSearch_plot(raw_data, plot_info):
    ret = {'success': False, 'error': None}
    parameter_names = [i['parameter_name'] for i in raw_data[0]['parameter_configs']]
    objective_names = list(raw_data[0]['obj_parameters'])
    
    if len(parameter_names) > 2:
        ret['error'] = 'more than 2 parameters'
        return ret
    elif len(parameter_names) < 1:
        ret['error'] = 'less than 1 parameters'
        return ret

    data = {'param_names': parameter_names, 'obj_names': objective_names}
    for param in parameter_names:
        data[param] = []
    for obj in objective_names:
        data[obj] = []

    for trial in raw_data:
        for val in trial['parameter_configs']:
            data[val['parameter_name']].append(val['value'])
        for obj_name, val in trial['obj_parameters'].items():
            data[obj_name] = val

    if len(parameter_names) == 1:
        ret = GridSearch_plot_1D(data, plot_info)
    else:
        ret = GridSearch_plot_2D(data, plot_info)

    return ret
    pass


