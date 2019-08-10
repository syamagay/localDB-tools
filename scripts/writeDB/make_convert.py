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

### Functions
url = 'mongodb://127.0.0.1:27017' 
client = MongoClient( url )
yarrdb = client['yarrdb']
localdb = client['localdb']
yarrfs = gridfs.GridFS( yarrdb )
localfs = gridfs.GridFS( localdb )
db_version = 1.01
DEBUG = True

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

def checkChip(i_oid): 
    query = { '_id': ObjectId(i_oid) }
    thisCmp = localdb.component.find_one(query)

    if thisCmp['componentType']=='module':
        return 'module'

    query = {
        'name'     : thisCmp['serialNumber'],
        'chipId'   : thisCmp['chipType'], 
        'chipType' : thisCmp['chipType'],
        'dbVersion': db_version
    } 
    thisChip = localdb.chip.find_one( query )

    if thisChip:
        chip_oid = str(thisChip['_id'])
    else:
        chip_oid = registerChip(i_oid)
    
    return chip_oid

def updateChip(i_oid):
    write_log( '\t[Update] Chip : {}'.format(i_oid))

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
    updateSys(str(this['_id']), col)
    updateVer(str(this['_id']), col)
    write_log( '\t         Success.')

def verifyChip(i_oid):
    write_log( '\t[Verify] Chip : {}'.format(i_oid))

    query = { '_id': ObjectId(i_oid) }
    col = 'chip'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return

    keys = {
        'name'         : 'str',
        'chipId'       : 0,
        'chipType'     : 'str',
        'componentType': 'str',
        'sys'          : {}
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key]):
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### component type
    if not this['componentType']=='front-end_chip':
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return

    write_log( '\t         Success.')

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
    chip_oid = localdb[col].insert_one(insert_doc).inserted_id
    updateSys(str(chip_oid), col)
    updateVer(str(chip_oid), col)
    write_log( '\t[Register] Chip : {}'.format( thisCmp['serialNumber'] ) )

    return str(chip_oid)

def checkComponent(i_oid, i_type='front-end_chip'):
    query = { '_id': ObjectId(i_oid) }
    col = 'component'
    this = yarrdb[col].find_one(query)

    component_type = i_type
    if i_type=='module':
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
        if 'chipType' in this:
            chip_type = this['chipType']
        else:
            chip_type = this['componentType']
    if chip_type == 'FEI4B': chip_type = 'FE-I4B'

    query = { 
        'serialNumber' : this['serialNumber'],
        'componentType': component_type,
        'chipType'     : chip_type,
        'dbVersion'    : db_version
    }
    this = localdb[col].find_one(query)

    if this:
        oid = str(this['_id'])
    else:
        oid = registerComponent(i_oid, component_type, chip_type)
    
    return oid

def updateComponent(i_oid):
    write_log( '\t[Update] Component : {}'.format(i_oid))

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
    updateSys(i_oid, col)
    updateVer(i_oid, col)
    write_log( '\t         Success.')

def verifyComponent(i_oid):
    write_log( '\t[Verify] Component : {}'.format(i_oid))

    query = { '_id': ObjectId(i_oid) }
    col = 'component'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return

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
        if not checkEmpty(this, key, keys[key]):
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### user
    query = { 
        '_id': ObjectId(this['user_id']),
        'dbVersion': db_version
    }
    thisUser = localdb.user.find_one(query)
    if not thisUser:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### site
    query = { 
        '_id': ObjectId(this['address']),
        'dbVersion': db_version
    }
    thisSite = localdb.institution.find_one(query)
    if not thisSite:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
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
    if not localdb.childParentRelation.count_documents(query)==1:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return

    write_log( '\t         Success.')

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
    user_oid = checkUser(user_name, institution, user_identity, user_name, institution)
    site_oid = checkSite('', institution, institution)
 
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

    write_log( '\t[Register] Component : {}'.format( this['serialNumber'] ) )

    return str(cmp_oid)

def updateChildParentRelation(i_oid):
    write_log( '\t[Update] ChildParentRelation : {}'.format(i_oid))

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
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return

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
    updateSys(i_oid, col)
    updateVer(i_oid, col)
    write_log( '\t         Success.')
    return

def verifyChildParentRelation(i_oid):
    write_log( '\t[Verify] ChildParentRelation : {}'.format(i_oid))

    query = { '_id': ObjectId(i_oid) }
    col = 'childParentRelation'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return

    keys = {
        'sys'   : {}, 
        'parent': 'str', 
        'child' : 'str',
        'chipId': 0,
        'status': 'str'
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key]):
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### child
    query = { 
        '_id'      : ObjectId(this['child']),
        'dbVersion': db_version
    }
    if not localdb.component.find_one(query):
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### parent
    query = {
        '_id'      : ObjectId(this['parent']),
        'dbVersion': db_version
    }
    if not localdb.component.find_one(query):
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return

    write_log( '\t         Success.')

def checkChildParentRelation(i_ch_oid, i_mo_oid):
    query = { 
        'parent'   : i_mo_oid, 
        'child'    : i_ch_oid,
        'status'   :'active',
        'dbVersion': db_version
    }
    this = localdb.childParentRelation.find_one(query)
    if not this:
        registerChildParentRelation(i_ch_oid, i_mo_oid) 

def registerChildParentRelation(i_ch_oid, i_mo_oid):
    col = 'childParentRelation'

    insert_doc = {
        'sys': {},
        'parent': i_mo_oid,
        'child': i_ch_oid,
        'status': 'active',
        'chipId': -1
    }
    cpr_oid = localdb[col].insert_one( insert_doc ).inserted_id
    updateSys(str(cpr_oid), col)
    updateVer(str(cpr_oid), col)
    write_log( '\t[Register] ChildParentRelation' )

