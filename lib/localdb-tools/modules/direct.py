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
from pymongo          import MongoClient, ASCENDING, DESCENDING
from bson.objectid    import ObjectId 
from datetime         import datetime, timezone, timedelta
from dateutil.tz      import tzlocal
from tzlocal          import get_localzone
import pytz

# log
from logging import getLogger
logger = getLogger("Log").getChild("sub")
global localdb
def __set_localdb(i_localdb):
    global localdb
    localdb = i_localdb

def setTime(date):
    local_tz = get_localzone() 
    converted_time = date.replace(tzinfo=timezone.utc).astimezone(local_tz)
    time = converted_time.strftime('%Y/%m/%d %H:%M:%S')
    return time

def printLog(message):
    global lines
    global size

    if lines<size:
        print(message)
        lines+=1
    else:
        try:
            input(message)
        except KeyboardInterrupt:
            print('')
            sys.exit()

def getConfigJson(cmp_oid, config, run_oid):
    fs = gridfs.GridFS(localdb)

    r_json = {}
    
    query = { 
        'component': cmp_oid,
        'testRun': run_oid
    }
    this_ctr = localdb.componentTestRun.find_one(query)
    if not this_ctr:
        logger.error('Not found test data: component: {0}, run: {1}'.format( cmp_oid, run_oid ))
        sys.exit()
    if config == 'ctrl' or config == 'scan':
        query = { '_id': ObjectId(run_oid) }
        this_run = localdb.testRun.find_one(query)
    elif config == 'after' or config== 'before':
        this_run = this_ctr
    else:
        logger.error('Not exist config type: {}'.format( config ))
        sys.exit()
    
    if this_run['{}Cfg'.format(config)] == '...':
        r_json.update({ 'data': 'Not found', 'write': False })
    else:
        query = { '_id': ObjectId(this_run['{}Cfg'.format(config)]) }
        this_cfg = localdb.config.find_one(query)
        r_json.update({ 
            'data': 'Found',
            'write': True,
            'config': json.loads(fs.get(ObjectId(this_cfg['data_id'])).read().decode('ascii')),
            'filename': this_cfg['filename'],
        }) 

    return r_json

def __log(args, serialnumber=None):
    global lines
    global size
    lines = 0
    size = shutil.get_terminal_size().lines-4

    arg_vars = vars(args)
    run_query = {}
    log_query = {}
    if args.dummy:
        log_query.update({'dummy': True})
    elif serialnumber:
        query = { 'serialNumber': serialnumber }
        this_cmp = localdb.component.find_one(query)
        if not this_cmp:
            logger.error('Not found component data: {}'.format(serialnumber))
            sys.exit()
        run_query.update({ 'component': str(this_cmp['_id']) })

    if not run_query == {}:
        run_entries = localdb.componentTestRun.find(run_query)
        run_oids = []
        for run_entry in run_entries:
            run_oids.append({ '_id': ObjectId(run_entry['testRun']) })
        log_query.update({ '$or': run_oids })

    if arg_vars.get('user',None):
        query = { 'userName': arg_vars['user'] }
        this_user = localdb.user.find_one( query )
        if not this_user:
            logger.error('Not found user data: {}'.format(arg_vars['user']))
            sys.exit()
        log_query.update({ 'user_id': str(this_user['_id']) })
    if arg_vars.get('site',None):
        query = { 'institution': arg_vars['site'] }
        this_site = localdb.user.find_one( query )
        if not this_site:
            logger.error('Not found site data: {}'.format(arg_vars['site']))
            sys.exit()
        log_query.update({ 'address': str(this_site['_id']) })

    run_entries = localdb.testRun.find(log_query).sort([('startTime', DESCENDING)])

    r_json = { 'log': [] }
    if run_entries:
        for run_entry in run_entries:
            query = { '_id': ObjectId(run_entry['user_id']) }
            this_user = localdb.user.find_one( query )
            query = { '_id': ObjectId(run_entry['address']) }
            this_site = localdb.institution.find_one( query )
            this_dcs = []
            if not run_entry.get('environment','...')=='...': 
                query = { '_id': ObjectId(run_entry['environment']) }
                this_env = localdb.environment.find_one( query)
                for key in this_env:
                    if not key=='_id' and not key=='dbVersion' and not key=='sys':
                        this_dcs.append(key)
            test_data = {
                'user': this_user['userName'],
                'site': this_site['institution'],
                'datetime': setTime(run_entry['startTime']),
                'runNumber': run_entry['runNumber'],
                'testType': run_entry['testType'],
                'runId': str(run_entry['_id']),
                'serialNumber': run_entry['serialNumber'],
                'environment': this_dcs
            }
            r_json['log'].append(test_data)

    for test_data in r_json['log']:
        printLog('\033[1;33mtest data ID: {0} \033[0m'.format(test_data['runId'])) 
        printLog('User          : {0} at {1}'.format(test_data['user'], test_data['site']))
        printLog('Date          : {0}'.format(test_data['datetime']))
        printLog('Serial Number : {0}'.format(test_data['serialNumber']))
        printLog('Run Number    : {0}'.format(test_data['runNumber']))
        printLog('Test Type     : {0}'.format(test_data['testType']))
        if test_data.get('environment',[])==[]:
            printLog('DCS Data      : NULL')
        else:
            for key in test_data.get('environment',[]):
                printLog('DCS Data      : {}'.format(key))
        printLog('')

