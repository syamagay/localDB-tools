#!/usr/bin/env python3
#################################
# Author: Arisa Kubota
# Email: arisa.kubota at cern.ch
# Date: July 2019
# Project: Local Database for YARR
#################################

# Common
import os
import sys
import shutil
import json
from bson import Binary, Code, decode_all, BSON
from bson.json_util import dumps
from bson.json_util import loads

import gridfs             
from pymongo          import MongoClient
from bson.objectid    import ObjectId 
from datetime         import datetime, timezone, timedelta
from dateutil.tz      import tzlocal
from tzlocal          import get_localzone
import pytz

DB_DEBUG = False

def alert(i_message, i_type='error'):
    if DB_DEBUG: print('DBHandler: Alert "{}"'.format(i_type))

    if i_type=="error":
        alert_message = "#DB ERROR#"
    elif i_type=='warning':
        alert_message = '#DB WARNING#'

    print('{0} {1}'.format(alert_message, i_message))
# TODO logging
#    now = datetime.now().timestamp()
#
#    std::string log_path = m_cache_dir+"/var/log/"+timestamp+"_error.log";
#    std::ofstream file_ofs(log_path, std::ios::app);
#    strftime(tmp, 20, "%F_%H:%M:%S", lt);
#    timestamp=tmp;
#    file_ofs << timestamp << " " << alert_message << " [" << m_option << "] " << i_function << std::endl;
#    file_ofs << "Message: " << i_message << std::endl;
#    file_ofs << "Log: " << m_log_path << std::endl;
#    file_ofs << "Cache: " << m_cache_path << std::endl;
#    file_ofs << "--------------------" << std::endl;

    if i_type=='error': sys.exit()

def toJson(i_file_path):
    if DB_DEBUG: print('\t\tDBHandler: Convert to json code from: {}'.format(i_file_path))

    if os.path.isfile(i_file_path):
        try:
            with open(i_file_path, 'r') as f: file_json = json.load(f)
        except ValueError as e:
            message = 'Could not parse {0}\n\twhat(): {1}'.format(i_file_path, e)
            alert(message)

    return file_json

def writeJson(key, value, file_path, file_json):
    if DB_DEBUG: print('\tDBHandler: Write Json file: {}'.format(file_path))

    file_json[key] = value
    with open(file_path, 'w') as f:
        json.dump(file_json, f, indent=4)


