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
import os, sys, datetime, json, re, hashlib, argparse, yaml, uuid, time
import gridfs
from   pymongo       import MongoClient
from   bson.objectid import ObjectId   

### Set DBs
url = 'mongodb://127.0.0.1:27017' 
client = MongoClient( url )
new_db = 'localdb'
copy_db = 'localdb_replica'
old_db  = 'yarrdb'
yarrdb  = client[old_db]
localdb = client[new_db]
yarrfs  = gridfs.GridFS( yarrdb )
localfs = gridfs.GridFS( localdb )
db_version = 1.01

### Set log file
log_dir = './log'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
now = datetime.datetime.now() 
log_filename = now.strftime('{}/logConvert_%m%d_%H%M.txt'.format(log_dir))
log_file = open( log_filename, 'w' )

#start
start_time_utc = datetime.datetime.utcnow() 

def write_log( text ):
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S {}\n'.format(text) ) )

#############################
# Check if data is registered
def checkCol(i_col):
    write_log( '----------------------------------------------' )
    write_log( '[Start] {0:<20} Collection'.format(i_col) )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S {0:<20} Collection'.format(i_col) ))
    entries = yarrdb[i_col].find({},projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        if   i_col=='component'          : checkComponent(oid)
        elif i_col=='childParentRelation': checkChildParentRelation(oid)
        elif i_col=='componentTestRun'   : checkComponentTestRun(oid)
        elif i_col=='testRun'            : checkTestRun(oid)

def checkChip(i_oid): 
    query = { '_id': ObjectId(i_oid) }
    col = 'chip'
    thisCmp = localdb.component.find_one(query)

    if thisCmp['componentType']=='module':
        return 'module'

    query = {
        'name'     : thisCmp['serialNumber'],
        'chipId'   : thisCmp['chipId'], 
        'chipType' : thisCmp['chipType'],
        'dbVersion': db_version
    } 
    this = localdb[col].find_one( query )

    if this:
        oid = str(this['_id'])
    else:
        oid = registerChip(i_oid)
    
    return oid

def checkComponent(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'component'
    this = yarrdb[col].find_one(query)

    component_type = this['componentType'].lower().replace(' ','_')
    if component_type=='module':
        query = { 'parent': i_oid }
        this_cpr = yarrdb.childParentRelation.find_one(query)
        if this_cpr:
            query = { '_id': ObjectId(this_cpr['child']) }
            this_chip = yarrdb.component.find_one(query)
            if 'chipType' in this_chip:
                chip_type = this_chip['chipType']
            else:
                chip_type = this_chip['componentType']
        else:
            chip_type = 'unknown'
    else:
        component_type = 'front-end_chip'
        if 'chipType' in this:
            chip_type = this['chipType']
        else:
            chip_type = this['componentType']
    if chip_type == 'FEI4B': chip_type = 'FE-I4B'

    query = { 
        'serialNumber' : this['serialNumber'],
        'componentType': component_type.lower().replace(' ','_'),
        'chipType'     : chip_type,
        'dbVersion'    : db_version
    }
    this = localdb[col].find_one(query)

    if this:
        oid = str(this['_id'])
    else:
        oid = registerComponent(i_oid, component_type, chip_type)
    
    return oid

def checkChildParentRelation(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'childParentRelation'
    this = yarrdb[col].find_one(query)

    ### child
    ch_oid = checkComponent(this['child'])
    ### parent
    mo_oid = checkComponent(this['parent'])

    query = { 
        'parent'   : mo_oid, 
        'child'    : ch_oid,
        'status'   :'active',
        'dbVersion': db_version
    }
    this = localdb[col].find_one(query)
    if not this:
        registerChildParentRelation(ch_oid, mo_oid) 

def checkUser(i_user_name=os.environ['USER'], i_institution=os.environ['HOSTNAME'], i_description='default'):
    col = 'user'
    query = {
        'userName'   : i_user_name.lower().replace(' ','_'),
        'institution': i_institution.lower().replace(' ','_'),
        'description': i_description,
        'dbVersion'  : db_version
    }
    this = localdb[col].find_one(query)

    if this:
        oid = str(this['_id'])
    else:
        oid = registerUser(i_user_name, i_institution, i_description)
    
    return oid

def checkSite(i_institution=os.environ['HOSTNAME']):
    col = 'institution'
    site_query = {
        'institution': i_institution.lower().replace(' ','_'),
        'dbVersion'  : db_version
    }

    this = localdb[col].find_one( site_query )
    if this:
        oid = str(this['_id'])
    else:
        oid = registerSite(i_institution)
    
    return oid 

def checkTestRun(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'testRun'
    this = yarrdb[col].find_one(query)

    ### user and site
    if 'userIdentity' in this:
        user_name     = this['userIdentity']
        institution   = this['institution']
        user_identity = 'default'
    else:
        query = { '_id': ObjectId(this['user_id']) }
        thisUser = yarrdb.user.find_one( query )
        user_name     = thisUser['userName']
        institution   = thisUser['institution']
        user_identity = thisUser['userIdentity']
    user_oid = checkUser(user_name, institution, user_identity) 
    site_oid = checkSite(institution)

    query = {
        'user_id'  : user_oid,
        'address'  : site_oid,
        'testType' : this['testType'],
        'runNumber': this['runNumber'],
        'dbVersion': db_version
    }
    this = localdb[col].find_one(query)
    if this:
        oid = str(this['_id'])
    else:
        oid = registerTestRun(i_oid, user_oid, site_oid)

    ### stage
    query = { '_id': ObjectId(i_oid) }
    this_old = yarrdb[col].find_one(query)
    query = { '_id': ObjectId(oid) }
    this_new = localdb[col].find_one(query)
    addStage(this_old.get('stage',''), oid)
    query = { 'testRun': i_oid }
    entries = yarrdb.componentTestRun.find(query, projection={'_id':1})
    ctr_oids = []
    for entry in entries:
        ctr_oids.append(str(entry['_id']))
    for ctr_oid in ctr_oids:
        query = { '_id': ObjectId(ctr_oid) }
        thisCtr = yarrdb.componentTestRun.find_one(query)
        addStage(thisCtr.get('stage',''), oid)

    ### config
    for key in this_old:
        if 'Cfg' in key and not this_old[key]=='...' and this_new.get(key, '...')=='...':
            registerConfigFromJson(this_old[key], oid, col, key)

    return oid

def checkComponentTestRun(i_oid=None, i_cmp_oid=None, i_tr_oid=None):
    col = 'componentTestRun'
    if i_oid:
        query = { '_id': ObjectId(i_oid) }
        this = yarrdb[col].find_one(query)

    ### component
    if i_cmp_oid:
        cmp_oid = i_cmp_oid
    else:
        cmp_oid = checkComponent(this['component'])
    ### testRun
    if i_tr_oid:
        tr_oid = i_tr_oid
    else:
        tr_oid = checkTestRun(this['testRun'])

    query = {
        'component': cmp_oid,
        'testRun'  : tr_oid,
        'dbVersion': db_version
    }
    this = localdb[col].find_one( query )
    if this:
        oid = str(this['_id'])
    else:
        oid = registerComponentTestRun(cmp_oid, tr_oid)

    if i_oid:
        addValue( col, oid, 'enable', 1 )
    else:
        return oid

    ### attachment
    query = { '_id': ObjectId(i_oid) }
    this_old = yarrdb[col].find_one(query)
    query = { '_id': ObjectId(oid) }
    this_new = localdb[col].find_one( query )

    query = { '_id': ObjectId(cmp_oid) }
    thisCmp = localdb.component.find_one(query)

    query = { '_id': ObjectId(this_old['testRun']) }
    thisRun = yarrdb.testRun.find_one(query)
    plots = []
    for attachment in thisRun.get('attachments',[]):
        title = registerAttachment(attachment, thisCmp['name'], oid, 'dat') 
        if not title == '':
            plots.append(title)
        if thisCmp['componentType']=='module':
            title = registerAttachment(attachment, thisCmp['name'], oid, 'png')
            if not title == '':
                plots.append(title)
        if attachment['contentType']=='after' or attachment['contentType']=='before': 
            registerConfig(attachment, oid)
    for attachment in this_new.get('attachments',[]): 
        title = registerDatFromDat(attachment, oid)
        if not title == '':
            plots.append(title)

    query = { '_id': ObjectId(tr_oid) }
    thisRun = localdb.testRun.find_one(query)
    if thisRun.get('plots',[])==[]:
        for plot in list(set(plots)):
            update_doc = {'$push': {'plots': plot}}
            localdb.testRun.update_one(query, update_doc)

    ### config
    for key in this_old:
        if 'Cfg' in key and not this_old[key]=='...' and this_new.get(key, '...')=='...':
            registerConfigFromJson(this_old[key], oid, col, key)

    ### environment
    checkEnvironment(i_oid, oid, tr_oid)

    return oid
 
def checkEnvironment(i_old_oid, i_new_oid, i_tr_oid):
    query = { '_id': ObjectId(i_old_oid) }
    thisCtr = yarrdb.componentTestRun.find_one(query)
    query = { '_id': ObjectId(i_tr_oid) }
    thisRun = localdb.testRun.find_one(query)
    start_time = thisRun['startTime']
    finish_time = thisRun['finishTime']
    query = { '_id': ObjectId(i_new_oid) }
    this = localdb.componentTestRun.find_one(query)
    if not this.get('environment', '...')=='...':
        return
   
    col = 'environment'
    insert_doc = {}
    for env_doc in thisCtr.get('environments',[]):
        insert_doc.update({
            env_doc['key'].lower().replace(' ','_'): [{
                'data': [{ 
                    'date' : start_time,
                    'value': env_doc['value']
                }],
                'description': env_doc['description'],
                'mode': 'null',
                'setting': -1,
                'num': 0
            }]
        })

    query = {
        '$and': [
            { 'date': { '$gt': start_time - datetime.timedelta(minutes=1) }},
            { 'date': { '$lt': finish_time +  datetime.timedelta(minutes=1) }}
        ]
    }
    environment_entries = yarrdb[col].find( query )
    env_dict = {}
    description = {}
    for environment in environment_entries:
        if not environment['key'].lower().replace(' ','_') in env_dict:
            env_dict.update({ environment['key'].lower().replace(' ','_'): [] })
        env_dict[environment['key'].lower().replace(' ','_')].append({
            'date' : environment['date'],
            'value': environment['value']
        })
        description.update({ environment['key'].lower().replace(' ','_'): environment['description'] })
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
        oid = localdb[col].insert_one(insert_doc).inserted_id
        updateVer(str(oid), col)
        updateSys(str(oid), col)
        addValue( 'componentTestRun', i_new_oid, 'environment', str(oid) )
        addValue( 'testRun', i_tr_oid, 'environment', True )

        write_log( '\t[Register] Environment' )
        return True
    else:
        return False

#####################
# Update DB Structure
def updateCol(i_col):
    write_log( '----------------------------------------------' )
    write_log( '[Start] {0:<20} Collection'.format(i_col) )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S {0:<20} Collection'.format(i_col) ))
    entries = localdb[i_col].find({},projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        if   i_col=='chip'               : update = updateChip(oid)
        elif i_col=='component'          : update = updateComponent(oid)
        elif i_col=='childParentRelation': update = updateChildParentRelation(oid)
        elif i_col=='user'               : update = updateUser(oid)
        elif i_col=='institution'        : update = updateSite(oid)
        elif i_col=='componentTestRun'   : update = updateComponentTestRun(oid)
        elif i_col=='testRun'            : update = updateTestRun(oid)
        if update:
            updateSys(oid, i_col)
            updateVer(oid, i_col)

            write_log( '\t[Update] {0:<20} : {1}'.format(i_col, oid))

def updateChip(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'chip'
    this = localdb[col].find_one(query)

    update_doc = {
        '$set': {
            'name'         : this['name'],
            'chipId'       : this['chipId'], 
            'chipType'     : this['chipType'],
            'componentType': this['componentType'].lower().replace(' ','_'),
        }
    }
    query = { '_id': ObjectId(i_oid) }
    localdb[col].update_one( query, update_doc )
    return True

def updateComponent(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'component'

    this = localdb[col].find_one(query)

    ### user
    query = { 
        '_id'      : ObjectId(this['user_id']),
        'dbVersion': db_version
    }
    thisUser = localdb.user.find_one(query)
    if not thisUser: user_oid = checkUser()
    else: user_oid = str(thisUser['_id'])

    ### site
    query = { 
        '_id'      : ObjectId(this['address']), 
        'dbVersion': db_version
    }
    thisSite = localdb.institution.find_one(query)
    if not thisSite: site_oid = checkSite()
    else: site_oid = str(thisSite['_id'])

    update_doc = {
        'serialNumber' : this['serialNumber'],
        'chipType'     : this['chipType'],
        'componentType': this['componentType'].lower().replace(' ','_'),
        'name'         : this['serialNumber'],
        'chipId'       : this.get('chipId',-1), 
        'address'      : site_oid, 
        'user_id'      : user_oid,
        'children'     : this.get('children',-1),
        'proDB'        : False
    }
    query = { '_id': ObjectId(i_oid) }
    localdb[col].update_one( query, { '$set': update_doc } )
    return True

def updateChildParentRelation(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'childParentRelation'
    this = localdb[col].find_one(query)

    ### child
    query = { 
        '_id'      : ObjectId(this['child']),
        'dbVersion': db_version
    }
    thisChild = localdb.component.find_one(query)

    ### parent
    query = {
        '_id'      : ObjectId(this['parent']),
        'dbVersion': db_version
    }
    thisParent = localdb.component.find_one(query)

    if not thisChild or not thisParent:
        write_log( '\t[Failed] {0:<20} : Not found child or parent: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False

    update_doc = { 
        '$set': {
            'status': this.get('status', 'active') 
        }
    }
    if thisChild:
        if not this['chipId']==thisChild['chipId']:
            query = { '_id': ObjectId(i_oid) }
            update_doc['$set'].update({
                'chipId': thisChild['chipId'] 
            })
    localdb[col].update_one( query, update_doc )
    return True

def updateUser(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'user'
    this = localdb[col].find_one(query)
    update_doc = {
        'userName'   : this.get('userName' , os.environ['USER']).lower().replace(' ','_'),
        'institution': this.get('institution', os.environ['HOSTNAME']).lower().replace(' ','_'),
        'description': this.get('description', 'default'),
        'USER'       : this.get('USER', os.environ['USER']),
        'HOSTNAME'   : this.get('HOSTNAME', os.environ['HOSTNAME'])
    }
    query = { '_id': ObjectId(i_oid) }
    localdb[col].update_one( query, { '$set': update_doc } )
    return True

def updateSite(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'institution'
    this = localdb[col].find_one(query)
    if this.get('address', '')=='':
        address = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)for ele in range(0,8*6,8)][::-1])
    else:
        address = this['address']
    update_doc = {
        'address'    : address,
        'HOSTNAME'   : this.get('hostname', os.environ['HOSTNAME']),
        'institution': this.get('institution', os.environ['HOSTNAME']).lower().replace(' ','_')
    }
    query = { '_id': ObjectId(i_oid) }
    localdb[col].update_one( query, { '$set': update_doc } )
    return True

def updateTestRun(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'testRun'
    this = localdb[col].find_one(query)

    ### user
    query = { 
        '_id'      : ObjectId(this['user_id']),
        'dbVersion': db_version
    }
    thisUser = localdb.user.find_one(query)
    if not thisUser: user_oid = checkUser()
    else: user_oid = str(thisUser['_id'])

    ### site
    query = { 
        '_id'      : ObjectId(this['address']),
        'dbVersion': db_version
    }
    thisSite = localdb.institution.find_one(query)
    if not thisSite: site_oid = checkSite()
    else: site_oid = str(thisSite['_id'])

    ### componentTestRun
    query = { 
        'testRun'  : i_oid,
        'dbVersion': db_version
    }
    if localdb.componentTestRun.count_documents(query)==0:
        write_log( '\t[Failed] {0:<20} : Not found componentTestRun: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False

    ctr_entries = localdb.componentTestRun.find(query,projection={'chip':1})
    for this_ctr in ctr_entries:
        if this_ctr['chip']=='module': continue
        query = { '_id': ObjectId(this_ctr['chip']) }
        this_chip = localdb.chip.find_one(query)
        chip_type = this_chip['chipType']
        break

    ### config
    config_doc = {}
    for key in this:
        if 'Cfg' in key and not this[key]=='...':
            config_doc.update({ key: updateConfig(this[key]) })

    ### environment
    dcs = updateEnvironment(col, this.get('environment', '...'))

    start_time = this.get('startTime', this['sys'].get('cts',this['sys']['mts']))
    finish_time = this.get('finishTime', None)
    if not finish_time: finish_time = start_time

    update_doc = {
        '$set': {
            'testType'   : this.get('testType', '...'),
            'runNumber'  : this.get('runNumber', -1),
            'stage'      : this.get('stage', '...').lower().replace(' ','_'),
            'chipType'   : chip_type,
            'address'    : site_oid,
            'user_id'    : user_oid,
            'environment': dcs,
            'plots'      : this.get('plots', []),
            'passed'     : this.get('passed', True),
            'qaTest'     : this.get('qaTest', False),
            'qcTest'     : this.get('qcTest', False),
            'summary'    : this.get('summary', False), 
            'startTime'  : start_time,
            'finishTime' : finish_time
        }
    }
    update_doc['$set'].update(config_doc)
    query = { '_id': ObjectId(i_oid) }
    localdb[col].update_one( query, update_doc )
    return True

def updateComponentTestRun(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'componentTestRun'
    this = localdb[col].find_one(query)

    ### chip
    thisChip = None
    if not this.get('chip', 'module')=='module' and not this.get('chip','...')=='...':
        query = { 
            '_id'      : ObjectId(this['chip']),
            'dbVersion': db_version
        }
        thisChip = localdb.chip.find_one(query)

    ### component
    thisCmp = None
    if this.get('component',None):
        try:
            query = { 
                '_id'      : ObjectId(this['component']), 
                'dbVersion': db_version
            }
            thisCmp = localdb.component.find_one(query)
            cmp_oid = str(thisCmp['_id'])
        except:
            cmp_oid = '...'
    else:
        cmp_oid = '...'

    if not thisChip and thisCmp:
        chip_oid = checkChip(str(thisCmp['_id'])) 
    else:
        chip_oid = this.get('chip', '...')

    ### testRun
    query = { '_id': ObjectId(this['testRun']) }
    thisRun = localdb.testRun.find_one(query)

    if not thisRun:
        write_log( '\t[Failed] {0:<20} : Not found testRun: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False

    if chip_oid=='module':
        name = thisCmp['serialNumber']
    elif chip_oid=='...':
        name = this.get('name', 'DisabledChip')
    else:
        query = { '_id': ObjectId(chip_oid) }
        thisChip = localdb.chip.find_one(query)
        name = thisChip['name']

    ### attachments
    attachments = []
    for this_attachment in this.get('attachments', []):
        if updateAttachment(this_attachment['code'], this_attachment['contentType']):
            attachments.append(this_attachment)

    ### config
    config_doc = {}
    for key in this:
        if 'Cfg' in key and not this[key]=='...':
            config_doc.update({ key: updateConfig(this[key]) })

    ### environment
    if updateEnvironment(col, this.get('environment','...')):
        dcs = this['environment']
    else:
        dcs = '...'

    ### componentTestRun
    update_doc = {
        '$set': {
            'component'  : cmp_oid,
            'chip'       : chip_oid,
            'testRun'    : this['testRun'],
            'attachments': attachments,
            'name'       : name,
            'tx'         : this.get('tx', -1), 
            'rx'         : this.get('rx', -1), 
            'environment': dcs 
        }
    }
    update_doc['$set'].update(config_doc)
    query = { '_id': ObjectId(i_oid) }
    localdb[col].update_one( query, update_doc )
    return True
 
def updateEnvironment(i_col, i_oid):

    if i_oid=='...':
        return False

    if type(i_oid)==bool:
        return i_oid

    query = { '_id': ObjectId(i_oid) }
    col = 'environment'
    this = localdb[col].find_one(query)

    if not this:
        if i_col=='testRun':
            query = { 'environment': i_oid }
            run_entries = localdb.testRun.find(query,projection={'_id':1})
            for this_run in run_entries:
                addValue( 'testRun', str(this_run['_id']), 'environment', False )
        elif i_col=='componentTestRun':
            query = { 'environment': i_oid }
            this_ctr = localdb.componentTestRun.find_one(query)
            if this_ctr:
                addValue( 'componentTestRun', str(this_ctr['_id']), 'environment', '...' )
        return False

    if i_col=='testRun':
        insert_doc = {}
        for key in this:
            if not key=='_id' and not key=='sys' and not key=='dbVersion':
                insert_doc.update({ key.lower().replace(' ','_'): this[key] })
        insert_doc.update({ 'sys': {} })
        query = { 'environment': i_oid }
        run_entries = localdb.testRun.find(query,projection={'_id':1})
        for this_run in run_entries:
            query = { 'testRun': str(this_run['_id']) }
            ctr_entries = localdb.componentTestRun.find(query,projection={'_id':1})
            env_docs = []
            for this_ctr in ctr_entries:
                insert_doc.pop('_id',None)
                oid = localdb[col].insert_one(insert_doc).inserted_id
                updateSys(str(oid), col)
                updateVer(str(oid), col)
                addValue( 'componentTestRun', str(this_ctr['_id']), 'environment', str(oid) )
            addValue( 'testRun', str(this_run['_id']), 'environment', True )
        write_log( '\t[Update] {0:<20} Disabled original document: {1}'.format(col, i_oid))
        disabled(i_oid, col)

    elif i_col=='componentTestRun':
        updateVer(i_oid, col)

    updateSys(i_oid, col)
    write_log( '\t[Update] {0:<20} : {1}'.format(col, str(i_oid)))
    return True

def updateConfig(i_oid):

    if i_oid=='...': 
        return '...'

    ### config
    query = { '_id': ObjectId(i_oid) }
    this = localdb.config.find_one(query)
    if not this:
        return '...'

    ### fs.files
    query = { '_id': ObjectId(this['data_id']) }
    this_file = localdb.fs.files.find_one(query)

    ### fs.chunks
    query = { 'files_id': ObjectId(this['data_id']) }
    this_chunks = localdb.fs.chunks.count_documents(query)

    if not this_file or this_chunks==0:
        return '...'

    updateVer(i_oid, 'config')
    updateSys(i_oid, 'config')
    updateVer(this['data_id'], 'fs.files')
    updateSys(this['data_id'], 'fs.files')

    write_log( '\t[Update] {0:<20} : {1}'.format('config', i_oid))
    return i_oid

def updateAttachment(i_oid, i_type):

    ### fs.files
    query = { '_id': ObjectId(i_oid) }
    this_file = localdb.fs.files.find_one(query)

    ### fs.chunks
    query = { 'files_id': ObjectId(i_oid) }
    this_chunks = localdb.fs.chunks.count_documents(query)

    if not this_file or this_chunks==0:
        return False

    if i_type=='dat' and not is_dat(localfs.get(ObjectId(i_oid)).read()):
        write_log( '\t[Failed] {0:<20} : Not dat data: {1}'.format('fs.files', i_oid))
        disabled(i_oid, 'fs.files')
        return False
    if i_type=='png' and not is_png(localfs.get(ObjectId(i_oid)).read()):
        write_log( '\t[Failed] {0:<20} : Not png data: {1}'.format('fs.files', i_oid))
        disabled(i_oid, 'fs.files')
        return False 

    updateVer(i_oid, 'fs.files')
    updateSys(i_oid, 'fs.files')

    write_log( '\t[Update] {0:<20} : {1}'.format('fs.files', i_oid))
    return True 

#####################
# Verify DB Structure
def verifyCol(i_col):
    write_log( '----------------------------------------------' )
    write_log( '[Start] {0:<20} Collection'.format(i_col) )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S {0:<20} Collection'.format(i_col) ))
    entries = localdb[i_col].find({},projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        if   i_col=='chip'               : verify = verifyChip(oid)
        elif i_col=='component'          : verify = verifyComponent(oid)
        elif i_col=='childParentRelation': verify = verifyChildParentRelation(oid)
        elif i_col=='user'               : verify = verifyUser(oid)
        elif i_col=='institution'        : verify = verifySite(oid)
        elif i_col=='componentTestRun'   : verify = verifyComponentTestRun(oid)
        elif i_col=='testRun'            : verify = verifyTestRun(oid)
        if verify:
            updateSys(oid, i_col)
            write_log( '\t[Verify] {0:<20} : {1}'.format(i_col, oid))

def verifyChip(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'chip'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return False

    keys = {
        'name'         : 'str',
        'chipId'       : 0,
        'chipType'     : 'str',
        'componentType': 'str',
        'sys'          : {}
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key])==True:
            write_log( '\t[Failed] {0:<20} : Not found key {1} in document: {2}'.format(col, key, i_oid))
            disabled(i_oid, col)
            return False
    ### component type
    if not this['componentType']=='front-end_chip':
        write_log( '\t[Failed] {0:<20} : componentType is not "front-end_chip": {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t[Failed] {0:<20} : Not match dbVersion: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False

def verifyComponent(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'component'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return False

    keys = {
        'serialNumber' : 'str',
        'componentType': 'str',
        'chipType'     : 'str',
        'name'         : 'str',
        'chipId'       : 0,
        'address'      : 'str',
        'user_id'      : 'str',
        'children'     : 0,
        'proDB'        : True,
        'sys'          : {}
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key])==True:
            write_log( '\t[Failed] {0:<20} : Not found key {1} in document: {2}'.format(col, key, i_oid))
            disabled(i_oid, col)
            return False
    ### user
    query = { 
        '_id': ObjectId(this['user_id']),
        'dbVersion': db_version
    }
    thisUser = localdb.user.find_one(query)
    if not thisUser:
        write_log( '\t[Failed] {0:<20} : Not found user document: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### site
    query = { 
        '_id': ObjectId(this['address']),
        'dbVersion': db_version
    }
    thisSite = localdb.institution.find_one(query)
    if not thisSite:
        write_log( '\t[Failed] {0:<20} : Not found site document: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### cpr
    query = { 
        '$or'      : [{
            'parent': str(this['_id'])
        },{
            'child': str(this['_id'])
        }],
        'dbVersion': db_version,
        'status'   : 'active'
    }
    if localdb.childParentRelation.count_documents(query)==0:
        write_log( '\t[Failed] {0:<20} : Not match cpr counts: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t[Failed] {0:<20} : Not match dbVersion: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False

    return True

def verifyChildParentRelation(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'childParentRelation'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return False

    keys = {
        'sys'   : {}, 
        'parent': 'str', 
        'child' : 'str',
        'chipId': 0,
        'status': 'str'
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key])==True:
            write_log( '\t[Failed] {0:<20} : Not found key {1} in document: {2}'.format(col, key, i_oid))
            disabled(i_oid, col)
            return False
    ### child
    query = { 
        '_id'      : ObjectId(this['child']),
        'dbVersion': db_version
    }
    if not localdb.component.find_one(query):
        write_log( '\t[Failed] {0:<20} : Not found child: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### parent
    query = {
        '_id'      : ObjectId(this['parent']),
        'dbVersion': db_version
    }
    if not localdb.component.find_one(query):
        write_log( '\t[Failed] {0:<20} : Not found parent: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t[Failed] {0:<20} : Not match dbVersion: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False

    return True

def verifyUser(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'user'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return False

    keys = {
        'userName'   : 'str',
        'institution': 'str',
        'description': 'str',
        'USER'       : 'str',
        'HOSTNAME'   : 'str',
        'sys'        : {}
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key]):
            write_log( '\t[Failed] {0:<20} : Not found key {1} in document: {2}'.format(col, key, i_oid))
            disabled(i_oid, col)
            return False
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t[Failed] {0:<20} : Not match dbVersion: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False

    return True

def verifySite(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'institution'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return False

    keys = {
        'address'    : 'str',
        'HOSTNAME'   : 'str',
        'institution': 'str',
        'sys'        : {}
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key])==True:
            write_log( '\t[Failed] {0:<20} : Not found key {1} in document: {2}'.format(col, key, i_oid))
            disabled(i_oid, col)
            return False
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t[Failed] {0:<20} : Not match dbVersion: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False

    return True

def verifyTestRun(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'testRun'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return False

    keys = {
        'testType'   : 'str',
        'runNumber'  : 0,
        'stage'      : 'str',
        'chipType'   : 'str',
        'address'    : 'str',
        'user_id'    : 'str',
        'environment': True,
        'plots'      : [],
        'passed'     : True,
        'qcTest'     : True,
        'qaTest'     : True,
        'summary'    : True,
        'startTime'  : datetime.datetime.now(),
        'finishTime' : datetime.datetime.now()
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key])==True:
            write_log( '\t[Failed] {0:<20} : Not found key {1} in document: {2}'.format(col, key, i_oid))
            disabled(i_oid, col)
            return False
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t[Failed] {0:<20} : Not match dbVersion: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### user
    query = { 
        '_id'      : ObjectId(this['user_id']),
        'dbVersion': db_version
    }
    if not localdb.user.find_one(query):
        write_log( '\t[Failed] {0:<20} : Not found user document: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### site
    query = { 
        '_id'      : ObjectId(this['address']),
        'dbVersion': db_version
    }
    if not localdb.institution.find_one(query):
        write_log( '\t[Failed] {0:<20} : Not found site document: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### componentTestRun
    query = { 
        'testRun'  : i_oid,
        'dbVersion': db_version
    }
    if localdb.componentTestRun.count_documents(query)==0:
        write_log( '\t[Failed] {0:<20} : Not found componentTestRun: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### config
    for key in this:
        if 'Cfg' in key and not this[key]=='...':
            query = { '_id': ObjectId(this[key]) }
            if not localdb.config.find_one(query):
                write_log( '\t[Failed] {0:<20} : Not found config document: {1}'.format(col, i_oid))
                disabled(i_oid, col)
                return False
            thisCfg = localdb.config.find_one(query)
            if not is_json(localfs.get(ObjectId(thisCfg['data_id'])).read()):
                write_log( '\t[Failed] {0:<20} : Not json data: {1}'.format(col, i_oid))
                disabled(i_oid, col)
                return False
    ### environment
    if this.get('environment', False):
        query = { 
            'testRun'  : i_oid,
            'dbVersion': db_version
        }
        entries = localdb.componentTestRun.find(query, projection={'environment':1})
        dcs = False
        for entry in entries:
            if not entry.get('environment', '...')=='...':
                dcs = True
        if not dcs:
            write_log( '\t[Failed] {0:<20} : Problems in DCS: {1}'.format(col, i_oid))
            disabled(i_oid, col)
            return False

    return True

def verifyComponentTestRun(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'componentTestRun'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return False

    keys = {
        'sys'        : {}, 
        'component'  : 'str',
        'chip'       : 'str',
        'testRun'    : 'str',
        'attachments': [],
        'tx'         : 0,
        'rx'         : 0,
        'environment': 'str',
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key])==True:
            write_log( '\t[Failed] {0:<20} : Not found key {1} in document: {2}'.format(col, key, i_oid))
            disabled(i_oid, col)
            return False
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t[Failed] {0:<20} : Not match dbVersion: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False

    ### component
    if not this.get('component', '...')=='...':
        query = {
            '_id'      : ObjectId(this['component']),
            'dbVersion': db_version
        }
        if not localdb.component.find_one(query):
            write_log( '\t[Failed] {0:<20} : Not found component document: {1}'.format(col, i_oid))
            disabled(i_oid, col)
            return False
    ### chip
    if not this.get('chip', 'module')=='module' and not this.get('chip','...')=='...':
        query = { 
            '_id'      : ObjectId(this['chip']),
            'dbVersion': db_version
        }
        if not localdb.chip.find_one(query):
            write_log( '\t[Failed] {0:<20} : Not found chip document: {1}'.format(col, i_oid))
            disabled(i_oid, col)
            return False
    ### testRun
    query = { 
        '_id'      : ObjectId(this['testRun']),
        'dbVersion': db_version
    }
    if not localdb.testRun.find_one(query):
        write_log( '\t[Failed] {0:<20} : Not found testRun document: {1}'.format(col, i_oid))
        disabled(i_oid, col)
        return False
    ### attachments
    for entry in this.get('attachments', []):
        if entry['contentType']=='dat':
            if not is_dat(localfs.get(ObjectId(entry['code'])).read()):
                write_log( '\t[Failed] {0:<20} : Not dat data: {1}'.format(col, i_oid))
                disabled(i_oid, col)
                return False
        elif entry['contentType']=='png':
            if not is_png(localfs.get(ObjectId(entry['code'])).read()):
                write_log( '\t[Failed] {0:<20} : Not png data: {1}'.format(col, i_oid))
                disabled(i_oid, col)
                return False
        else:
            write_log( '\t[Failed] {0:<20} : Unknown type: {1}'.format(col, i_oid))
            disabled(i_oid, col)
            return False
    ### config
    for key in this:
        if 'Cfg' in key and not this[key]=='...':
            query = { '_id': ObjectId(this[key]) }
            if not localdb.config.find_one(query):
                write_log( '\t[Failed] {0:<20} : Not found config document: {1}'.format(col, i_oid))
                disabled(i_oid, col)
                return False
            thisCfg = localdb.config.find_one(query)
            if not is_json(localfs.get(ObjectId(thisCfg['data_id'])).read()):
                write_log( '\t[Failed] {0:<20} : Not json data: {1}'.format(col, i_oid))
                disabled(i_oid, col)
                return False
    ### environment
    if not this.get('environment','...')=='...':
        query = { '_id': ObjectId(this['environment']) }
        if not localdb.environment.find_one(query):
            write_log( '\t[Failed] {0:<20} : Not found DCS data: {1}'.format(col, i_oid))
            disabled(i_oid, col)
            return False

    return True 

###################
# Register document
def registerChip(i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'chip'

    thisCmp = localdb.component.find_one(query)
    insert_doc = {
        'sys'          : {},
        'name'         : thisCmp['serialNumber'],
        'chipId'       : thisCmp['chipId'], 
        'chipType'     : thisCmp['chipType'],
        'componentType': 'front-end_chip',
    } 
    oid = localdb[col].insert_one(insert_doc).inserted_id
    updateSys(str(oid), col)
    updateVer(str(oid), col)
    write_log( '\t[Register] {0:<20} : {1}'.format(col, str(oid)) )

    return str(oid)

def registerComponent(i_oid, i_type, i_chip_type):
    query = { '_id': ObjectId(i_oid) }
    col = 'component'
    this = yarrdb[col].find_one(query)

    component_type = i_type 
    chip_type = i_chip_type
    if component_type=='module':
        query = { 'parent': i_oid }
        children = yarrdb.childParentRelation.count_documents(query)
    else:
        children = -1

    ### user and site
    if 'userIdentity' in this:
        user_name     = this['userIdentity']
        institution   = this['institution']
        user_identity = 'default'
    else:
        query = { '_id': ObjectId(this['user_id']) }
        thisUser = yarrdb.user.find_one( query )
        user_name     = thisUser['userName']
        institution   = thisUser['institution']
        user_identity = thisUser['userIdentity']
    user_oid = checkUser(user_name, institution, user_identity)
    site_oid = checkSite(institution)
 
    insert_doc = {
        'sys'          : {},
        'serialNumber' : this['serialNumber'],
        'componentType': component_type.lower().replace(' ','_'),
        'chipType'     : chip_type,
        'name'         : this['serialNumber'],
        'chipId'       : -1, 
        'address'      : site_oid, 
        'user_id'      : user_oid,
        'children'     : children,
        'proDB'        : False
    } 
    cmp_oid = localdb[col].insert_one(insert_doc).inserted_id
    updateSys(str(cmp_oid), col)
    updateVer(str(cmp_oid), col)

    write_log( '\t[Register] {0:<20} : {1}'.format(col, str(cmp_oid)) )

    return str(cmp_oid)

def registerChildParentRelation(i_ch_oid, i_mo_oid):
    col = 'childParentRelation'

    insert_doc = {
        'sys'   : {},
        'parent': i_mo_oid,
        'child' : i_ch_oid,
        'status': 'active',
        'chipId': -1
    }
    oid = localdb[col].insert_one( insert_doc ).inserted_id
    updateSys(str(oid), col)
    updateVer(str(oid), col)
    write_log( '\t[Register] {0:<20} : {1}'.format(col, str(oid)) )

def registerUser(i_user_name, i_institution, i_description, i_user=os.environ['USER'], i_hostname=os.environ['HOSTNAME']):
    col = 'user'
    insert_doc = {
        'sys'        : {},
        'userName'   : i_user_name.lower().replace(' ','_'),
        'institution': i_institution.lower().replace(' ','_'),
        'description': i_description,
        'userType'   : 'readWrite',
        'USER'       : i_user, 
        'HOSTNAME'   : i_hostname
    }

    oid = localdb[col].insert_one(insert_doc).inserted_id
    updateSys(str(oid), col)
    updateVer(str(oid), col)

    write_log( '\t[Register] {0:<20} : {1}'.format(col, str(oid)) )
    return str(oid)

def registerSite(i_institution, i_address=':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)for ele in range(0,8*6,8)][::-1]), i_hostname=os.environ['HOSTNAME']):
    col = 'institution'
    insert_doc = {
        'sys'        : {},
        'address'    : i_address,
        'institution': i_institution.lower().replace(' ','_'),
        'HOSTNAME'   : i_hostname
    }

    oid = localdb[col].insert_one(insert_doc).inserted_id
    updateSys(str(oid), col)
    updateVer(str(oid), col)

    write_log( '\t[Register] {0:<20} : {1}'.format(col, str(oid)) )
    return str(oid)
 
def registerTestRun(i_oid, i_user_oid, i_site_oid):
    col = 'testRun'
    query = { '_id': ObjectId(i_oid) }
    this = yarrdb[col].find_one(query)

    if 'startTime' in this:
        start_time  = this['startTime']
    else:
        start_time  = this['date']
    if 'finishTime' in this:
        finish_time = this['finishTime']
    else:
        finish_time = start_time

    insert_doc = {
        'sys'         : {},
        'testType'    : this['testType'],
        'runNumber'   : this['runNumber'],
        'startTime'   : start_time,
        'finishTime'  : finish_time,
        'stage'       : '...', 
        'passed'      : True,
        'qcTest'      : False,
        'qaTest'      : False,
        'summary'     : this.get('display', False),
        'targetCharge': this.get('targetCharge',-1),
        'targetTot'   : this.get('targetTot',-1),
        'exec'        : '...',
        'plots'       : [], 
        'chipType'    : '...',
        'environment' : False,
        'user_id'     : i_user_oid, 
        'address'     : i_site_oid
    }

    oid = localdb[col].insert_one(insert_doc).inserted_id
    updateSys(str(oid), col)
    updateVer(str(oid), col)

    write_log( '\t[Register] {0:<20} : {1}'.format(col, str(oid)) )
    return str(oid)

def registerComponentTestRun(i_cmp_oid, i_tr_oid):
    col = 'componentTestRun'

    # testRun
    query = { '_id': ObjectId(i_tr_oid) }
    thisRun = localdb.testRun.find_one(query)
    # component
    query = { '_id': ObjectId(i_cmp_oid) }
    thisCmp = localdb.component.find_one(query)

    insert_doc = {
        'sys'        : {},
        'component'  : i_cmp_oid,
        'testRun'    : i_tr_oid,
        'chip'       : '...',
        'attachments': [],
        'name'       : thisCmp['name'],
        'tx'         : -1, 
        'rx'         : -1,
        'enable'     : 0,
        'environment': '...',
    }

    oid = localdb[col].insert_one(insert_doc).inserted_id
    updateSys(str(oid), col)
    updateVer(str(oid), col)

    write_log( '\t[Register] {0:<20} : {1}'.format(col, str(oid)) )
    return str(oid)

def registerConfigFromJson(i_config_oid, i_oid, i_col, i_key):
    query = { '_id': ObjectId(i_config_oid) }
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
        'hash'     : shaHashed
    }
    data_doc = localdb.fs.files.find_one(query)
    if data_doc:
        data = str(data_doc['_id'])
    else:
        data = localfs.put( binary, filename=filename, hash=shaHashed, dbVersion=db_version )   
        updateSys(str(data), 'fs.files')

    config_doc = { 
        'filename': filename, 
        'chipType': chip_type,
        'title'   : title,    
        'format'  : 'fs.files',
        'data_id' : str(data) 
    }
    oid = localdb.config.insert_one(config_doc).inserted_id
    updateSys(str(oid), 'config')
    updateVer(str(oid), 'config')
    addValue( i_col, i_oid, i_key, str(oid) )
    
    write_log( '\t[Register] {0:<20} : {1}'.format('config', str(oid)) )
    return str(oid)

def registerConfig(attachment, i_ctr_oid):
    chip_id = None
    tx = None
    rx = None

    query = { '_id': ObjectId(i_ctr_oid) }
    thisCtr = localdb.componentTestRun.find_one(query)

    contentType = attachment['contentType']

    code = attachment['code']
    data_id = None
    binary = yarrfs.get(ObjectId(code)).read()
    try:
        json_data = json.loads(binary.decode('utf-8')) 
    except:
        json_data = {}

    if not thisCtr.get('{}Cfg'.format(contentType), '...')=='...':
        config_oid = thisCtr['{}Cfg'.format(contentType)]
        query = { '_id': ObjectId(config_oid) }
        thisCfg = localdb.config.find_one(query)
        data_id = thisCfg['data_id']
        binary = localfs.get(ObjectId(data_id)).read()
        try:
            json_data = json.loads(binary.decode('utf-8'))
        except:
            write_log( '\t[Failed] {0:<20} : Not json format: {1}'.format('config', config_oid))
            disabled(config_oid, 'config')
            addValue( 'componentTestRun', i_ctr_oid, '{}Cfg'.format(contentType), '...' )

    if 'FE-I4B' in json_data:
        chip_id = json_data['FE-I4B']['Parameter']['chipId']
        tx      = json_data['FE-I4B'].get('tx',-1)
        rx      = json_data['FE-I4B'].get('rx',-1) 
        chip_type = 'FE-I4B'
    elif 'RD53A' in json_data:
        chip_id = json_data['RD53A']['Parameter']['ChipId'] 
        chip_type = 'RD53A'
    else:
        if not thisCtr.get('{}Cfg'.format(contentType), '...')=='...':
            addValue( 'componentTestRun', i_ctr_oid, '{}Cfg'.format(contentType), '...' )
        return 

    shaHashed = hashlib.sha256(binary).hexdigest()
    query = {
        'dbVersion': db_version,
        'hash'     : shaHashed
    }
    data_doc = localdb.fs.files.find_one(query)
    if data_doc:
        code = str(data_doc['_id'])
    else:
        code = localfs.put( binary, filename='chipCfg.json', hash=shaHashed, dbVersion=db_version ) 
        updateSys(str(code), 'fs.files')

    if not data_id or not data_id==str(code):
        insert_doc = {
            'filename' : 'chipCfg.json',
            'chipType' : chip_type,
            'title'    : 'chipCfg',
            'format'   : 'fs.files',
            'data_id'  : str(code)
        }
        config_oid = localdb.config.insert_one(insert_doc).inserted_id
        updateSys(str(config_oid), 'config')
        updateVer(str(config_oid), 'config')
        addValue( 'componentTestRun', i_ctr_oid, '{}Cfg'.format(contentType), str(config_oid) )

    query = { '_id': ObjectId(thisCtr['component']) }
    thisCmp = localdb.component.find_one(query)
    if chip_id and thisCmp['chipId']==-1:
        addValue( 'component', thisCtr['component'], 'chipId', chip_id )
        query = { 'child': thisCtr['component'] }
        thisCpr = localdb.childParentRelation.find_one(query)
        addValue( 'childParentRelation', str(thisCpr['_id']), 'chipId', chip_id )
    if tx and thisCtr.get('tx',-1)==-1:
        addValue( 'componentTestRun', i_ctr_oid, 'tx', tx )
        addValue( 'componentTestRun', i_ctr_oid, 'rx', rx )

    write_log( '\t[Register] {0:<20} : {1}'.format('config', str(config_oid)) )
    return 

def registerDatFromDat(attachment, i_oid):
    code = attachment['code']
    query = { '_id': ObjectId(code) }
    thisData = yarrdb.dat.find_one( query )
    if not thisData: 
        return ''

    query = { '_id': ObjectId(i_oid) }
    col = 'componentTestRun'
    this = localdb[col].find_one( query )
    thisDat = thisData['data']
    for new_attachment in this.get('attachments', []):
        if new_attachment['title']==attachment['title'] and new_attachment['filename']==attachment['filename']:
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
    code = localfs.put( binary, filename=thisData['filename'], dbVersion=db_version )  
    updateSys(str(code), 'fs.files')

    attachment.update({ 'code': str(code) })
    query = { '_id': ObjectId(i_oid) }
    localdb[col].update_one( query, { '$push': { 'attachments': attachment }})
    updateSys(i_oid, col)

    write_log( '\t[Register] {0:<20} : {1}'.format('fs.files', str(code)) )
    return attachment['title']

def registerAttachment(i_attachment, i_name, i_oid, i_type):
    query = { '_id': ObjectId(i_oid) }
    thisCtr = localdb.componentTestRun.find_one( query )
    code = i_attachment['code']
    binary = yarrfs.get(ObjectId(code)).read()
    if i_type=='png' and not is_png(binary):
        return ''
    if i_type=='dat' and not is_dat(binary): 
        return ''

    filename = i_attachment['filename']
    if i_name in filename:     filename = filename.split(i_name)[1][1:].replace('_','-')
    elif 'chipId' in filename: filename = filename.split('chipId')[1][2:].replace('_','-')
    else:                      filename = filename[filename.rfind('_')+1:]

    for new_attachment in thisCtr.get('attachments', []):
        if new_attachment['title']==filename and new_attachment['filename']=='{0}.{1}'.format(filename, i_type):
            return ''

    code = localfs.put( binary, filename='{0}.{1}'.format(filename, i_type), dbVersion=db_version ) 
    updateSys(str(code), 'fs.files')

    query = { '_id': ObjectId(i_oid) }
    localdb.componentTestRun.update_one( query, { 
        '$push': { 
            'attachments': { 
                'code'       : str(code),
                'dateTime'   : i_attachment['dateTime'],
                'title'      : filename, 
                'description': 'describe',
                'contentType': i_type,
                'filename'   : '{0}.{1}'.format(filename, i_type) 
            }
        }
    })
    updateSys(i_oid, 'componentTestRun')

    write_log( '\t[Register] {0:<20} : {1}'.format('fs.files', str(code)))
    return filename

def is_png(b):
    return bool(re.match(br"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", b[:8]))

def is_pdf(b):
    return bool(re.match(b"^%PDF", b[:4]))

def is_dat(b):
    try:
        this = bool('Histo' in b.decode('utf-8').split('\n')[0][0:7])
    except:
        this = False
    return this

def is_json(b):
    try:
        json_data = json.loads(b.decode('utf-8')) 
        return True
    except:
        return False

def addStage(i_stage, i_oid):
    query = { '_id': ObjectId(i_oid) }
    col = 'testRun'
    this = localdb[col].find_one(query)
    if not i_stage=='' and this.get('stage', '...')=='...':
        query = { '_id': ObjectId(i_oid) }
        update_doc = {
            '$set': {
                'stage': i_stage.lower().replace(' ','_')
            }
        }
        localdb[col].update_one(query, update_doc)
        updateSys(i_oid, col)

def addValue( i_col, i_oid, i_key, i_value ):
    query = { '_id': ObjectId(i_oid) }
    update_doc = { '$set': { i_key: i_value } }
    localdb[i_col].update_one( query, update_doc )
    updateSys(i_oid, i_col)

def updateVer(i_oid, i_col):
    query = { '_id': ObjectId(i_oid) }
    this = localdb[i_col].find_one(query)

    if not this: return
    if this.get('dbVersion',None)==db_version: return

    update_doc = { '$set': { 'dbVersion': db_version } }
    localdb[i_col].update_one( query, update_doc )

def updateSys(i_oid, i_col):
    query = { '_id': ObjectId(i_oid) }
    this = localdb[i_col].find_one(query)

    if not this: return

    now = datetime.datetime.utcnow()

    if this.get('sys',{}).get('mts',None):
        if this['sys']['mts']>start_time_utc: return

    if this.get('sys',{})=={}:
        update_doc = { 
            '$set': {
                'sys': {
                    'cts': now,
                    'mts': now,
                    'rev': 0
                }
            }
        }
    else:
        update_doc = {
            '$set': {
                'sys': {
                    'cts': this['sys'].get('cts', now),
                    'mts': now,
                    'rev': this['sys']['rev']+1
                }
            }
        }
    localdb[i_col].update_one( query, update_doc )

def disabled(i_oid, i_col):
    query = { '_id': ObjectId(i_oid) }
    update_doc = {
        '$set': {
            'update_failed': True,
            'dbVersion'    : -1
        }
    }
    localdb[i_col].update_one( query, update_doc )
    updateSys(i_oid, i_col)

def checkEmpty(i_doc, i_key, i_type='str'):
    if not i_key in i_doc:
        return False
    elif not type(i_doc[i_key])==type(i_type):
        return False
    else:
        return True

def confirm():
    ### Confirmation
    write_log( '----------------------------------------------' )
    write_log( '[Start] Confirmation' )
    cols = localdb.list_collection_names()
    for col in cols:
        if col=='fs.chunks': continue
        query = { 'dbVersion': {'$ne': db_version}, 'update_failed': {'$ne': True} }
        entries = localdb[col].find(query, projection={'_id':1})
        for entry in entries:
            write_log( '\t[Failed] {0:<20} : Not match DB version: {1}'.format(col, str(entry['_id'])))
            disabled(str(entry['_id']), col)
            addValue( col, str(entry['_id']), 'dbVersion', -1 )
        query = { 'update_failed': True }
        entries = localdb[col].find(query, projection={'_id':1})
        for entry in entries:
            if entry.get('dbVersion',-1)==db_version: 
                addValue( col, str(entry['_id']), 'dbVersion', -1 )
        print('\tCollection: {0:<25} ... disabled: {1:<6} / {2:<6}'.format(col, localdb[col].count_documents(query), localdb[col].count_documents({})))

def outputTime(i_start_time, i_finish_time, i_function):
    write_log( '----------------------------------------------' )
    write_log( '[Finish]' )
    write_log( '==============================================' )
    print( '\t# Succeeded in {}'.format(i_function) )
    print( ' ' )
        
    write_log( '====        Operation Time        ====' )
    total_time = datetime.timedelta(seconds=(i_finish_time-i_start_time).total_seconds())
    write_log( '{0:<15} total time:  {1}'.format(i_function, total_time) )
    write_log( i_start_time.strftime( '\tStart: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( i_finish_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( '======================================' )
    
    print( i_start_time.strftime( '# Start time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( i_finish_time.strftime( '# Finish time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( '# Total time: ' + str(total_time) + ' [s]' ) 
    print( ' ' )

#################
# Update Function
# localdb(old ver) -> localdb(latest ver)
def update():
    start_update_time = ''
    finish_update_time = ''

    # update documents
    start_update_time = datetime.datetime.now() 
    print( '# Update database scheme: {}'.format(new_db) )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
    write_log( '==============================================' )
    write_log( '[Update] database: {}'.format(new_db) )

    ### user
    updateCol('user')
   
    ### site
    updateCol('institution')

    ### chip
    updateCol('chip')

    ### component
    updateCol('component')

    ### childParentRelation
    updateCol('childParentRelation')

    ### componentTestRun
    updateCol('componentTestRun')

    ### testRun
    updateCol('testRun')

    confirm()

    finish_update_time = datetime.datetime.now() 
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
    outputTime(start_update_time, finish_update_time, 'Update')

##################
# Convert Function
# yarrdb(old ver) -> localdb(latest ver)
def convert():
    start_convert_time = ''
    finish_convert_time = ''

    # convert database structure
    start_convert_time = datetime.datetime.now() 
    print( '# Convert database scheme: {0} -> {1}'.format(old_db, new_db) )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
    write_log( '==============================================' )
    write_log( '[Convert] database: {}'.format(old_db) )

    ### component
    checkCol('component')

    ### childParentRelation
    checkCol('childParentRelation')

    ### testRun
    checkCol('testRun')

    ### componentTestRun
    checkCol('componentTestRun')

    ### relationships and attachments
    write_log( '----------------------------------------------' )
    write_log( '[Start] Attachments and Relationships' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Attachments and Relationships' ))
    query = { 'componentType': 'module' }
    entries = localdb.component.find(query,projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        cmp_oids = []
        cmp_oids.append({ 'component': oid })
        query = { 'parent': oid }
        entries = localdb.childParentRelation.find(query,projection={'child':1})
        for entry in entries:
            cmp_oids.append({ 'component': entry['child'] })
        query = { '$or': cmp_oids }
        entries = localdb.componentTestRun.find(query,projection={'testRun':1})
        tr_oids = []
        for entry in entries:
            tr_oids.append(entry['testRun'])
        for tr_oid in list(set(tr_oids)):
            chip_type = None
            for i, cmp_oid in enumerate(cmp_oids):
                query = { '_id': ObjectId(cmp_oid['component']) }
                thisCmp = localdb.component.find_one(query)
                ctr_oid = checkComponentTestRun(None, cmp_oid['component'], tr_oid)
                col = 'componentTestRun'
                if thisCmp['componentType']=='module':
                    addValue( col, ctr_oid, 'chip', 'module' )
                else:
                    chip_oid = checkChip(cmp_oid['component'])
                    addValue( col, ctr_oid, 'chip', chip_oid )
                    addValue( col, ctr_oid, 'geomId', i-1 )
                query = { '_id': ObjectId(cmp_oid['component']) }
                thisCmp = localdb.component.find_one(query)
                if not thisCmp.get('chipType','...')=='...':
                    chip_type = thisCmp['chipType']
            query = { '_id': ObjectId(tr_oid) }
            thisRun = localdb.testRun.find_one(query)
            # chiptype
            if thisRun.get('chipType','...')=='...' and chip_type:
                addValue( 'testRun', tr_oid, 'chipType', chip_type )

    ### Confirmation
    confirm()

    finish_convert_time = datetime.datetime.now() 
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
    outputTime(start_convert_time, finish_convert_time, 'Conversion')

def verify():
    start_verify_time = ''
    finish_verify_time = ''

    # verigy database structure
    start_verify_time = datetime.datetime.now() 
    print( '# Verify database scheme: {}'.format(new_db) )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
    write_log( '==============================================' )
    write_log( '[Verify] database: {}'.format(new_db) )

    ### user
    verifyCol('user')
   
    ### site
    verifyCol('institution')

    ### chip
    verifyCol('chip')

    ### component
    verifyCol('component')

    ### childParentRelation
    verifyCol('childParentRelation')

    ### componentTestRun
    verifyCol('componentTestRun')

    ### testRun
    verifyCol('testRun')

    ### Confirmation
    confirm()

    finish_verify_time = datetime.datetime.now() 
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
    outputTime(start_verify_time, finish_verify_time, 'Verification')

def main():
    start_time = datetime.datetime.now() 
    write_log( '[Start] convertDB.py' )

    dbs = client.list_database_names()
    if copy_db in dbs:
        print( '# {} is found.'.format(copy_db) )
        print( ' ' )
        answer = ''
        while not answer == 'y' and not answer == 'n':
            answer = input( '# Do you make it back to the original DB: {0} ---> {1}? (y/n) > '.format(copy_db, new_db) )
        print( ' ' )
        if answer == 'y' :
            print( '# Restoring ...' )
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
            client.drop_database( new_db )
            client.admin.command( 'copydb',
                                  fromdb=copy_db,
                                  todb=new_db )#COPY 
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]' ) )
            print( '# Succeeded in Restoring.' )
            print( ' ' )

    answer = ''
    while not answer == 'y' and not answer =='n':
        answer = input( '# Do you replicate DB: {0} ---> {1}? (y/n) > '.format( new_db, copy_db ) )
    print( ' ' )
    if answer == 'y':
        if copy_db in dbs:
            print( '# {} is found.'.format(copy_db) )
            print( ' ' )
            answer = ''
            while not answer == 'y' and not answer == 'n':
                answer = input( '# Do you override DB: {0} ---> {1}? (y/n) > '.format(new_db, copy_db) )
            print( ' ' )
            if answer == 'y' :
                client.drop_database( copy_db )
            else:
                print( '# Cannot replicating then exit.' )
                sys.exit()
        # copy database for buckup
        print( '# Replicating database to "{}" for replica ... '.format(copy_db) )
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
        client.admin.command( 'copydb',
                              fromdb=new_db,
                              todb=copy_db ) 
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]' ) )
        print( '# Succeeded in replicating.' )
        print( ' ' )

    answer = ''
    while not answer == 'y' and not answer =='n':
        answer = input( '# Continue to convert DB: {0}/{1}(old) ---> {1}(latest)? (y/n) > '.format(old_db, new_db) )
    print( ' ' )
    if not answer == 'y':
        print( '# Exit.' )
        sys.exit()

    update()
    convert()
    verify()

    finish_time = datetime.datetime.now() 
    print( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish]') )
    outputTime(start_time, finish_time, 'All Steps')

    log_file.close()

if __name__ == '__main__': main()
