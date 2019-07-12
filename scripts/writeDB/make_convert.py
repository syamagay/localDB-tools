#!/usr/bin/env python3
#################################
# Author: Arisa Kubota
# Email: arisa.kubota at cern.ch
# Date: Feb 2019
# Project: Local Database for YARR
# Description: DB scheme convertor
# Usage: python app.py --config conf.yml
#################################

### Import 
import os
import sys
import datetime
import json
import re
import hashlib
import argparse
import yaml
import gridfs
from   pymongo       import MongoClient
from   bson.objectid import ObjectId   

### Functions
url = 'mongodb://127.0.0.1:27017' 
client = MongoClient( url )
yarrdb = client['yarrdb']
localdb = client['localdb']
yarrfs = gridfs.GridFS( yarrdb )
localfs = gridfs.GridFS( localdb )
db_version = 1

### Set log file
log_dir = './log'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
now = datetime.datetime.now() 
log_filename = now.strftime('{}/logConvert_%m%d_%H%M.txt'.format(log_dir))
log_file = open( log_filename, 'w' )

def write_log( text ):
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S {}\n'.format(text) ) )

def checkComponent(i_doc, i_new_id):
    query = { 'serialNumber': i_doc['serialNumber'] }
    component_type = i_doc['componentType']
    if component_type != 'Module' and component_type != 'Front-end Chip':
        component_type = 'Front-end Chip'
    query.update({ 'componentType': component_type })
    thisComponent = localdb.component.find_one( query )
    cmp_id_str = ""
    if thisComponent:
        cmp_id_str = str(thisComponent['_id'])
    else:
        cmp_id_str = registerComponent(i_doc, i_new_id)
    
    return cmp_id_str

def registerComponent(i_doc, i_new_id):
    component_type = i_doc['componentType']
    chip_type = i_doc.get('chipType', '')
    children = -1
    if component_type == 'Module':
        if chip_type == '':
            query = { 'parent': str(i_doc['_id']) }
            entries = yarrdb.childParentRelation.find( query )
            if entries.count() != 0:
                query = { '_id': ObjectId(entries[0]['child']) }
                chip = yarrdb.component.find_one( query )
                chip_type = chip['componentType']
                children  = entries.count()
            else:
                chip_type = 'unknown'
    elif component_type != 'Front-end Chip':
        component_type = 'Front-end Chip'
        chip_type      = i_doc['componentType']

    user_id_str = ''
    site_id_str = ''
    if 'userIdentity' in i_doc:
        user_name     = i_doc['userIdentity']
        institution   = i_doc['institution']
        user_identity = 'default'
    else:
        query = { '_id': ObjectId(i_doc['user_id']) }
        thisUser = yarrdb.user.find_one( query )
        user_name     = thisUser['userName']
        institution   = thisUser['institution']
        user_identity = thisUser['userIdentity']
    user_id_str = checkUser(user_name, institution, user_identity)
    site_id_str = checkSite('', institution)
 
    timestamp = datetime.datetime.utcnow()
    insert_doc = {
        'sys': {
            'rev': 2,
            'cts': timestamp,
            'mts': timestamp
        },
        'serialNumber' : i_doc['serialNumber'],
        'chipType'     : chip_type,
        'componentType': component_type,
        'children'     : children,
        'chipId'       : -1, 
        'dbVersion'    : db_version,
        'address'      : site_id_str, 
        'user_id'      : user_id_str 
    } 
    cmp_id = localdb.component.insert( insert_doc )

    if component_type == 'Front-end Chip':
        query = { 
            'parent': i_new_id,
            'child' : str(cmp_id)
        }
        thisCpr = localdb.childParentRelation.find_one( query )
        if not thisCpr:
            timestamp = datetime.datetime.utcnow()
            insert_doc = {
                'sys': {
                    'rev': 2,
                    'cts': timestamp,
                    'mts': timestamp
                },
                'parent'   : i_new_id,
                'child'    : str(cmp_id),
                'chipId'   : -1,
                'status'   : 'active',
                'dbVersion': db_version
            }
            localdb.childParentRelation.insert( insert_doc )

    write_log( '\t[Register] Component : {}'.format( i_doc['serialNumber'] ) )

    return str(cmp_id)

