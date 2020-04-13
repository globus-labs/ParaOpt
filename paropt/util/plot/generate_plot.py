import numpy as np
import math
# import matplotlib
import matplotlib.pyplot as plt
import os
import json
import pandas as pd


def GridSearch_plot_1D(data, plot_info):
    """
    function that draw 1D plot
    """
    ret = {'success': False, 'error': None}
    x_vals = sorted(list(set(data[data['param_names'][0]])))
    
    for idx, obj_name in enumerate(data['obj_names']):
        fig, axes = plt.subplots(figsize=(12, 8))
        fig.suptitle(f'Experiment {plot_info["experiment_id"]}_fig{idx}')
        y_val_by_x = {x_val: [] for x_val in x_vals}
        for i, x_val in enumerate(data[data['param_names'][0]]):
            y_val_by_x[x_val].append(data[obj_name][i])

        y_vals = [np.mean(y_val_by_x[x_val]) for x_val in x_vals]
        y_errs = [np.std(y_val_by_x[x_val]) for x_val in x_vals]

        axes.errorbar(x_vals, y_vals, y_errs)
        axes.set_xlabel(data['param_names'][0])
        axes.set_ylabel(obj_name)
    # plt.legend()
        plot_name = os.path.join(plot_info['plot_dir'], f'{plot_info["experiment_id"]}_fig{idx}_{obj_name}.png')
        plt.savefig(plot_name)
    return {'success': True, 'error': f'{plot_info["plot_dir"]}, {plot_info["experiment_id"]}'}


def GridSearch_plot_2D(data, plot_info):
    """
    function that draw 2D plot
    """
    ret = {'success': False, 'error': None}
    x_vals = sorted(list(set(data[data['param_names'][0]])))
    y_vals = sorted(list(set(data[data['param_names'][1]])))

    x_val_dic = {val: i for i, val in enumerate(x_vals)}
    y_val_dic = {val: i for i, val in enumerate(y_vals)}

    X_VAL, Y_VAL = np.meshgrid(x_vals, y_vals)

    
    for idx, obj_name in enumerate(data['obj_names']):
        fig, axes = plt.subplots(figsize=(12, 8))
        fig.suptitle(f'Experiment {plot_info["experiment_id"]}_fig{idx}')
        Z = []
        for i in range(len(X_VAL)):
            Z.append([])
            for j in range(len(X_VAL[0])):
                Z[i].append([])

        for i in range(len(data[data['param_names'][0]])):
            Z[y_val_dic[data[data['param_names'][1]][i]]][x_val_dic[data[data['param_names'][0]][i]]].append(data[obj_name][i])

        Z = np.array(Z)
        # print(Z.shape)
        Z = np.mean(Z, axis=2)
        ZT = np.flipud(Z)

        im = axes.imshow(ZT)

        for i in range(len(ZT)):
            for j in range(len(ZT[0])):
                text = axes.text(j, i, round(ZT[i, j], 2), ha="center", va="center", color="w")

        axes.set_title(f'{obj_name}')
        axes.set_xlabel(data['param_names'][0])
        axes.set_ylabel(data['param_names'][1])
        axes.set_xticks(range(len(x_vals)))
        axes.set_yticks(range(len(y_vals)))
        axes.set_xticklabels(x_vals)
        axes.set_yticklabels(reversed(y_vals))

        plot_name = os.path.join(plot_info['plot_dir'], f'{plot_info["experiment_id"]}_fig{idx}_{obj_name}.png')
        plt.savefig(plot_name)
    return {'success': True, 'error': f'{plot_info["plot_dir"]}, {plot_info["experiment_id"]}'}


def GridSearch_plot(raw_data, plot_info):
    """
    draw plots for grid search experiment

    parameters:
    raw_data: list
        data read by experiment
    plot_info: dict
        some parameters that is used. The following need to be set:
            'draw_plot': True
            'plot_dir': '.'
    """

    ret = {'success': False, 'error': None}
    
    # clean data
    parameter_names = [i['parameter_name'] for i in raw_data[0]['parameter_configs']]
    objective_names = list(raw_data[0]['obj_parameters'].keys())
    objective_names.append('obj_outcome')
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
            data[obj_name].append(val)

        data['obj_outcome'].append(trial['outcome'])

    # draw plots
    if len(parameter_names) == 1:
        ret = GridSearch_plot_1D(data, plot_info)
    else:
        ret = GridSearch_plot_2D(data, plot_info)

    return ret