def checkUser(i_user_name=os.environ['USER'], i_institution=os.environ['HOSTNAME'], i_description='default', i_user=os.environ['USER'], i_hostname=os.environ['HOSTNAME'])
    col = 'user'
    query = {
        'userName'   : i_user_name.lower().replace(' ','_'),
        'institution': i_institution.lower().replace(' ','_'),
        'description': i_description,
        'USER'       : i_user,
        'HOSTNAME'   : i_hostname,
        'dbVersion'  : db_version
    }
    this = localdb[col].find_one(query)

    if this:
        oid = str(this['_id'])
    else:
        oid = registerUser(i_user_name, i_institution, i_description, i_user, i_hostname)
    
    return oid

def updateUser(i_oid):
    write_log( '\t[Update] User : {}'.format(i_oid))

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
    updateSys(i_oid, col)
    updateVer(i_oid, col)
    write_log( '\t         Success.')

def verifyUser(i_oid):
    write_log( '\t[Verify] User : {}'.format(i_oid))

    query = { '_id': ObjectId(i_oid) }
    col = 'user'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return

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
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return

    write_log( '\t         Success.')

def registerUser(i_user_name, i_institution, i_description, i_user, i_hostname):
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

    write_log( '\t[Register] User : {0} {1}'.format( i_user_name, i_institution ) )
    return str(oid)

def checkSite(i_address=':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)for ele in range(0,8*6,8)][::-1]), i_institution=os.environ['HOSTNAME'], i_hostname=os.environ['HOSTNAME']):
    col = 'institution'
    site_query = {
        'address'    : i_address,
        'institution': i_institution.lower().replace(' ','_'),
        'HOSTNAME'   : i_hostname,
        'dbVersion'  : db_version
    }

    this = localdb[col].find_one( site_query )
    if this:
        oid = str(this['_id'])
    else:
        oid = registerSite(i_address, i_institution, i_hostname)
    
    return oid 

def updateSite(i_oid):
    write_log( '\t[Update] Site : {}'.format(i_oid))

    query = { '_id': ObjectId(i_oid) }
    col = 'institution'
    this = localdb[col].find_one(query)
    update_doc = {
        'address'    : this.get('address', ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)for ele in range(0,8*6,8)][::-1])),
        'HOSTNAME'   : this.get('hostname', os.environ['HOSTNAME']),
        'institution': this.get('institution', os.environ['HOSTNAME']).lower().replace(' ','_')
    }
    query = { '_id': ObjectId(i_oid) }
    localdb[col].update_one( query, { '$set': update_doc } )
    updateSys(i_oid, col)
    updateVer(i_oid, col)
    write_log( '\t         Success.')

def verifySite(i_oid):
    write_log( '\t[Verify] Site : {}'.format(i_oid))

    query = { '_id': ObjectId(i_oid) }
    col = 'institution'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return

    keys = {
        'address'    : 'str',
        'HOSTNAME'   : 'str',
        'institution': 'str',
        'sys'        : {}
    }
    for key in keys:
        if not checkEmpty(this, key, keys[key]):
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return

    write_log( '\t         Success.')

def registerSite(i_address, i_institution, i_hostname):
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

    write_log( '\t[Register] Site : {0}'.format( i_institution ) )
    return str(oid)
 
def def checkTestRun(i_oid):
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
    user_oid = checkUser(user_name, institution, user_identity, user_name, institution) 
    site_oid = checkSite('', institution, institution)

    if 'startTime' in this:
        start_time  = this['startTime']
    else:
        start_time  = this['date']

    tr_query = {
        'startTime': start_time,
        'user_id'  : user_oid,
        'address'  : site_oid,
        'dbVersion': db_version
    }
    this = localdb.testRun.find_one( tr_query )
    if this:
        oid = str(this['_id'])
    else:
        oid = registerTestRun(i_oid, start_time, user_oid, site_oid)

    return oid

def updateTestRun(i_oid):
    write_log( '\t[Update] TestRun : {}'.format(i_oid))

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
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return

    ctr_entries = localdb.componentTestRun.find(query,projection={'chip':1})
    for this_ctr in ctr_entries:
        if this_ctr['chip']=='module': continue
        query = { '_id': ObjectId(this_ctr['chip']) }
        this_chip = localdb.chip.find_one(query)
        chip_type = this_chip['chipType']
        break

    ### environment
    dcs = updateEnvironment(col, this.get('environment', '...'))

    start_time = this.get('startTime', this['sys']['cts'])
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
            'summary'    : this.get('summary', False), #TODO
            'startTime'  : start_time,
            'finishTime' : finish_time
        }
    }
    query = { '_id': ObjectId(i_oid) }
    localdb[col].update_one( query, update_doc )
    updateSys(i_oid, col)
    updateVer(i_oid, col)
    write_log( '\t         Success.')

    return

def verifyTestRun(i_oid):
    write_log( '\t[Verify] TestRun : {}'.format(i_oid))

    query = { '_id': ObjectId(i_oid) }
    col = 'testRun'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return

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
        if not checkEmpty(this, key, keys[key]):
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### user
    query = { 
        '_id'      : ObjectId(thisRun['user_id']),
        'dbVersion': db_version
    }
    if not localdb.user.find_one(query):
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### site
    query = { 
        '_id'      : ObjectId(thisRun['address']),
        'dbVersion': db_version
    }
    if not localdb.institution.find_one(query):
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### componentTestRun
    query = { 
        'testRun'  : i_oid,
        'dbVersion': db_version
    }
    if localdb.componentTestRun.count_documents(query)==0:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### config
    for key in this:
        if 'Cfg' in key:
            query = { '_id': ObjectId(this[key]) }
            if not localdb.config.find_one(query):
                write_log( '\t         Failed.')
                disabled(i_oid, col)
                return
            thisCfg = localdb.config.find_one(query)
            if not is_json(localfs.get(ObjectId(thisCfg['data_id'])).read()):
                write_log( '\t         Failed.')
                disabled(i_oid, col)
                return
    ### environment
    if not this.get('environment', '...')=='...':
        query = { 
            'testRun'  : i_oid,
            'dbVersion': db_version
        }
        entries = localdb.componentTestRun.find(query)
        dcs = False
        for entry in entries:
            if not entry.get('environment', '...')=='...':
                dcs = True
        if dcs:
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return

    write_log( '\t         Success.')