def checkUser(i_user_name, i_institution, i_user_identity):
    user_query = {
        'userName'    : i_user_name,
        'institution' : i_institution,
        'userIdentity': i_user_identity
    }
    thisUser = localdb.user.find_one( user_query )
    user_id = ""
    if thisUser:
        user_id = str(thisUser['_id'])
    else:
        user_id = registerUser(i_user_name, i_institution, i_user_identity)
    
    return user_id

def registerUser(i_user_name, i_institution, i_user_identity):
    timestamp = datetime.datetime.utcnow()
    insert_doc = {
        'sys': {
            'rev': 2,
            'cts': timestamp,
            'mts': timestamp
        },
        'userName'    : i_user_name,
        'institution' : i_institution,
        'userIdentity': i_user_identity,
        'userType'    : 'readWrite',
        'dbVersion'   : db_version
    }
    user_id = localdb.user.insert( insert_doc )

    write_log( '\t[Register] User : {0} {1}'.format( i_user_name, i_institution ) )
    return str(user_id)

def checkSite(i_address, i_institution):
    site_query = {
        'address'    : i_address,
        'institution': i_institution
    }
    thisSite = localdb.institution.find_one( site_query )
    site_id_str = ''
    if thisSite:
        site_id_str = str(thisSite['_id'])
    else:
        site_id_str = registerSite(i_address, i_institution)
    
    return site_id_str

def registerSite(i_address, i_institution):
    timestamp = datetime.datetime.utcnow()
    insert_doc = {
        'sys': {
            'rev': 2,
            'cts': timestamp,
            'mts': timestamp
        },
        'name'       : '',
        'address'    : i_address,
        'institution': i_institution
    }
    site_id = localdb.institution.insert( insert_doc )

    write_log( '\t[Register] Site : {0}'.format( i_institution ) )
    return str(site_id)
 
def checkTestRun(i_doc, i_serial_number):
    user_id = ''
    site_id = ''
    if 'userIdentity' in i_doc:
        user_name     = i_doc['userIdentity']
        institution   = i_doc['institution']
        user_identity = 'default'
    else:
        query = { '_id': ObjectId(i_doc['user_id']) }
        thisUser = yarrdb.user.find_one( query )
        user_name     = thisUser['userName']
        institution   = thisUser['institution']
        user_identity = thisUser['userIdentity']
    user_id_str = checkUser(user_name, institution, user_identity)
    site_id_str = checkSite('', institution)

    tr_query = {
        'testType'    : i_doc['testType'],
        'runNumber'   : i_doc['runNumber'],
        'user_id'     : user_id_str,
        'address'     : site_id_str,
        'serialNumber': i_serial_number
    }
    thisRun = localdb.testRun.find_one( tr_query )
    tr_id_str = ''
    if thisRun:
        tr_id_str = str(thisRun['_id'])
    else:
        i_doc.update( tr_query )
        tr_id_str = registerTestRun(i_doc)

    return tr_id_str

def registerTestRun(i_doc):
    env_id = '...'
    if 'startTime' in i_doc:
        start_time  = i_doc['startTime']
        if 'finishTime' in i_doc:
            finish_time = i_doc['finishTime']
        else:
            finish_time = start_time
        env_id = registerEnvFromTr( start_time, finish_time, i_doc['address'] )
    else:
        start_time  = i_doc['date']
        finish_time = i_doc['date']
    timestamp = datetime.datetime.utcnow()
    insert_doc = {
        'sys': {
            'rev': 2,
            'cts': timestamp,
            'mts': timestamp
        },
        'testType'    : i_doc['testType'],
        'runNumber'   : i_doc['runNumber'],
        'startTime'   : start_time,
        'passed'      : True,
        'problems'    : True,
        'summary'     : i_doc.get('display', False),
        'state'       : 'ready',
        'targetCharge': i_doc.get('targetCharge',-1),
        'targetTot'   : i_doc.get('targetTot',-1),
        'command'     : '...',
        'comments'    : [],
        'defects'     : [],
        'finishTime'  : finish_time,
        'plots'       : [], 
        'serialNumber': i_doc['serialNumber'],
        'chipType'    : '...',
        'dummy'       : False,
        'stage'       : '...', 
        'ctrlCfg'     : '...', 
        'scanCfg'     : '...', 
        'environment' : env_id,
        'address'     : i_doc['address'], 
        'user_id'     : i_doc['user_id'], 
        'dbVersion'   : db_version
    }
    tr_id = localdb.testRun.insert( insert_doc )

    write_log( '\t[Register] testRun : {0} {1} {2}'.format( i_doc['runNumber'], i_doc['testType'], i_doc['serialNumber'] ) )
    return str(tr_id)
 
