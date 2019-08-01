#!/usr/bin/env python3
# -*- coding: utf-8 -*
##################################
## Author1: Eunchong Kim (eunchong.kim at cern.ch)
## Copyright: Copyright 2019, ldbtools
## Date: Jul. 2019
## Project: Local Database Tools
## Description: Logging error message and exit with code
##################################

from configs.development import * # Omajinai

# Python logging
# https://stackoverflow.com/questions/17743019/flask-logging-cannot-get-it-to-write-to-a-file

def setupLogging(logfile):
    # Create log directory if need
    if len(logfile.split("/")) > 1:
        log_directory = logfile.rsplit('/', 1)[0]
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

    logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            filename='%s' % (logfile),
            filemode='a'
        )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    coloredlogs.install()

def loggingInfo(toolname=TOOLNAME, funcname=FUNCNAME, message=""):
    logging.info(toolname + funcname + " " + message)

def loggingWarning(toolname=TOOLNAME, funcname=FUNCNAME, message=""):
    logging.warning(toolname + funcname + " " + message)

def loggingDebug(toolname=TOOLNAME, funcname=FUNCNAME, message=""):
    logging.debug(toolname + funcname + " " + message)

def loggingErrorAndExit(toolname=TOOLNAME, funcname=FUNCNAME, message="", exit_code=100):
    logging.error(toolname + funcname + " " + message)
    exit(exit_code)