def __checkout(args, serialnumber=None, runid=None):
    configs = [{ 
        'type': 'ctrl',
        'name': 'controller',
        'col': 'testRun'
    },{
        'type': 'scan',
        'name': 'scan',
        'col': 'testRun'
    }]
    if not args.before or args.after:
        configs.append({
            'type': 'after',
            'name': 'chip(after)',
            'col': 'componentTestRun'
        })
    else:
        configs.append({
            'type': 'before',
            'name': 'chip(before)',
            'col': 'componentTestRun'
        })

    run_oid = None
    if args.dummy:
        query = { 'dummy': True }
        run_entry = localdb.testRun.find(query).sort([('startTime', DESCENDING)]).limit(1)
        if not run_entry.count()==0:
            run_oid = str(run_entry[0]['_id'])
            serialnumber = run_entry[0]['serialNumber']
    elif runid:
        query = { 'testRun': runid }
        this_run = localdb.componentTestRun.find_one(query)
        if this_run:
            run_oid = runid 
            query = { '_id': ObjectId(run_oid) }
            this_run = localdb.testRun.find_one(query)
            serialnumber = this_run['serialNumber']
    elif serialnumber:
        query = { 'serialNumber': serialnumber }
        this_cmp = localdb.component.find_one(query)
        if this_cmp:
            query = { 'component': str(this_cmp['_id']) }
            run_entry = localdb.componentTestRun.find(query).sort([('$natural', -1)]).limit(1)
            if not run_entry.count()==0:
                run_oid = run_entry[0]['testRun']
    else:
        run_entry = localdb.testRun.find({}).sort([('startTime', DESCENDING)]).limit(1)
        if not run_entry.count()==0:
            run_oid = str(run_entry[0]['_id'])
            serialnumber = run_entry[0]['serialNumber']

    if not run_oid:
        if serialnumber:
            logger.error('Not exist test data of the component: {}'.format(serialnumber))
        else:
            logger.error('Not exist test data')
        sys.exit()

    query = { 'serialNumber': serialnumber }
    this_cmp = localdb.component.find_one(query)
    if this_cmp: cmp_oid = str(this_cmp['_id'])
    else:        cmp_oid = serialnumber

    query = { '_id': ObjectId(run_oid) }
    this_run = localdb.testRun.find_one(query)
    chip_data = []
    if this_run['serialNumber'] == serialnumber:
        component_type = 'Module'
        chip_type = this_run.get('chipType','NULL')
        query = { 'testRun': run_oid, 'component': {'$ne': cmp_oid} }
        ctr_entries = localdb.componentTestRun.find(query)
        for ctr in ctr_entries:
            chip_data.append({ 'component': ctr['component'] })
    else:
        component_type = 'Front-end Chip'
        chip_type = this_run.get('chipType','NULL')
        chip_data.append({ 'component': cmp_oid })

    if chip_type == 'FE-I4B': chip_type = 'FEI4B'

    query = { '_id': ObjectId(this_run['user_id']) }
    this_user = localdb.user.find_one(query)

    query = { '_id': ObjectId(this_run['address']) }
    this_site = localdb.institution.find_one(query)

    query = { 'testRun': run_oid }
    run_entries = localdb.componentTestRun.find(query)
    test_data = {
        'testRun'     : run_oid,
        'runNumber'   : this_run['runNumber'],
        'testType'    : this_run['testType'],
        'datetime'    : setTime(this_run['startTime']),
        'serialNumber': this_run['serialNumber'],
        'user'        : this_user['userName'],
        'site'        : this_site['institution'],
        'chips'       : { 
            'serialNumber': {},
            'chipId'      : {},
            'geomId'      : {},
            'tx'          : {},
            'rx'          : {}
        }
    }
    for i, run in enumerate(run_entries):
        try:
            query = { '_id': ObjectId(run['component']) }
            this_cmp = localdb.component.find_one(query)
            ch_serial_number = this_cmp['serialNumber']
            ch_id = this_cmp['chipId']
        except:
            ch_serial_number = run['component']
            ch_id = run.get('chipId',-1)
        test_data['chips']['serialNumber'][run['component']] = ch_serial_number
        test_data['chips']['chipId'][run['component']] = ch_id
        test_data['chips']['geomId'][run['component']] = run.get('geomId',i+1)
        test_data['chips']['tx'][run['component']] = run['tx']
        test_data['chips']['rx'][run['component']] = run['rx']
 
    logger.info('test data information')
    logger.info('- Date          : {}'.format(test_data['datetime']))
    logger.info('- Serial Number : {}'.format(test_data['serialNumber']))
    logger.info('- Run Number    : {}'.format(test_data['runNumber']))
    logger.info('- Test Type     : {}'.format(test_data['testType']))

    # make directory
    if not args.directory: dir_path = './localdb-configs'
    else: dir_path = args.directory

    # get config data
    config_json = []
    test_data.update({ 'path': {} })
    for config in configs:
        for chip in chip_data:
            r_json = getConfigJson(chip['component'], config['type'], test_data['testRun'])
            if r_json['write']: 
                if config['col'] == 'testRun': 
                    file_path = '{0}/{1}'.format(dir_path, r_json['filename'])
                elif config['col'] == 'componentTestRun': 
                    file_path = '{0}/chip{1}-{2}'.format(dir_path, test_data['chips']['geomId'][chip['component']], r_json['filename'])
                config_data = {
                    'data': r_json['config'],
                    'path': file_path 
                } 
                test_data['path'][chip['component']] = 'chip{0}-{1}'.format(test_data['chips']['geomId'][chip['component']], r_json['filename'])
                config_json.append(config_data)
                logger.info('{0:<15} : {1:<10} --->   path: {2}'.format(config['name'], r_json['data'], file_path))
            else: 
                logger.info('{0:<15} : {1:<10}'.format(config['name'], r_json['data']))
            if config['col'] == 'testRun': break
    
    if component_type == 'Module':
        logger.info('{0:<15} : {1:<10} --->   path: {2}/{3}'.format('connectivity', 'Found', dir_path, 'connectivity.json'))
        conn_json = {
            'stage': 'Testing',
            'chipType': chip_type,
            'chips': []
        }
        if not args.dummy:
            conn_json.update({
                'module': {
                    'serialNumber': test_data['serialNumber'],
                    'componentType': 'Module'
                }
            })
        for chip in chip_data:
            chip_json = {
                'serialNumber': test_data['chips']['serialNumber'][chip['component']],
                'chipId': test_data['chips']['chipId'][chip['component']],
                'geomId': test_data['chips']['geomId'][chip['component']],
                'config': test_data['path'][chip['component']],
                'tx': test_data['chips']['tx'][chip['component']],
                'rx': test_data['chips']['rx'][chip['component']]
            }
            conn_json['chips'].append(chip_json)
        config_data = {
            'data': conn_json,
            'path': '{0}/connectivity.json'.format(dir_path) 
        }
        config_json.append(config_data)

    # make config files
    if os.path.isdir(dir_path): 
        shutil.rmtree(dir_path)
    os.makedirs(dir_path)

    for config in config_json:
        with open('{0}'.format(config['path']), 'w') as f: json.dump( config['data'], f, indent=4 )