def checkComponentTestRun(i_cmp_id, i_tr_id):
    query = {
        'component': i_cmp_id,
        'testRun'  : i_tr_id
    }
    thisComponentTestRun = localdb.componentTestRun.find_one( query )
    ctr_id_str = ''
    if thisComponentTestRun:
        ctr_id_str = str(thisComponentTestRun['_id'])
    else:
        ctr_id_str = registerComponentTestRun(i_cmp_id, i_tr_id)

    return ctr_id_str
    
def registerComponentTestRun(i_cmp_id, i_tr_id):
    query = { '_id': ObjectId(i_tr_id) }
    thisRun = localdb.testRun.find_one( query )
    query = { '_id': ObjectId(i_cmp_id) }
    thisCmp = localdb.component.find_one( query )
    timestamp = datetime.datetime.utcnow()
    insert_doc = {
        'sys': {
            'rev': 2,
            'cts': timestamp,
            'mts': timestamp
        },
        'component'  : i_cmp_id,
        'state'      : '...',
        'testType'   : thisRun['testType'],
        'testRun'    : i_tr_id,
        'qaTest'     : False,
        'runNumber'  : thisRun['runNumber'],
        'passed'     : True,
        'problems'   : True,
        'attachments': [],
        'tx'         : -1, 
        'rx'         : -1, 
        'geomId'     : thisCmp.get('chipId',-1),
        'beforeCfg'  : '...', 
        'afterCfg'   : '...', 
        'dbVersion'  : db_version
    }
    ctr_id = localdb.componentTestRun.insert( insert_doc )
    query = { '_id': ObjectId(i_cmp_id) }
    thisComponent = localdb.component.find_one( query )

    write_log( '\t[Register] componentTestRun : {0} {1} {2}'.format( thisRun['runNumber'], thisRun['testType'], thisComponent['serialNumber'] ) )
    return str(ctr_id)

def registerEnvFromTr(i_start_time, i_finish_time, i_address):
    env_id = '...'
    query = {
        '$and': [
            { 'date': { '$gt': i_start_time - datetime.timedelta(minutes=1) }},
            { 'date': { '$lt': i_finish_time +  datetime.timedelta(minutes=1) }}
        ]
    }
    insert_doc = {}
    environment_entries = yarrdb.environment.find( query )
    env_dict = {}
    description = {}
    for environment in environment_entries:
        if not environment['key'] in env_dict:
            env_dict.update({ environment['key']: [] })
        env_dict[environment['key']].append({
            'date': environment['date'],
            'value': environment['value']
        })
        description.update({ environment['key']: environment['description'] })
    for key in env_dict:
        if not key in insert_doc:
            insert_doc.update({ key: [] })
        insert_doc[key].append({
            'data': env_dict[key],
            'description': description[key],
            'mode': 'null',
            'setting': -1,
            'num': 0
        })
    if not insert_doc == {}:
        timestamp = datetime.datetime.utcnow()
        insert_doc.update({
            'sys': {
                'rev': 2,
                'cts': timestamp,
                'mts': timestamp
            },
            'dbVersion': db_version
        })
        env_id = localdb.environment.insert( insert_doc )

    write_log( '\t[Register] Environment' )
    return str(env_id)

def registerEnvFromCtr(i_doc, date):
    timestamp = datetime.datetime.utcnow()
    insert_doc = {
        'sys': {
            'rev': 2,
            'cts': timestamp,
            'mts': timestamp
        },
        'dbVersion': db_version
    }
    for env_doc in i_doc['environments']:
        insert_doc.update({
            env_doc['key']: [{
                'data': [{ 
                    'date': date,
                    'value': env_doc['value']
                }],
                'description': env_doc['description'],
                'mode': 'null',
                'setting': -1,
                'num': 0
            }]
        })
    env_id = localdb.environment.insert( insert_doc )

    write_log( '\t[Register] Environment' )
    return str(env_id)
        
