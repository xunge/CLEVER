#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
process_log.py

process log files generated by clever.py

Copyright (C) 2017-2018, IBM Corp.
Copyright (C) 2017, Lily Weng  <twweng@mit.edu>
                and Huan Zhang <ecezhang@ucdavis.edu>

This program is licenced under the Apache 2.0 licence,
contained in the LICENCE file in this directory.
"""

import os, glob
import sys
import scipy
import scipy.io as sio
from scipy.stats import weibull_min
import numpy as np
import pandas as pd
import argparse
import matplotlib.pyplot as plt


def readDebugLog2array(filename):
    f = open(filename)
    
    # last 3 lines are L0 verbosity, the first line is comment
    #lines = f.readlines()[0:-3]   
    lines = f.readlines()[0:] # read all the lines and check if belongs to [DEBUG][L1] below   
    # if the files are ended with "_grep"
    #lines = f.readlines()
    f.close()
    
    data_arr = {"[DEBUG][L1] id":[],"true_label":[],"target_label":[],"info":[],"bnd_norm":[],
               "bnd":[],"ks":[],"pVal":[],"shape":[],"loc":[],"scale":[], "g_x0":[]}
    
    #Ncols = len(lines[0].strip().split(','));
    
    for line in lines:
        # split ',' into columns
        subline = line.strip().split(',')
        
        #print(subline)
        #print('-reading lines-')
        
        # only save the info when the line is [DEBUG][L1]
        if subline[0].split('=')[0] == '[DEBUG][L1] id ':
            for elems in subline:
                temp = elems.split('=');
                key = temp[0].strip()
                val = temp[1].strip()
                # save key and val to array
                data_arr[key].append(val)
            
    return data_arr


table_results = {}

if __name__ == "__main__":
    # parse command line parameters
    parser = argparse.ArgumentParser(description='Process experiment data.')
    parser.add_argument('data_folder', nargs='+', help='log file(s) or directory')
    parser.add_argument('--save_pickle', 
                action='store_true',
                help='save result to pickle')
    args = vars(parser.parse_args())
    print(args)
    # process all the log files in the folder    
    flag_process_all_dir = False
    # save result to pickle
    is_save2pickle = args['save_pickle']
    
    files = []
    # the argument is a list of paths
    for path in args['data_folder']:
        # if the path is a directory, look for all log files inside
        if os.path.isdir(path):
            files.extend(glob.glob(os.path.join(path, "*.log")))
        # if the path is a file, include it directly
        else:
            files.append(path)
    print(files)

    for file in files:
        # datas is a dictionary
        datas = readDebugLog2array(file)
        
        # convert the dictionary to dataframe df
        df = pd.DataFrame.from_dict(datas)
        
        # convert the string type columns to numeric 
        df['bnd'] = pd.to_numeric(df['bnd'])
        df['g_x0'] = pd.to_numeric(df['g_x0'])
        df['ks'] = pd.to_numeric(df['ks'])
        df['loc'] = pd.to_numeric(df['loc'])
        df['pVal'] = pd.to_numeric(df['pVal'])
        df['scale'] = pd.to_numeric(df['scale'])
        df['shape'] = pd.to_numeric(df['shape'])
        
        tag1 = os.path.basename(file).split('_')[1]
        
        # cifar, mnist, imagenet 
        if (tag1 == 'cifar') or (tag1 == 'mnist'):
            modelName = tag1 + '_' + os.path.basename(file).split('_')[2].split('.')[0]
        else:
            modelName = tag1
        
        if modelName not in table_results:
            nan = float('nan')
            table_results[modelName] = {'least': {'1': [nan,nan], '2': [nan,nan], 'i': [nan,nan]}, 
                                        'random':{'1': [nan,nan], '2': [nan,nan], 'i': [nan,nan]},
                                        'top2':  {'1': [nan,nan], '2': [nan,nan], 'i': [nan,nan]}}

        for label in ['least','random','top2']:
            for bnd_norm in ['1','2','i']:         
                df_out = df[(df["info"]==label) & (df["bnd_norm"]==bnd_norm)]
                
                if not df_out.empty:
                    out_name = 'pickle_'+modelName+'_'+label+'_norm'+bnd_norm
                    
                    
                    if is_save2pickle:
                        # save selected df to pickle files
                        df_out.to_pickle(out_name)

                    # obtain statistics and print out
                    descrb_0 = df_out.describe()
                    descrb_1 = df_out[(df_out["pVal"]>0.05)&(df_out["shape"]<1000)].describe()
                    
                    
                    bnd_0 = descrb_0["bnd"]["mean"]
                    count_0 = descrb_0["bnd"]["count"]
                    
                    bnd_1 = descrb_1["bnd"]["mean"]
                    count_1 = descrb_1["bnd"]["count"]

                    table_results[modelName][label][bnd_norm][0] = bnd_1
                    table_results[modelName][label][bnd_norm][1] = count_1 * 100.0 / count_0
                    print("[L0] model = {}, Nimg = {}, bnd_avg = {:.5g}, pVal>0.05 & shape<1000 gives" 
                          "Nimg = {}, bnd_avg = {:.5g}, useable = {:.1f} %".format(out_name,count_0,bnd_0,count_1,bnd_1,count_1/count_0*100))
    # print out table for easy pasting to LaTeX
    output = sys.stdout
    print('Generating LaTeX table...')
    order=['mnist_2-layer', 'mnist_normal', 'mnist_distilled', 'mnist_brelu', 'cifar_2-layer', 'cifar_normal', 'cifar_distilled', 'cifar_brelu', 'inception', 'resnet', 'mobilenet']

    def gen_table(elem_index, precision=3):
        for label in ['least','random','top2']:
            output.write("{:15s} &\t{:7s} &\t{:7s} &\n".format(label, '2', 'i'))
            for model in order:
                if model in table_results:
                    output.write("{:15s} &\t".format(model))
                    for bnd_norm in ['2','i']: 
                        output.write(("{:7."+str(precision)+"f} &\t").format(table_results[model][label][bnd_norm][elem_index]))
                    output.write("\n")

    print('\n%%% Table for bounds %%%')
    gen_table(0)
    print('\n%%% Table for p-values %%%')
    gen_table(1,1)

