#!/usr/bin/env python3
# -*- coding: utf-8 -*
##################################
## Author1: Eunchong Kim (eunchong.kim at cern.ch)
## Copyright: Copyright 2019, ldbtools
## Date: Jul. 2019
## Project: Local Database Tools
## Description: All configs for development environment
##################################

# Imports modules
from configs.imports import * #

# System environments
from configs.environment import * #

# Route of functions and tools
from configs.route import * #

# Tool name?
TOOLNAME = "[LDBTool-dev] "

# Python logging
# https://stackoverflow.com/questions/17743019/flask-logging-cannot-get-it-to-write-to-a-file
directory = "logs"
if not os.path.exists(directory):
    os.makedirs(directory)
logging.config.dictConfig(yaml.safe_load(open('./configs/logging.yml')))
coloredlogs.install()