def registerConfigFromJson(config_id):
    query = { '_id': ObjectId(config_id) }
    json_data = yarrdb.json.find_one( query )
    filename = json_data['filename']
    title = json_data['title']
    chip_type = json_data['chipType']
    if title == 'chipCfg': filename = 'chipCfg.json'
    path = 'tmp.json'
    
    with open(path, 'w') as f:
        json.dump( json_data['data'], f, indent=4 )
    binary_image = open(path, 'rb')
    binary = binary_image.read()
    shaHash = hashlib.sha256(binary)
    shaHashed = shaHash.hexdigest()
    query = {
        'dbVersion': db_version,
        'hash': shaHashed
    }
    data_doc = localdb.fs.files.find_one(query)
    if data_doc:
        data = str(data_doc['_id'])
    else:
        data = localfs.put( binary, filename=filename, hash=shaHashed, dbVersion=db_version )   
        c_query = { 'files_id': data }
        localdb.fs.chunks.update(
            c_query,
            {'$set':{'dbVersion': db_version}},
            multi=True
        )

    config_doc = { 
        'filename': filename, 
        'chipType': chip_type,
        'title'   : title,    
        'format'  : 'fs.files',
        'data_id' : str(data) 
    }
    config_id = localdb.config.insert( config_doc )
    
    write_log( '\t[Register] Config : {0} {1}'.format( filename, title ))
    return str(config_id)

def registerConfig(attachment, chip_type, new_ctr):
    code = attachment['code']
    contentType = attachment['contentType']
    binary = yarrfs.get(ObjectId(code)).read()
    shaHashed = hashlib.sha256(binary).hexdigest()

    return_doc = {
        'chip_id': -1,
        'tx': -1,
        'rx': -1
    }

    try:
        json_data = json.loads(binary.decode('utf-8')) 
    except:
        return return_doc
    query = {
        'dbVersion': db_version,
        'hash': shaHashed
    }

    data_doc = localdb.fs.files.find_one(query)
    if data_doc:
        code = str(data_doc['_id'])
    else:
        code = localfs.put( binary, filename='chipCfg.json', hash=shaHashed, dbVersion=db_version ) 
        c_query = { 'files_id': code }
        localdb.fs.chunks.update(
            c_query,
            {'$set':{'dbVersion': db_version}},
            multi=True
        )

    if chip_type in json_data:
        if chip_type == 'FE-I4B':
            return_doc.update({ 'chip_id': json_data[chip_type]['Parameter']['chipId'],
                                'tx': json_data[chip_type].get('tx',-1),
                                'rx': json_data[chip_type].get('rx',-1) })
        elif chip_type == 'RD53A':
            return_doc.update({ 'chip_id': json_data[chip_type]['Parameter']['ChipId'] })
    insert_doc = {
        'filename' : 'chipCfg.json',
        'chipType' : chip_type,
        'title'    : 'chipCfg',
        'format'   : 'fs.files',
        'data_id'  : str(code)
    }
    config_id = localdb.config.insert(insert_doc)
    ctr_query = { '_id': ObjectId(new_ctr['_id']) }
    localdb.componentTestRun.update( ctr_query, { '$set': { '{}Cfg'.format(contentType): str(config_id) }}) 

    write_log( '\t[Register] Config : {0} {1}'.format( 'chipCfg.json', '{}Cfg'.format(contentType) ))
    return return_doc