def registerTestRun(i_oid, i_time, i_user_oid, i_site_oid):
    col = 'testRun'
    query = { '_id': ObjectId(i_oid) }
    this = yarrdb[col].find_one(query)
    start_time = i_time
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

    write_log( '\t[Register] testRun : {0} {1}'.format( this['runNumber'], this['testType'] ) )
    return str(oid)
 
def checkComponentTestRun(i_cmp_oid, i_tr_oid, i_num):
    col = 'componentTestRun'
    query = {
        'component': i_cmp_oid,
        'testRun'  : i_tr_oid,
        'dbVersion': db_version
    }
    this = localdb[col].find_one( query )
    if this:
        oid = str(this['_id'])
    else:
        oid = registerComponentTestRun(i_cmp_oid, i_tr_oid, i_num)

    return oid
    
def updateComponentTestRun(i_oid):
    write_log( '\t[Update] ComponentTestRun : {}'.format(i_oid))

    query = { '_id': ObjectId(i_oid) }
    col = 'componentTestRun'
    this = localdb[col].find_one(query)

    ### chip
    thisChip = None
    if not this.get('chip', 'module')=='module':
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
        chip_oid = this.get('chip',None)

    ### testRun
    query = { '_id': ObjectId(this['testRun']) }
    thisRun = localdb.testRun.find_one(query)

    if not thisRun or not chip_oid:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return

    if chip_oid=='module':
        name = thisCmp['serialNumber']
    else:
        query = { '_id': ObjectId(chip_oid) }
        thisChip = localdb.chip.find_one(query)
        name = thisChip['name']

    ### attachments
    entries = []
    for this_attachment in this.get('attachments', []):
        entries.append(this_attachment['code'])
    attachments = []
    for entry in entries:
        if updateAttachment(entry):
            attachments.append(this_attachment)

    ### config
    config_doc = {}
    for key in this:
        if 'Cfg' in key:
            config_doc.update({ key: this[key] })
    for key in config_doc:
        config_doc.update({ key: updateConfig(config_doc[key]) })

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
    updateSys(i_oid, col)
    updateVer(i_oid, col)
    write_log( '\t         Success.')

    return
 
def verifyComponentTestRun(i_oid):
    write_log( '\t[Verify] ComponentTestRun : {}'.format(i_oid))

    query = { '_id': ObjectId(i_oid) }
    col = 'componentTestRun'
    this = localdb[col].find_one(query)

    if this.get('update_failed', False):
        return

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
        if not checkEmpty(this, key, keys[key]):
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### Version
    if not this['dbVersion']==db_version:
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return

    ### component
    if not this.get('component', '...')=='...':
        query = {
            '_id'      : ObjectId(this['component']),
            'dbVersion': db_version
        }
        if not localdb.component.find_one(query):
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### chip
    if not this.get('chip', 'module')=='module':
        query = { 
            '_id'      : ObjectId(this['chip']),
            'dbVersion': db_version
        }
        if not localdb.chip.find_one(query):
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### testRun
    query = { 
        '_id'      : ObjectId(this['testRun']),
        'dbVersion': db_version
    }
    if not localdb.testRun.find_one(query):
        write_log( '\t         Failed.')
        disabled(i_oid, col)
        return
    ### attachments
    for entry in this.get('attachments', []):
        if entry['contentType']=='dat':
            if not is_dat(localfs.get(ObjectId(entry['code'])).read()):
                write_log( '\t         Failed.')
                disabled(i_oid, col)
                return
        elif entry['contentType']=='png':
            if not is_png(localfs.get(ObjectId(entry['code'])).read()):
                write_log( '\t         Failed.')
                disabled(i_oid, col)
                return
        else:
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return
    ### config
    for key in this:
        if 'Cfg' in key:
            query = { '_id': ObjectId(this[key]) }
            if not localdb.config.find_one(query):
                write_log( '\t         Failed.')
                disabled(i_oid, col)
                return
            thisCfg = localdb.config.find_one(query)
            if not is_json(localfs.get(ObjectId(thisCfg['data_id'])).read()):
                write_log( '\t         Failed.')
                disabled(i_oid, col)
                return
    ### environment
    if not this.get('environment','...')=='...':
        query = { '_id': ObjectId(this['environment']) }
        if not localdb.environment.find_one(query):
            write_log( '\t         Failed.')
            disabled(i_oid, col)
            return

    write_log( '\t         Success.')
 
def registerComponentTestRun(i_cmp_oid, i_tr_oid, i_num):
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
        'geomId'     : i_num
    }

    oid = localdb[col].insert_one(insert_doc).inserted_id
    updateSys(str(oid), col)
    updateVer(str(oid), col)

    write_log( '\t[Register] componentTestRun : {0} {1} {2}'.format( thisRun['runNumber'], thisRun['testType'], thisCmp['serialNumber'] ) )
    return str(oid)

