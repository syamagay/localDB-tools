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

def loggingInfo(toolname=TOOLNAME, funcname=FUNCNAME, message=""):
    logging.info(toolname + funcname + " " + message)

def loggingWarning(toolname=TOOLNAME, funcname=FUNCNAME, message=""):
    logging.warning(toolname + funcname + " " + message)

def loggingDebug(toolname=TOOLNAME, funcname=FUNCNAME, message=""):
    logging.debug(toolname + funcname + " " + message)

def loggingErrorAndExit(toolname=TOOLNAME, funcname=FUNCNAME, message="", exit_code=100):
    logging.error(toolname + funcname + " " + message)
    exit(exit_code)