def registerDatFromDat(attachment, new_ctr_id):
    code = attachment['code']
    query = { '_id': ObjectId(code) }
    thisData = yarrdb.dat.find_one( query )
    if not thisData: return ''

    query = { '_id': ObjectId(new_ctr_id) }
    new_ctr = localdb.componentTestRun.find_one( query )
    thisDat = thisData['data']
    update_doc = {
        'title': attachment['title'],
        'filename': attachment['filename'],
    }
    for new_attachment in new_ctr.get('attachments', []):
        if new_attachment['title'] == update_doc['title'] and new_attachment['filename'] == update_doc['filename']:
            return ''

    path = './tmp.dat'
    with open(path, 'w') as f:
        f.write(thisDat['type']+'\n')
        f.write(thisDat['name']+'\n')
        f.write(thisDat['xaxisTitle']+'\n')
        f.write(thisDat['yaxisTitle']+'\n')
        f.write(thisDat['zaxisTitle']+'\n')
        f.write('{0} {1} {2}\n'.format(thisDat['xbins'], thisDat['xlow'], thisDat['xhigh']))
        if thisDat['type'] == 'Histo2d' or thisDat['type'] == 'Histo3d':
            f.write('{0} {1} {2}\n'.format(thisDat['ybins'], thisDat['ylow'], thisDat['yhigh']))
        if thisDat['type'] == 'Histo3d':
            f.write('{0} {1} {2}\n'.format(thisDat['zbins'], thisDat['zlow'], thisDat['zhigh']))
        f.write('{0} {1}\n'.format(thisDat['underflow'], thisDat['overflow']))
        if thisDat['type'] == 'Histo1d':
            for data in thisDat['dat']:
               f.write('{} '.format(data))
        elif thisDat['type'] == 'Histo2d':
            for line in thisDat['dat']:
                for data in line:
                    f.write('{} '.format(data))
                f.write('\n')
        elif thisDat['type'] == 'Histo3d':
            for line in thisDat['dat']:
                for data in line:
                    f.write('{} '.format(data))
                f.write('\n')
    binary_image = open(path, 'rb')
    binary = binary_image.read()
    code = localfs.put( binary, filename=thisData['filename'] )  
    attachment.update({ 'code': str(code) })
    ctr_query = { '_id': ObjectId(new_ctr['_id']) }
    localdb.componentTestRun.update( ctr_query, { '$push': { 'attachments': attachment }})

    write_log( '\t[Register] Dat : {0}'.format( thisData['filename'] ))
    return attachment['title']

def is_png(b):
    return bool(re.match(br"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", b[:8]))

def is_pdf(b):
    return bool(re.match(b"^%PDF", b[:4]))

def registerDat(attachment, name, new_ctr_id, plots):
    query = { '_id': ObjectId(new_ctr_id) }
    new_ctr = localdb.componentTestRun.find_one( query )
    code = attachment['code']
    bin_data = yarrfs.get(ObjectId(code)).read()
    if (is_png(bin_data)): 
        return ''
    if (is_pdf(bin_data)): 
        return ''
    if not 'Histo' in bin_data.decode('utf-8').split('\n')[0][0:7]: return ''

    filename = attachment['filename']
    if name in filename:       filename = filename.split(name)[1][1:].replace('_','-')
    elif 'chipId' in filename: filename = filename.split('chipId')[1][2:].replace('_','-')
    else:                      filename = filename[filename.rfind('_')+1:]
    #for plot in plots:
    #    if plot:
    #        if plot in attachment['filename']: filename = plot

    update_doc = {
        'title': filename,
        'filename': '{0}.dat'.format(filename),
    }
    for new_attachment in new_ctr.get('attachments', []):
        if new_attachment['title'] == update_doc['title'] and new_attachment['filename'] == update_doc['filename']:
            return ''

    binary = yarrfs.get(ObjectId(code)).read()
    code = localfs.put( binary, filename='{0}.dat'.format(filename) ) 
    ctr_query = { '_id': ObjectId(new_ctr['_id']) }
    localdb.componentTestRun.update( ctr_query, { 
        '$push': { 
            'attachments': { 
                'code'       : str(code),
                'dateTime'   : attachment['dateTime'],
                'title'      : filename, 
                'description': 'describe',
                'contentType': 'dat',
                'filename'   : '{0}.dat'.format(filename) 
            }
        }
    })

    write_log( '\t-----------------------------------------')
    write_log( '\t[Register] Dat : {0} -> {1} : {2}'.format(attachment['filename'], filename, code))
    return filename