def __fetch(args, remote):
    global lines
    global size
    lines = 0
    size = shutil.get_terminal_size().lines-4

    db_path = os.environ['HOME']+'/.localdb_retrieve'
    ref_path = db_path+'/refs/remotes'
    if not os.path.isdir(ref_path): 
        os.makedirs(ref_path)
 
    remote_path = ref_path+'/'+remote
    remote_file = open(remote_path, 'w')
    modules = [] 
    query = { 'componentType': 'Module' }
    component_entries = localdb.component.find(query)
    for component in component_entries:
        if component['serialNumber'] == '': continue
        module = {}
        module['serialNumber'] = component['serialNumber'] 
        module['componentType'] = component['componentType']
        module['chipType'] = component['chipType']
        query = { 'parent': str(component['_id']) }
        child_entries = localdb.childParentRelation.find(query)
        module['chips'] = []
        for child in child_entries:
            query = { '_id': ObjectId(child['child']) }
            this_chip = localdb.component.find_one(query)
            chip = {}
            chip['serialNumber'] = this_chip['serialNumber']
            chip['componentType'] = this_chip['componentType']
            chip['chipId'] = this_chip['chipId']
            module['chips'].append(chip)
        modules.append(module)
        remote_file.write('{}\n'.format(component['serialNumber']))
    remote_file.close()

    logger.info('Download Component Data of Local DB locally...')
    printLog('--------------------------------------')
    for j, module in enumerate(modules):
        printLog('Component ({})'.format(j+1))
        printLog('    Chip Type: {}'.format(module['chipType']))
        printLog('    Module:')
        printLog('        serial number: {}'.format(module['serialNumber']))
        printLog('        component type: {}'.format(module['componentType']))
        printLog('        chips: {}'.format(len(module['chips'])))
        for i, chip in enumerate(module['chips']):
            printLog('    Chip ({}):'.format(i+1))
            printLog('        serial number: {}'.format(chip['serialNumber']))
            printLog('        component type: {}'.format(chip['componentType']))
            printLog('        chip ID: {}'.format(chip['chipId']))
        printLog('--------------------------------------\n')
    printLog('Done.')

    sys.exit()