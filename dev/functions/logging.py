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

def loggingInfo(toolname, funcname, message):
    logging.info(toolname + funcname + " " + message)

def loggingWarning(toolname, funcname, message):
    logging.warning(toolname + funcname + " " + message)

def loggingDebug(toolname, funcname, message):
    logging.debug(toolname + funcname + " " + message)

def loggingErrorAndExit(toolname, funcname, error_message, exit_code):
    logging.error(toolname + funcname + " " + error_message)
    exit(exit_code)