def registerPng(attachment, name, new_ctr, plots):
    code = attachment['code']
    binary = yarrfs.get(ObjectId(code)).read()
    if not (is_png(binary)): 
        return ''

    filename = attachment['filename']
    if name in filename:       filename = filename.split(name)[1][1:].replace('_','-')
    elif 'chipId' in filename: filename = filename.split('chipId')[1][2:].replace('_','-')
    else:                      filename = filename[filename.rfind('_')+1:]
    for plot in plots:
        if plot:
            if plot in attachment['filename']: filename = plot

    update_doc = {
        'title': filename,
        'filename': '{0}.png'.format(filename),
    }
    for new_attachment in new_ctr.get('attachments', []):
        if new_attachment['title'] == update_doc['title'] and new_attachment['filename'] == update_doc['filename']:
            return ''

    code = localfs.put( binary, filename='{0}.png'.format(filename) ) 
    ctr_query = { '_id': ObjectId(new_ctr['_id']) }
    localdb.componentTestRun.update( ctr_query, { 
        '$push': { 
            'attachments': { 
                'code'       : str(code),
                'dateTime'   : attachment['dateTime'],
                'title'      : filename, 
                'description': 'describe',
                'contentType': 'png',
                'filename'   : '{0}.png'.format(filename) 
            }
        }
    })

    write_log( '\t[Register] Png : {0} -> {0}'.format(attachment['filename'], filename))
    return filename

def addStage(stage, new_stage, new_trid):
    if (not stage == '') and new_stage == '...':
        query = { '_id': ObjectId(new_trid) }
        localdb.testRun.update(
            query,
            {'$set': {'stage': stage}}
        )

