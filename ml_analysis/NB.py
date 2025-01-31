"""
 File: NB.py 
 Project: analysis 
 Last Modified: 2022-2-7
 Created Date: 2022-2-7
 Copyright (c) 2021
 Author: AHMA project (Univ Rennes, CNRS, Inria, IRISA)
"""

################################################################################
import sys, os, glob
import logging
import numpy                       as np
import joblib
import argparse
import time

from tqdm                          import tqdm
from datetime                      import datetime
from sklearn.metrics               import classification_report


sys.path.append(os.path.join (os.path.dirname (__file__), "../pre-processings/"))

from nicv import compute_nicv
from evaluation import get_tag, load_traces

################################################################################
def evaluate (path_lists, log_file, model_lda, model_nb, mean_sizes, nb_of_bd,
              path_acc, time_limit):
################################################################################
# mean_by_label
# compute the LDA + BN learning algorithm
# 
# input:
#  + path_lists: path of the lists 
#  + log_file: where the results are saved
#  + model_{lda, nb}: prevously saved {LDA, NB}-model
#  + mean_sizes: numbers of mean sizes to try.
#  + path_acc: directory where acculmulators are
#  + time_limit: percentage of the trace (from the begining)
################################################################################
    ## logging exp in file
   
    today = datetime.now ()
    d1 = today.strftime ("%d.%m.%Y - %H:%M:%S")

    file_log = open (log_file, 'a')
    file_log.write ('-'*80 + '\n')
    file_log.write (d1 + '\n')
    file_log.write ('path_lists: %s\n'%str (path_lists)\
                    + 'log_file: %s\n'%str (log_file)\
                    + 'model_lda: %s\n'%str (model_lda)\
                    + 'model_svm: None\n'\
                    + 'model_nb: %s\n'%str (model_nb)\
                    + 'means: %s\n'%str (mean_sizes)\
                    + 'nb_of_bd: %s\n'%str (nb_of_bd)\
                    + 'path_acc: %s\n'%str (path_acc)\
                    + 'time_limit: %s\n'%str (time_limit)\
                    + 'metric: max_nicv\n')
    file_log.write ('-'*80 + '\n')
    file_log.close ()
    
    ## load lists
    [_, _, x_test_filelist, _, _, y_test] \
         = np.load (path_lists, allow_pickle = True)

    ## load LDA (needed for the meaning)
    clf_known = False
    if (model_lda.split ('.')[-1] == 'jl'): # if the model is given
        ## get indexes
        _, _, nicv, bandwidth = compute_nicv (path_lists, path_acc, None,\
                                              bandwidth_nb = nb_of_bd,
                                              time_limit = time_limit)
    
        clf = joblib.load (model_lda)
        
        ## testing
        testing_traces = load_traces (x_test_filelist,  bandwidth, time_limit)
        
        ## no means
        ## LDA
        t0 = time.time ()
        
        X = clf.transform (testing_traces.T)

        clf_known = True
    else: # meaning it is the transformed traces (numpy format)
        ## testing
        t0 = time.time ()
        X = np.load (model_lda, allow_pickle = True)

        
    ## testing
    testing_labels = y_test

    ## get tags to be able to mean
    testing_tags = np.array ([get_tag (f) for f in x_test_filelist])
    
    ## load NB 
    gnb = joblib.load (model_nb)

    file_log = open (log_file, 'a')
    file_log.write ('transform (size: %s): %s seconds\n'%(str(X.shape), str (time.time () - t0)))
    file_log.close ()

    ## NB 
    t0 = time.time ()
    
    predicted_labels = gnb.predict (X)
    
    file_log = open (log_file, 'a')
    file_log.write ('Test NB  (size: %s) [%s seconds]:\n'%(str (X.shape), str (time.time () - t0)))
    file_log.write (f'{classification_report (list (testing_labels), predicted_labels, digits = 4, zero_division = 0)}')
    file_log.close ()

    ## compute for all means size // onloy if the LDA model is known
    if (clf_known):
        for mean_size in mean_sizes:
            file_log = open (log_file, 'a')
            file_log.write ('compute with %s per mean\n'%mean_size)
            file_log.close ()

            X, y = mean_by_tags (testing_traces, testing_tags,
                                 np.array (testing_labels), x_test_filelist, mean_size)

            # NB + LDA
            t0 = time.time ()
            predicted_labels = gnb.predict (clf.transform (X.T))
            
            file_log = open (log_file, 'a')
            file_log.write (f'NB - mean {mean_size}:\n {classification_report (list (y), predicted_labels, digits = 4, zero_division = 0)}')
            file_log.close ()

    
################################################################################
if __name__ == '__main__':
################################################################################

    parser = argparse.ArgumentParser()

    parser.add_argument ('--lists', action = 'store',
                         type = str, dest = 'path_lists',
                         help = 'Absolute path to a file containing the lists')

    parser.add_argument ('--model_lda', action = 'store', type=str,
                         dest = 'model_lda',
                         help = 'Absolute path to the file where the LDA model has been previously saved')

    parser.add_argument ('--model_nb', action = 'store', type=str,
                         dest = 'model_nb',
                         help = 'Absolute path to the file where the NB model has been previously saved')

    parser.add_argument("--mean_size", default = [2,3,4,5,6,7,8,9,10],
                        action = 'append', dest = 'mean_sizes',
                        help = 'Size of each means')
    
    parser.add_argument('--log-file', default = 'log-evaluation.txt',
                         dest = 'log_file',
                         help = 'Absolute path to the file to save results')

    
    parser.add_argument ('--time_limit', action ='store', type = float, default = 0.5,
                         dest = 'time_limit',
                         help = 'percentage of time to concerve (from the begining)')

    
    parser.add_argument ('--acc', action='store', type=str,
                         dest='path_acc',
                         help='Absolute path of the accumulators directory')

    args, unknown = parser.parse_known_args ()
    assert len (unknown) == 0, f"[ERROR] Unknown arguments:\n{unknown}\n"
    
    nb_of_bandwidth_lda = int (args.model_lda.split ('/')[-1].split ('_')[-1].split ('.')[0][:-2])
    nb_of_bandwidth_nb  = int (args.model_nb.split  ('/')[-1].split ('_')[-1].split ('.')[0][:-2])
    assert nb_of_bandwidth_lda == nb_of_bandwidth_nb,\
        f"[ERROR] bad selected models, number of bandwidth must be the same\n"

    evaluate (args.path_lists,
              args.log_file,
              args.model_lda,
              args.model_nb,
              args.mean_sizes,
              nb_of_bandwidth_lda,
              args.path_acc,
              args.time_limit)
    
    
    
