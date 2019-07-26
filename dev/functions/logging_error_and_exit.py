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

def loggingErrorAndExit(error_message, exit_code):
    logging.error(TOOLNAME + FUNCNAME + " " + error_message)
    exit(exit_code)
