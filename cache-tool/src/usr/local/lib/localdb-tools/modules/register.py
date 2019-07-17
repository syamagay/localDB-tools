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

import gridfs             
from pymongo          import MongoClient
from bson.objectid    import ObjectId 
from datetime         import datetime, timezone, timedelta
from dateutil.tz      import tzlocal
from tzlocal          import get_localzone
import pytz

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import configJson

DB_DEBUG = False
DBV = 1

global localdb
global m_stage_list
global m_env_list
global m_cmp_list

def setTime(date):
    local_tz = get_localzone() 
    converted_time = date.replace(tzinfo=timezone.utc).astimezone(local_tz)
    time = converted_time.strftime('%Y/%m/%d %H:%M:%S')
    return time

def addSys(oid, col):
    now = datetime.utcnow()
    localdb[col].update(
        { 
            '_id': ObjectId(oid) 
        },{
            '$set': { 
                'sys': {
                    'cts': now,
                    'mts': now,
                    'rev': 0
                }
            }
        }
    )

def registerUser(user_name, institution, user_identity):
    if DB_DEBUG: print('\tDBHandler: Register user \n\tUser name: {0} \n\tInstitution: {1} \n\tUser identity: {2}'.format(user_name, institution, user_identity))
 
    doc_value = {
        'userName': user_name,
        'institution': institution,
        'userIdentity': user_identity
    }
    this_user = localdb.user.find_one(doc_value)
    user_oid = ''
    if this_user: 
        user_oid = this_user['_id']
    else:
        doc_value.update({
            'sys': {},
            'userType': 'readWrite',
            'dbVersion': DBV
        })
        user_oid = localdb.user.insert_one(doc_value)
        addSys(str(user_oid), 'user')

    return str(user_oid)

def registerSite(address, hostname, site):
    if DB_DEBUG: print('\tDBHandler: Register site \n\tAddress: {0} \n\tName: {1} \n\tInstitution: {2}'.format(address, hostname, site)) 
 
    doc_value = {
        'address': address,
        'institution': site
    }
    this_site = localdb.institution.find_one(doc_value)
    site_oid = ''
    if this_site: site_oid = this_site['_id']
    else: 
        doc_value.update({
            'sys': {},
            'name': hostname,
            'dbVersion': DBV
        })
        site_oid = localdb.institution.insert_one(doc_value)
        addSys(str(site_oid), 'institution')

    return str(site_oid)

def registerConnCfg(conn_paths):
    if DB_DEBUG: print('DBHandler: Register Component') 
 
    for conn_path in conn_paths:
        if DB_DEBUG: print('\tDBHandler: Register from connectivity: {}'.format(conn_path))

        conn_json = configJson.toJson(conn_path)
        mo_serial_number = conn_json["module"]["serialNumber"]

        module_is_exist = False
        chip_is_exist = False
        cpr_is_fine = True

        mo_oid_str = getComponent(mo_serial_number) 
        if mo_oid_str!='': module_is_exist = True
        chips = 0
        for i, chip_conn_json in enumerate(conn_json['chips']):
            ch_serial_number = chip_conn_json['serialNumber']
            chip_oid_str = getComponent(ch_serial_number)
            if chip_oid_str!='':
                chip_is_exist = True
                doc_value = {
                    'parent': mo_oid_str,
                    'child': chip_oid_str,
                    'status': 'active'
                }
       
#                    "parent" << mo_oid_str <<
#                    "child" << chip_oid_str <<
#                    "status" << "active" <<
#                finalize;
#                auto maybe_result = db["childParentRelation"].find_one(doc_value.view());
#                if (!maybe_result) cpr_is_fine = false;
#            }
#            chips++;
#        }
#        if (module_is_exist&&!chip_is_exist) {
#            std::string message = "There are registered module in connectivity : "+conn_path;
#            std::string function = __PRETTY_FUNCTION__;
#            this->alert(function, message); return;
#        } else if (!module_is_exist&&chip_is_exist) {
#            std::string message = "There are registered chips in connectivity : "+conn_path;
#            std::string function = __PRETTY_FUNCTION__;
#            this->alert(function, message); return;
#        } else if (!cpr_is_fine) {
#            std::string message = "There are wrong relationship between module and chips in connectivity : "+conn_path;
#            std::string function = __PRETTY_FUNCTION__;
#            this->alert(function, message); return;
#        } else if (module_is_exist&&chip_is_exist&&cpr_is_fine) {
#            return;
#        }
#     
#        // Register module component
#        std::string mo_component_type = conn_json["module"]["componentType"];
#        mo_oid_str = this->registerComponent(mo_serial_number, mo_component_type, -1, chips);
#    
#        for (unsigned i=0; i<conn_json["chips"].size(); i++) {
#            std::string ch_serial_number  = conn_json["chips"][i]["serialNumber"];
#            std::string ch_component_type = conn_json["chips"][i]["componentType"];
#            int chip_id = conn_json["chips"][i]["chipId"];
#            // Register chip component
#            std::string ch_oid_str = this->registerComponent(ch_serial_number, ch_component_type, chip_id, -1);
#            this->registerChildParentRelation(mo_oid_str, ch_oid_str, chip_id);
#    
#            json chip_json;
#            chip_json["serialNumber"] = ch_serial_number;
#            chip_json["componentType"] = ch_component_type;
#            chip_json["chipId"] = chip_id;
#        }
#    }
#}
#
#
#
#
#
#




def getComponent(i_serial_number):
    if DB_DEBUG: print('\tDBHandler: Get component data: "Serial Number": {}'.format(i_serial_numebr))

    doc_value = { 'serialNumber': i_serial_number }
    this_cmp = localdb.component.find_one(doc_value)
    oid = ''
    if this_cmp:
        oid = str(this_cmp['_id'])
    return oid

def __set_localdb(i_localdb):
    global localdb
    localdb = i_localdb

def __set_stage_list(i_stage_list):
    global m_stage_list
    m_stage_list = i_stage_list

def __set_env_list(i_env_list):
    global m_env_list
    m_env_list = i_env_list

def __set_cmp_list(i_cmp_list):
    global m_cmp_list
    m_cmp_list = i_cmp_list

def __set_user(user_path):
    if DB_DEBUG: print('DBHandler: Set user: {}'.format(user_path)) 

    global m_user_oid_str

    if user_path == '':
        user_name = os.environ['USER']
        institution = os.environ['HOSTNAME']
        user_identity = 'default'
    else:
        with open(user_path, 'r') as f:
            user_json = json.load(f)
        user_name = user_json.get('userName', os.environ['USER'])
        institution = user_json.get('institution', os.environ['HOSTNAME'])
        user_identity = user_json.get('userIdentity', 'default')

    m_user_oid_str = registerUser(user_name, institution, user_identity)

def __set_site(site_path):
    if DB_DEBUG: print('DBHandler: Set site: {}'.format(site_path)) 

    global m_site_oid_str

    with open(site_path, 'r') as f:
        site_json = json.load(f)
    address = site_json['macAddress']
    hostname = site_json['hostname']
    site = site_json['institution']

    m_site_oid_str = registerSite(address, hostname, site);

def __set_conn(conn_paths):
    if DB_DEBUG: print('DBHandler: Set connectivity config') 

    global m_chip_type

    for conn_path in conn_paths:
        if DB_DEBUG: print('\tDBHandler: setting connectivity config file: {}'.format(conn_path))
        with open(conn_path, 'r') as f: conn_json = json.load(f)
        m_chip_type = conn_json['chipType']
        if m_chip_type=='FEI4B': m_chip_type = 'FE-I4B'