def convert():
    start_time = datetime.datetime.now() 
    start_update_time = ''
    finish_update_time = ''
    write_log( '[Start] convertDB.py' )

    # modify module document
    start_update_time = datetime.datetime.now() 
    print( '# Convert database scheme' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
    write_log( '==============================================' )
    write_log( '[Convert] database: yarrdb' )

    query = { 'componentType' : 'Module' }
    entries = yarrdb.component.find( query )
    moduleids = []
    for entry in entries: # module entry
        moduleids.append( str(entry['_id']) )
    for moduleid in moduleids:
        query = { '_id': ObjectId(moduleid) }
        thisModule = yarrdb.component.find_one( query )

        write_log( '----------------------------------------------' )
        write_log( '[Start] Module: {}'.format( thisModule['serialNumber'] ) )

        new_mo_id = checkComponent(thisModule, '') # check and insert if not exist component data
        moduleid = {'old': str(thisModule['_id']),
                    'new': new_mo_id}
        
        mo_serial_number = thisModule['serialNumber']
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Module: {}'.format(mo_serial_number)) )
        
        ### convert module - testRun (if registered)
        query = { 'parent': str(thisModule['_id']) }
        child_entries = yarrdb.childParentRelation.find( query )
        chipids = []
        ctr_query = []
        ctr_query.append({'component':str(thisModule['_id'])})
        for child in child_entries:
            query = { '_id': ObjectId(child['child']) }
            thisChip = yarrdb.component.find_one( query )
            new_ch_id = checkComponent(thisChip, new_mo_id) # check and insert if not exist component data
            chipids.append({'old': child['child'],
                            'new': new_ch_id})
            ctr_query.append({'component':child['child']}) 
        query = { '$or': ctr_query }
        ctr_entries = yarrdb.componentTestRun.find( query )
        trid_entries = []
        for ctr_entry in ctr_entries:
            trid_entries.append( ctr_entry['testRun'] )
        new_trids = {}
        for trid in trid_entries:
            query = { '_id': ObjectId(trid) }
            thisRun = yarrdb.testRun.find_one( query )
            new_trid = checkTestRun(thisRun, mo_serial_number) # check and insert if not exist test data
            if new_trid in new_trids:
                new_trids[new_trid].append( trid )
            else:
                new_trids.update({ new_trid: [] })
                new_trids[new_trid].append( trid )

        for new_trid in new_trids:
            plots = []
            new_tr_query = { '_id': ObjectId(new_trid) }
            new_thisRun = localdb.testRun.find_one( new_tr_query )
            write_log( '        runNumber: {}'.format( new_thisRun['runNumber'] ) )
            # for module
            new_ctrid = checkComponentTestRun(moduleid['new'], new_trid)
            new_ctr_query = { '_id': ObjectId(new_ctrid) }
            new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
            for trid in new_trids[new_trid]:
                query = { '_id': ObjectId(trid) }
                thisRun = yarrdb.testRun.find_one( query )
                query = { 'component': moduleid['old'],
                          'testRun': trid }
                thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
                if thisComponentTestRun:
                    attachments = thisRun.get('attachments',[])
                    for attachment in attachments: 
                        title = registerPng(attachment, mo_serial_number, new_thisComponentTestRun, plots)
                        if not title == '':
                            plots.append(title)
            for chip in chipids:
                new_ctrid = checkComponentTestRun(chip['new'], new_trid)
                new_ctr_query = { '_id': ObjectId(new_ctrid) }
                new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )

                new_ch_query = { '_id': ObjectId(chip['new']) }
                new_thisChip = localdb.component.find_one( new_ch_query )
                chip_type = new_thisChip['chipType']
                write_log( '        chip serial: {}'.format( new_thisChip['serialNumber'] ) )
                if chip_type == "FEI4B": chip_type = "FE_I4B"

                query = { '_id': ObjectId(chip['old']) }
                thisChip = yarrdb.component.find_one( query )
                chip_name = thisChip.get('name','')
                for trid in new_trids[new_trid]:
                    query = { '_id': ObjectId(trid) }
                    thisRun = yarrdb.testRun.find_one( query )
                    query = { 'component': chip['old'],
                              'testRun': trid }
                    thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
                    if thisComponentTestRun:
                        # stage
                        addStage(thisComponentTestRun.get('stage',''), new_thisRun['stage'], new_trid)
                        addStage(thisRun.get('stage',''), new_thisRun['stage'], new_trid)
                        # chiptype
                        if new_thisRun['chipType'] == '...':
                            localdb.testRun.update(
                                new_tr_query,
                                {'$set': {'chipType': chip_type }}
                            )
                            new_thisRun = localdb.testRun.find_one( new_tr_query )
                        # environment
                        if (not thisComponentTestRun.get('environments',[]) == []) and new_thisRun['environment'] == '...':
                            env_id = registerEnvFromCtr(thisComponentTestRun, new_thisRun['startTime'])
                            localdb.testRun.update(
                                new_tr_query,
                                {'$set': {'environment': env_id}}   
                            )
                            new_thisRun = localdb.testRun.find_one( new_tr_query )
                        # controller config
                        if 'ctrlCfg' in thisRun and new_thisRun['ctrlCfg'] == '...':
                            ctrl_id = registerConfigFromJson(thisRun['ctrlCfg'])
                            localdb.testRun.update(
                                new_tr_query,
                                {'$set': {'ctrlCfg': ctrl_id}}
                            )
                            new_thisRun = localdb.testRun.find_one( new_tr_query )
                        # scan config
                        if 'scanCfg' in thisRun and new_thisRun['scanCfg'] == '...':
                            scan_id = registerConfigFromJson(thisRun['scanCfg'])
                            localdb.testRun.update(
                                new_tr_query,
                                {'$set': {'scanCfg': scan_id}}
                            )
                            new_thisRun = localdb.testRun.find_one( new_tr_query )
                        attachments = thisComponentTestRun.get('attachments',[])
                        for attachment in attachments: 
                            title = registerDatFromDat(attachment, new_ctrid)
                            if not title == '':
                                plots.append(title)

                        if new_thisComponentTestRun.get('beforeCfg','...') == '...':
                            if not thisComponentTestRun.get('beforeCfg', '...') == '...':
                                config_id = registerConfigFromJson(thisComponentTestRun['beforeCfg'])
                                localdb.componentTestRun.update(
                                    new_ctr_query,
                                    {'$set': {'beforeCfg': config_id}}
                                )
                                new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
                        if new_thisComponentTestRun.get('afterCfg','...') == '...':
                            if not thisComponentTestRun.get('afterCfg', '...') == '...':
                                config_id = registerConfigFromJson(thisComponentTestRun['afterCfg'])
                                localdb.componentTestRun.update(
                                    new_ctr_query,
                                    {'$set': {'afterCfg': config_id}}
                                )
                                new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
                        attachments = thisRun.get('attachments',[])
                        for attachment in attachments: 
                            title = registerDat(attachment, chip_name, new_ctrid, plots)
                            if not title == '':
                                plots.append(title)
                            if attachment['contentType'] == 'after': 
                                if new_thisComponentTestRun.get('afterCfg','...') == '...':
                                    return_doc = registerConfig(attachment, chip_type, new_thisComponentTestRun)
                                    if not return_doc['chip_id'] == -1 and new_thisChip['chipId'] == -1:
                                        localdb.component.update(
                                            new_ch_query,
                                            {'$set': { 'chipId': return_doc['chip_id'] }}
                                        )
                                        new_thisChip = localdb.component.find_one( new_ch_query )
                                        query = { 'parent': new_mo_id, 'child': chip['new'] }
                                        localdb.childParentRelation.update(
                                            query,
                                            {'$set': { 'chipId': return_doc['chip_id'] }}
                                        )
                                    if not return_doc['chip_id'] == -1 and new_thisComponentTestRun['geomId'] == -1:
                                        localdb.component.update(
                                            new_ctr_query,
                                            {'$set': { 'geomId': return_doc['chip_id'] }}
                                        )
                                        new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
                                    if new_thisComponentTestRun['tx'] == -1 and not return_doc['tx'] == -1:
                                        localdb.component.update(
                                            new_ch_query,
                                            {'$set': { 'tx': return_doc['tx'], 'rx': return_doc['rx'] }}
                                        )
                                        new_thisChip = localdb.component.find_one( new_ch_query )
                            if attachment['contentType'] == 'before': 
                                if new_thisComponentTestRun.get('beforeCfg','...') == '...':
                                    return_doc = registerConfig(attachment, chip_type, new_thisComponentTestRun)
                                    if not return_doc['chip_id'] == -1 and new_thisChip['chipId'] == -1:
                                        localdb.component.update(
                                            new_ch_query,
                                            {'$set': { 'chipId': return_doc['chip_id'] }}
                                        )
                                        new_thisChip = localdb.component.find_one( new_ch_query )
                                    if not return_doc['chip_id'] == -1 and new_thisComponentTestRun['geomId'] == -1:
                                        localdb.component.update(
                                            new_ctr_query,
                                            {'$set': { 'geomId': return_doc['chip_id'] }}
                                        )
                                        new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
                                    if new_thisComponentTestRun['tx'] == -1 and not return_doc['tx'] == -1:
                                        localdb.component.update(
                                            new_ch_query,
                                            {'$set': { 'tx': return_doc['tx'], 'rx': return_doc['rx'] }}
                                        )
                                        new_thisChip = localdb.component.find_one( new_ch_query )
                if new_thisChip['chipId'] == -1:
                    localdb.component.update(
                        new_ch_query,
                        {'$set': { 'chipId': 0 }}
                    )
            if new_thisRun.get('plots',[]) == []:
                for plot in list(set(plots)):
                    localdb.testRun.update(
                        new_tr_query,
                        {'$push': {'plots': plot}}
                    )

    finish_update_time = datetime.datetime.now() 
    write_log( '==============================================' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
    print( '\t# Succeeded in conversion.' )
    print( ' ' )
        
    finish_time = datetime.datetime.now()
    write_log( '====        Operation Time        ====' )
    total_time = datetime.timedelta(seconds=(finish_time-start_time).total_seconds())
    write_log( 'Total time: ' + str(total_time))
    write_log( start_time.strftime(  '\tStart: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( finish_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f' ) )
    if not start_update_time == '':
        total_update_time = datetime.timedelta(seconds=(finish_update_time-start_update_time).total_seconds())
        write_log( '--------------------------------------' )
        write_log( 'Update total time:  ' + str(total_update_time) )
        write_log( start_update_time.strftime( '\tStart: %Y-%m-%dT%H:%M:%S:%f' ) )
        write_log( finish_update_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( '======================================' )
    log_file.close()
    
    print( start_time.strftime( '# Start time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( finish_time.strftime( '# Finish time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( '# Total time: ' + str(total_time) + ' [s]' ) 
    print( ' ' )
    print( '# The path to log file: {}'.format(log_filename) )
    print( ' ' )
    print( '# Exit ...' )
    sys.exit()     

if __name__ == '__main__': convert()
