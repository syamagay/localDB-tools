#!/usr/bin/env python3
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Common imports
#################################

from configs.development import * # Omajinai

# Print iterations progress
def printProgressBar(iteration, total, prefix = '', suffix = '', decimals = 1, fill = '*'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        fill        - Optional  : bar fill character (Str)
    """
    rows, columns = os.popen('stty size', 'r').read().split() # Get terminal width
    length = int(columns) - len(prefix) - len(suffix) - 11
    if total == 0:
        percent = ("{0:." + str(decimals) + "f}").format(100)
        filledLength = int(length * 1)
    else:
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = "\r")
    # Print New Line on Complete
    if iteration == total: 
        print()