def updateEnvironment(i_col, i_oid):
    write_log( '\t\t[Update] Environment : {}'.format(str(i_oid)))

    if i_oid=='...':
        return False

    if type(i_oid)==bool:
        return i_oid

    query = { '_id': ObjectId(i_oid) }
    col = 'environment'
    this_dcs = localdb[col].find_one(query)

    if not this_dcs:
        if i_col=='testRun':
            query = { 'environment': i_oid }
            run_entries = localdb.testRun.find(query,projection={'_id':1})
            for this_run in run_entries:
                addValue( 'testRun', str(this_run['_id']), 'environment', False )
                updateSys(str(this_run['_id']), 'testRun')
        elif i_col=='componentTestRun':
            query = { 'environment': i_oid }
            this_ctr = localdb.componentTestRun.find_one(query)
            if this_ctr:
                addValue( 'componentTestRun', str(this_ctr['_id']), 'environment', '...' )
                updateSys(str(this_ctr['_id']), 'componentTestRun')
        return False

    if i_col=='testRun':
        insert_doc = {}
        for key in this_dcs:
            if not key=='_id' and not key=='sys' and not key=='dbVersion':
                insert_doc.update({ key.lower().replace(' ','_'): this_dcs[key] })
        insert_doc.update({ 'sys': {} })
        query = { 'environment': i_oid }
        run_entries = localdb.testRun.find(query,projection={'_id':1})
        for this_run in run_entries:
            query = { 'testRun': str(this_run['_id']) }
            ctr_entries = localdb.componentTestRun.find(query,projection={'_id':1})
            env_docs = []
            for this_ctr in ctr_entries:
                insert_doc.pop('_id',None)
                env_oid = localdb[col].insert_one(insert_doc).inserted_id
                updateSys(str(env_oid), col)
                updateVer(str(env_oid), col)
                addValue( 'componentTestRun', str(this_ctr['_id']), 'environment', str(env_oid) )
                updateSys(str(this_ctr['_id']), 'componentTestRun')
            addValue( 'testRun', str(this_run['_id']), 'environment', True )
            updateSys(str(this_run['_id']), 'testRun')
        disabled(i_oid, col)

    write_log( '\t\t         Success.')
    return True
 
def registerEnvFromTr(i_oid):
    # testRun
    query = { '_id': ObjectId(i_oid) }
    new_thisRun = localdb.testRun.find_one(query)
    start_time = new_thisRun['startTime']
    finish_time = new_thisRun['finishTime']

    col = 'environment'
    query = {
        '$and': [
            { 'date': { '$gt': start_time - datetime.timedelta(minutes=1) }},
            { 'date': { '$lt': finish_time +  datetime.timedelta(minutes=1) }}
        ]
    }
    insert_doc = {}
    environment_entries = yarrdb[col].find( query )
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
        query = { 'testRun': i_oid }
        ctr_entries = localdb.componentTestRun.find(query)
        for this_ctr in ctr_entries:
            insert_doc.pop('_id',None)
            env_oid = localdb[col].insert_one(insert_doc).inserted_id
            updateSys(str(env_oid), col)
            updateVer(str(env_oid), col)
            addValue( 'componentTestRun', str(this_ctr['_id']), 'environment', str(env_oid) )
            updateSys(str(this_ctr['_id']), 'componentTestRun')
        write_log( '\t[Register] Environment' )
        return True
    else:
        return False

def registerEnvFromCtr(i_doc, date):
    col = 'environment'
    insert_doc = {}
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
    env_oid = localdb[col].insert_one(insert_doc).inserted_id
    updateVer(str(env_oid), col)
    updateSys(str(env_oid), col)

    write_log( '\t[Register] Environment' )
    return str(env_oid)

def registerConfigFromJson(config_oid):
    query = { '_id': ObjectId(config_oid) }
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
    config_oid = localdb.config.insert_one( config_doc ).inserted_id
    updateSys(str(config_oid), 'config')
    updateVer(str(config_oid), 'config')
    
    write_log( '\t[Register] Config : {0} {1}'.format( filename, title ))
    return str(config_oid)

def updateConfig(i_oid):
    write_log( '\t\t[Update] Config : {}'.format(i_oid))

    if i_oid=='...': return '...'

    ### config
    query = { '_id': ObjectId(i_oid) }
    this_config = localdb.config.find_one(query)
    if not this_config:
        return '...'

    ### fs.files
    query = { '_id': ObjectId(this_config['data_id']) }
    this_file = localdb.fs.files.find_one(query)

    ### fs.chunks
    query = { 'files_id': ObjectId(this_config['data_id']) }
    this_chunks = localdb.fs.chunks.count_documents(query)

    if not this_file or this_chunks==0:
        write_log( '\t         Failed.')
        return '...'

    updateVer(str(this_config['_id']), 'config')
    updateVer(str(this_file['_id']), 'fs.files')
    updateSys(str(this_file['_id']), 'fs.files')

    write_log( '\t\t         Success.')
    return str(this_config['_id'])

def registerConfig(attachment, chip_type, new_ctr):
    code = attachment['code']
    contentType = attachment['contentType']
    binary = yarrfs.get(ObjectId(code)).read()
    shaHashed = hashlib.sha256(binary).hexdigest()

    return_doc = {
        'chip_id': -1,
        'tx'     : -1,
        'rx'     : -1
    }

    try:
        json_data = json.loads(binary.decode('utf-8')) 
    except:
        return return_doc
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
    config_oid = localdb.config.insert_one(insert_doc).inserted_id
    ctr_query = { '_id': ObjectId(new_ctr['_id']) }
    localdb.componentTestRun.update_one( ctr_query, { '$set': { '{}Cfg'.format(contentType): str(config_oid) }}) 

    write_log( '\t[Register] Config : {0} {1}'.format( 'chipCfg.json', '{}Cfg'.format(contentType) ))
    return return_doc

def updateAttachment(i_oid):
    write_log( '\t\t[Update] Attachment : {}'.format(i_oid))

    ### fs.files
    query = { '_id': ObjectId(i_oid) }
    this_file = localdb.fs.files.find_one(query)

    ### fs.chunks
    query = { 'files_id': ObjectId(i_oid) }
    this_chunks = localdb.fs.chunks.count_documents(query)

    if not this_file or this_chunks==0:
        write_log( '\t         Failed.')
        return False

    updateVer(str(this_file['_id']), 'fs.files')
    updateSys(str(this_file['_id']), 'fs.files')

    write_log( '\t\t         Success.')
    return True 

