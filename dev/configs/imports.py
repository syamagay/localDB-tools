#!/usr/bin/env python3
# -*- coding: utf-8 -*
##################################
## Author1: Eunchong Kim (eunchong.kim at cern.ch)
## Copyright: Copyright 2019, ldbtools
## Date: Jul. 2019
## Project: Local Database Tools
## Description: All configs for development environment
##################################

#==============================
# Use print() in python2 and 3
#==============================
from __future__ import print_function

#==============================
# Default modules
#==============================
import os, sys

#==============================
# Hash
#==============================
import hashlib

#==============================
# Get/Post Http/Https
#==============================
import requests
import json

#==============================
# For date
#==============================
import datetime
import dateutil.parser

#==============================
# Log
#==============================
import logging, logging.config
import coloredlogs

#==============================
# Pymongo and Bson
#==============================
from bson.objectid import ObjectId
from pymongo import MongoClient
import pymongo

#==============================
# For input
#==============================
import yaml, argparse

#==============================
# For beauty
#==============================
from prettytable import PrettyTable
import pprint

#==============================
# Special
#==============================
from uuid import getnode as get_mac # Get MAC adress