def registerDatFromDat(attachment, new_ctr_oid):
    code = attachment['code']
    query = { '_id': ObjectId(code) }
    thisData = yarrdb.dat.find_one( query )
    if not thisData: return ''

    query = { '_id': ObjectId(new_ctr_oid) }
    new_ctr = localdb.componentTestRun.find_one( query )
    thisDat = thisData['data']
    update_doc = {
        'title'   : attachment['title'],
        'filename': attachment['filename'],
    }
    for new_attachment in new_ctr.get('attachments', []):
        if new_attachment['title']==update_doc['title'] and new_attachment['filename']==update_doc['filename']:
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
    ctr_query = { '_id': ObjectId(new_ctr['_id']) }
    localdb.componentTestRun.update_one( ctr_query, { '$push': { 'attachments': attachment }})

    write_log( '\t[Register] Dat : {0}'.format( thisData['filename'] ))
    return attachment['title']

def is_png(b):
    return bool(re.match(br"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", b[:8]))

def is_pdf(b):
    return bool(re.match(b"^%PDF", b[:4]))

def is_dat(b):
    return bool('Histo' in b.decode('utf-8').split('\n')[0][0:7])

def is_json(b):
    try:
        json_data = json.loads(b.decode('utf-8')) 
        return True
    except:
        return False

def registerDat(attachment, name, new_ctr_oid, plots):
    query = { '_id': ObjectId(new_ctr_oid) }
    new_ctr = localdb.componentTestRun.find_one( query )
    code = attachment['code']
    bin_data = yarrfs.get(ObjectId(code)).read()
    if (is_png(bin_data)): 
        return ''
    if (is_pdf(bin_data)): 
        return ''
    if not is_dat(bin_data): return ''

    filename = attachment['filename']
    if name in filename:       filename = filename.split(name)[1][1:].replace('_','-')
    elif 'chipId' in filename: filename = filename.split('chipId')[1][2:].replace('_','-')
    else:                      filename = filename[filename.rfind('_')+1:]

    update_doc = {
        'title': filename,
        'filename': '{0}.dat'.format(filename),
    }
    for new_attachment in new_ctr.get('attachments', []):
        if new_attachment['title'] == update_doc['title'] and new_attachment['filename'] == update_doc['filename']:
            return ''

    binary = yarrfs.get(ObjectId(code)).read()
    code = localfs.put( binary, filename='{0}.dat'.format(filename), dbVersion=db_version ) 
    updateSys(str(code), 'fs.files')

    ctr_query = { '_id': ObjectId(new_ctr['_id']) }
    localdb.componentTestRun.update_one( ctr_query, { 
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

    code = localfs.put( binary, filename='{0}.png'.format(filename), dbVersion=db_version ) 
    updateSys(str(code), 'fs.files')

    ctr_query = { '_id': ObjectId(new_ctr['_id']) }
    localdb.componentTestRun.update_one( ctr_query, { 
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

def addStage(stage, new_stage, new_tr_oid):
    if not stage == '' and new_stage == '...':
        query = { '_id': ObjectId(new_tr_oid) }
        update_doc = {
            '$set': {
                'stage': stage.lower().replace(' ','_')
            }
        }
        localdb.testRun.update_one(query, update_doc)

def addValue( i_col, i_oid, i_key, i_value ):
    query = { '_id': ObjectId(i_oid) }
    update_doc = { '$set': { i_key: i_value } }
    localdb[i_col].update_one( query, update_doc )

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

def checkEmpty(i_doc, i_key, i_type='str'):
    if not i_key in i_doc:
        return False
    if not i_doc[i_key]==type(i_type):
        return False
    return True

#################
# Update Function
# localdb(old ver) -> localdb(latest ver)
def update():
    start_update_time = ''
    finish_update_time = ''

    # update documents
    start_update_time = datetime.datetime.now() 
    print( '# Update database scheme: localdb' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
    write_log( '==============================================' )
    write_log( '[Update] database: localdb' )

    ### user
    write_log( '----------------------------------------------' )
    write_log( '[Start] User Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S User Collection' ))
    entries = localdb.user.find(projection={'_id':1})
    user_oids = []
    for entry in entries:
        user_oids.append(str(entry['_id']))
    for user_oid in user_oids:
        updateUser(user_oid) # check and update if old childParentRelation data
   
    ### site
    write_log( '----------------------------------------------' )
    write_log( '[Start] Institution Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Institution Collection' ))
    entries = localdb.institution.find(projection={'_id':1})
    site_oids = []
    for entry in entries:
        site_oids.append(str(entry['_id']))
    for site_oid in site_oids:
        updateSite(site_oid) # check and update if old childParentRelation data

    ### chip
    write_log( '----------------------------------------------' )
    write_log( '[Start] Chip Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Chip Collection' ))
    entries = localdb.chip.find(projection={'_id':1})
    chip_oids = []
    for entry in entries:
        chip_oids.append(str(entry['_id']))
    for chip_oid in chip_oids:
        updateChip(chip_oid) # check and update if old chip data

    ### component
    write_log( '----------------------------------------------' )
    write_log( '[Start] Component Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Component Collection' ))
    entries = localdb.component.find(projection={'_id':1})
    component_oids = []
    for entry in entries:
        component_oids.append(str(entry['_id']))
    for component_oid in component_oids:
        updateComponent(component_oid) # check and update if old component data

    ### childParentRelation
    write_log( '----------------------------------------------' )
    write_log( '[Start] ChildParentRelation Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S ChildParentRelation Collection' ))
    entries = localdb.childParentRelation.find(projection={'_id':1})
    cpr_oids = []
    for entry in entries:
        cpr_oids.append(str(entry['_id']))
    for cpr_oid in cpr_oids:
        updateChildParentRelation(cpr_oid) # check and update if old childParentRelation data

    ### componentTestRun
    write_log( '----------------------------------------------' )
    write_log( '[Start] ComponentTestRun Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S ComponentTestRun Collection' ))
    entries = localdb.componentTestRun.find(projection={'_id':1})
    ctr_oids = []
    for entry in entries:
        ctr_oids.append(str(entry['_id']))
    for ctr_oid in ctr_oids:
        updateComponentTestRun(ctr_oid) # check and update if old componentTestRun data

    ### testRun
    write_log( '----------------------------------------------' )
    write_log( '[Start] testRun Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S testRun Collection' ))
    entries = localdb.testRun.find(projection={'_id':1})
    tr_oids = []
    for entry in entries:
        tr_oids.append(str(entry['_id']))
    for tr_oid in tr_oids:
        updateTestRun(tr_oid) # check and update if old testRun data

    ### Confirmation
    cols = localdb.list_collection_names()
    for col in cols:
        query = { 'update_failed': True }
        entries = localdb[col].find(query, projection={'_id':1})
        for entry in entries:
            if entry['dbVersion']==db_version: 
                print('WARNING: {}'.format(entry['_id'])
                addValue( col, str(entry['_id']), 'dbVersion', -1 )
        print('Collection: {0} ... disabled: {1}'.format(col, localdb[col].count_documents(query)))

    finish_update_time = datetime.datetime.now() 
    write_log( '==============================================' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
    print( '\t# Succeeded in update.' )
    print( ' ' )
        
    write_log( '====        Operation Time        ====' )
    total_update_time = datetime.timedelta(seconds=(finish_update_time-start_update_time).total_seconds())
    write_log( 'Update total time:  ' + str(total_update_time) )
    write_log( start_update_time.strftime( '\tStart: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( finish_update_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( '======================================' )
    
    print( start_update_time.strftime( '# Start time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( finish_update_time.strftime( '# Finish time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( '# Total time: ' + str(total_update_time) + ' [s]' ) 
    print( ' ' )

##################
# Convert Function
# yarrdb(old ver) -> localdb(latest ver)
def convert():
    start_convert_time = ''
    finish_convert_time = ''

    # convert database structure
    start_convert_time = datetime.datetime.now() 
    print( '# Convert database scheme: yarrdb -> localdb' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
    write_log( '==============================================' )
    write_log( '[Convert] database: yarrdb' )

    ### module
    query = { 'componentType' : 'Module' }
    entries = yarrdb.component.find(query,projection={'_id':1})
    mo_oids = []
    for entry in entries: # module entry
        mo_oids.append( str(entry['_id']) )
    for mo_oid in mo_oids:
        query = { '_id': ObjectId(mo_oid) }
        thisModule = yarrdb.component.find_one(query)

        mo_serial_number = thisModule['serialNumber']
        write_log( '----------------------------------------------' )
        write_log( '[Start] Module: {}'.format(mo_serial_number) )
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Module: {}'.format(mo_serial_number)) )

        new_mo_oid = checkComponent(mo_oid, 'module') # check and insert if not exist component data

        ### chips
        query = { 'parent': mo_oid }
        entries = yarrdb.childParentRelation.find(query,projection={'child':1})
        ch_oids = {}
        for entry in entries:
            ch_oids.update({ entry['child']: '...' })
        ctr_query = { '$or': [] }
        chip_oids = []
        for ch_oid in ch_oids:
            new_ch_oid = checkComponent(ch_oid) # check and insert if not exist component data
            checkChildParentRelation(new_ch_oid, new_mo_oid)
            ctr_query['$or'].append({ 'component': ch_oid })
            chip_oids.append({
                'old': ch_oid,
                'new': new_ch_oid 
            })
        entries = yarrdb.componentTestRun.find(ctr_query,projection={'testRun':1})
        tr_oids = []
        for entry in entries:
            tr_oids.append(entry['testRun'])
        new_tr_oids = {}
        for tr_oid in tr_oids:
            new_tr_oid = checkTestRun(tr_oid)
            if not new_tr_oid in new_tr_oids:
                new_tr_oids.update({ new_tr_oid: [] })
            new_tr_oids[new_tr_oid].append({ 'testRun': tr_oid })
        for new_tr_oid in new_tr_oids:
            plots = []
            new_tr_query = { '_id': ObjectId(new_tr_oid) }
            new_thisRun = localdb.testRun.find_one( new_tr_query )
            write_log( '        runNumber: {}'.format( new_thisRun['runNumber'] ) )

            # for module
            new_ctr_oid = checkComponentTestRun(new_mo_oid, new_tr_oid, 'module')
            new_ctr_query = { '_id': ObjectId(new_ctr_oid) }
            new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
            query = { 
                'component': mo_oid,
                '$or': new_tr_oids[new_tr_oid]
            }
            thisComponentTestRun = yarrdb.componentTestRun.find_one(query)
            if thisComponentTestRun:
                query = { '_id': ObjectId(thisComponentTestRun['testRun']) }
                thisRun = yarrdb.testRun.find_one( query )
                attachments = thisRun.get('attachments',[])
                for attachment in attachments: 
                    title = registerPng(attachment, mo_serial_number, new_thisComponentTestRun, plots)
                    if not title == '':
                        plots.append(title)
            for i, ch_oid in enumerate(chip_oids):
                new_ctr_oid = checkComponentTestRun(ch_oid['new'], new_tr_oid, i)
                new_ctr_query = { '_id': ObjectId(new_ctr_oid) }
                new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )

                new_ch_query = { '_id': ObjectId(ch_oid['new']) }
                new_thisChip = localdb.component.find_one( new_ch_query )
                chip_type = new_thisChip['chipType']
                if chip_type == "FEI4B": chip_type = "FE-I4B"

                query = { '_id': ObjectId(ch_oid['old']) }
                thisChip = yarrdb.component.find_one( query )
                chip_name = thisChip.get('name', 'UnnamedChip_{}'.format(i))
                query = { 
                    'component': ch_oid['old'],
                    '$or': new_tr_oids[new_tr_oid]
                }
                thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
                if thisComponentTestRun:
                    query = { '_id': ObjectId(thisComponentTestRun['testRun']) }
                    thisRun = yarrdb.testRun.find_one( query )
                    # stage
                    addStage(thisComponentTestRun.get('stage',''), new_thisRun['stage'], new_tr_oid)
                    addStage(thisRun.get('stage',''), new_thisRun['stage'], new_tr_oid)
                    # chiptype
                    if new_thisRun['chipType']=='...':
                        localdb.testRun.update_one(
                            new_tr_query,
                            {'$set': {'chipType': chip_type }}
                        )
                        new_thisRun = localdb.testRun.find_one( new_tr_query )
                    # environment
                    if not thisComponentTestRun.get('environments',[])==[]:
                        env_oid = registerEnvFromCtr(thisComponentTestRun, new_thisRun['startTime'])
                        localdb.componentTestRun.update_one(
                            new_ctr_query,
                            {'$set': {'environment': env_oid}}   
                        )
                        new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
                        localdb.testRun.update_one(
                            new_tr_query,
                            {'$set': {'environment': True}}   
                        )
                        new_thisRun = localdb.testRun.find_one( new_tr_query )
                    elif new_thisRun['environment']==False:
                        dcs = registerEnvFromTr(new_tr_oid)
                        localdb.testRun.update_one(
                            new_tr_query,
                            {'$set': {'environment': dcs}}   
                        )
                        new_thisRun = localdb.testRun.find_one( new_tr_query )
                    # controller config
                    if 'ctrlCfg' in thisRun and new_thisRun.get('ctrlCfg','...')=='...':
                        ctrl_oid = registerConfigFromJson(thisRun['ctrlCfg'])
                        localdb.testRun.update_one(
                            new_tr_query,
                            {'$set': {'ctrlCfg': ctrl_oid}}
                        )
                        new_thisRun = localdb.testRun.find_one( new_tr_query )
                    # scan config
                    if 'scanCfg' in thisRun and new_thisRun.get('scanCfg','...')=='...':
                        scan_oid = registerConfigFromJson(thisRun['scanCfg'])
                        localdb.testRun.update_one(
                            new_tr_query,
                            {'$set': {'scanCfg': scan_oid}}
                        )
                        new_thisRun = localdb.testRun.find_one( new_tr_query )

                    if not thisComponentTestRun.get('beforeCfg', '...')=='...' and new_thisComponentTestRun.get('beforeCfg','...')=='...':
                        config_oid = registerConfigFromJson(thisComponentTestRun['beforeCfg'])
                        localdb.componentTestRun.update_one(
                            new_ctr_query,
                            {'$set': {'beforeCfg': config_oid}}
                        )
                        new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
                    if not thisComponentTestRun.get('afterCfg', '...')=='...' and new_thisComponentTestRun.get('afterCfg','...')=='...':
                        config_oid = registerConfigFromJson(thisComponentTestRun['afterCfg'])
                        localdb.componentTestRun.update_one(
                            new_ctr_query,
                            {'$set': {'afterCfg': config_oid}}
                        )
                        new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )

                    ### attachments
                    attachments = thisComponentTestRun.get('attachments',[])
                    for attachment in attachments: 
                        title = registerDatFromDat(attachment, new_ctr_oid)
                        if not title == '':
                            plots.append(title)
                    attachments = thisRun.get('attachments',[])
                    for attachment in attachments: 
                        title = registerDat(attachment, chip_name, new_ctr_oid, plots)
                        if not title == '':
                            plots.append(title)
                        if attachment['contentType']=='after' and new_thisComponentTestRun.get('afterCfg','...')=='...': 
                            return_doc = registerConfig(attachment, chip_type, new_thisComponentTestRun)
                            if not return_doc['chip_id']==-1 and new_thisChip['chipId']==-1:
                                localdb.component.update_one(
                                    new_ch_query,
                                    {'$set': { 'chipId': return_doc['chip_id'] }}
                                )
                                new_thisChip = localdb.component.find_one( new_ch_query )
                                query = { 'parent': new_mo_oid, 'child': ch_oid['new'] }
                                localdb.childParentRelation.update_one(
                                    query,
                                    {'$set': { 'chipId': return_doc['chip_id'] }}
                                )
                            if new_thisComponentTestRun['tx']==-1 and not return_doc['tx']==-1:
                                localdb.componentTestRun.update_one(
                                    new_ctr_query,
                                    {'$set': { 'tx': return_doc['tx'], 'rx': return_doc['rx'] }}
                                )
                                new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
                        if attachment['contentType']=='before' and new_thisComponentTestRun.get('beforeCfg','...')=='...': 
                            return_doc = registerConfig(attachment, chip_type, new_thisComponentTestRun)
                            if not return_doc['chip_id']==-1 and new_thisChip['chipId']==-1:
                                localdb.component.update_one(
                                    new_ch_query,
                                    {'$set': { 'chipId': return_doc['chip_id'] }}
                                )
                                new_thisChip = localdb.component.find_one( new_ch_query )
                                query = { 'parent': new_mo_oid, 'child': ch_oid['new'] }
                                localdb.childParentRelation.update_one(
                                    query,
                                    {'$set': { 'chipId': return_doc['chip_id'] }}
                                )
                            if new_thisComponentTestRun['tx']==-1 and not return_doc['tx']==-1:
                                localdb.componentTestRun.update_one(
                                    new_ctr_query,
                                    {'$set': { 'tx': return_doc['tx'], 'rx': return_doc['rx'] }}
                                )
                                new_thisComponentTestRun = localdb.componentTestRun.find_one( new_ctr_query )
                if new_thisChip['chipId'] == -1:
                    localdb.component.update_one(
                        new_ch_query,
                        {'$set': { 'chipId': 0 }}
                    )
                chip_oid = checkChip(ch_oid['new'])
                localdb.componentTestRun.update_one(
                    new_ctr_query,
                    {'$set': { 'chip': chip_oid }}
                )
            if new_thisRun.get('plots',[])==[]:
                for plot in list(set(plots)):
                    localdb.testRun.update_one(
                        new_tr_query,
                        {'$push': {'plots': plot}}
                    )

    finish_convert_time = datetime.datetime.now() 
    write_log( '==============================================' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
    print( '\t# Succeeded in conversion.' )
    print( ' ' )
        
    write_log( '====        Operation Time        ====' )
    total_convert_time = datetime.timedelta(seconds=(finish_convert_time-start_convert_time).total_seconds())
    write_log( 'Convert total time:  ' + str(total_convert_time) )
    write_log( start_convert_time.strftime( '\tStart: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( finish_convert_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( '======================================' )
    
    print( start_convert_time.strftime( '# Start time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( finish_convert_time.strftime( '# Finish time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( '# Total time: ' + str(total_convert_time) + ' [s]' ) 
    print( ' ' )

def verify():
    start_verify_time = ''
    finish_verify_time = ''

    # verigy database structure
    start_verify_time = datetime.datetime.now() 
    print( '# Verify database scheme: yarrdb -> localdb' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
    write_log( '==============================================' )
    write_log( '[Verify] database: yarrdb' )

    ### user
    write_log( '----------------------------------------------' )
    write_log( '[Start] User Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S User Collection' ))
    entries = localdb.user.find(projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        verifyUser(oid) # check and update if old childParentRelation data
   
    ### site
    write_log( '----------------------------------------------' )
    write_log( '[Start] Institution Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Institution Collection' ))
    entries = localdb.institution.find(projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        verifySite(oid) # check and update if old childParentRelation data

    ### chip
    write_log( '----------------------------------------------' )
    write_log( '[Start] Chip Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Chip Collection' ))
    entries = localdb.chip.find(projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        verifyChip(oid) # check and update if old chip data

    ### component
    write_log( '----------------------------------------------' )
    write_log( '[Start] Component Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Component Collection' ))
    entries = localdb.component.find(projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        verifyComponent(oid) # check and update if old component data

    ### childParentRelation
    write_log( '----------------------------------------------' )
    write_log( '[Start] ChildParentRelation Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S ChildParentRelation Collection' ))
    entries = localdb.childParentRelation.find(projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        verifyChildParentRelation(oid) # check and update if old childParentRelation data

    ### componentTestRun
    write_log( '----------------------------------------------' )
    write_log( '[Start] ComponentTestRun Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S ComponentTestRun Collection' ))
    entries = localdb.componentTestRun.find(projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        verifyComponentTestRun(oid) # check and update if old componentTestRun data

    ### testRun
    write_log( '----------------------------------------------' )
    write_log( '[Start] testRun Collection' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S testRun Collection' ))
    entries = localdb.testRun.find(projection={'_id':1})
    oids = []
    for entry in entries:
        oids.append(str(entry['_id']))
    for oid in oids:
        verifyTestRun(oid) # check and update if old testRun data

    ### Confirmation
    cols = localdb.list_collection_names()
    for col in cols:
        query = { 'update_failed': True }
        entries = localdb[col].find(query, projection={'_id':1})
        for entry in entries:
            if entry['dbVersion']==db_version: 
                print('WARNING: {}'.format(entry['_id'])
                addValue( col, str(entry['_id']), 'dbVersion', -1 )
        print('Collection: {0} ... disabled: {1}'.format(col, localdb[col].count_documents(query)))

    cols = localdb.list_collection_names()
    for col in cols:
        query = { 'dbVersion': {'$ne': db_version} }
        print('Collection: {0} ... not match version: {1}'.format(col, localdb[col].count_documents(query)))

    finish_verify_time = datetime.datetime.now() 
    write_log( '==============================================' )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
    print( '\t# Succeeded in verification.' )
    print( ' ' )
        
    write_log( '====        Operation Time        ====' )
    total_verify_time = datetime.timedelta(seconds=(finish_verify_time-start_verify_time).total_seconds())
    write_log( 'Verify total time:  ' + str(total_verify_time) )
    write_log( start_verify_time.strftime( '\tStart: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( finish_verify_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f' ) )
    write_log( '======================================' )
    
    print( start_verify_time.strftime( '# Start time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( finish_verify_time.strftime( '# Finish time: %Y-%m-%dT%H:%M:%S' ) ) 
    print( '# Total time: ' + str(total_verify_time) + ' [s]' ) 
    print( ' ' )


def main():
    #start_time = datetime.datetime.now() 
    #write_log( '[Start] convertDB.py' )

    #client.drop_database('localdb')
    #client.admin.command(
    #    'copydb',
    #    fromdb='localdb_replica',
    #    todb='localdb'
    #)
    #update()
    #convert()
    verify()

    #finish_time = datetime.datetime.now() 
    #write_log( '==============================================' )
    #print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
    #print( '\t# Succeeded in all.' )
    #print( ' ' )
    #    
    #write_log( '====        Operation Time        ====' )
    #total_time = datetime.timedelta(seconds=(finish_time-start_time).total_seconds())
    #write_log( 'Total time:  ' + str(total_time) )
    #write_log( start_time.strftime( '\tStart: %Y-%m-%dT%H:%M:%S:%f' ) )
    #write_log( finish_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f' ) )
    #write_log( '======================================' )
    #write_log( '[Finish] convertDB.py' )
    #
    #print( start_time.strftime( '# Start time: %Y-%m-%dT%H:%M:%S' ) ) 
    #print( finish_time.strftime( '# Finish time: %Y-%m-%dT%H:%M:%S' ) ) 
    #print( '# Total time: ' + str(total_time) + ' [s]' ) 
    #print( ' ' )

    log_file.close()

if __name__ == '__main__': main()
