"""
script for conversion databaase scheme
log file ---> log/loConvert_%m%d_%H%M.txt
"""

### Import 
import os, sys, datetime, json, re, time, hashlib
import gridfs # gridfs system 
from   pymongo       import MongoClient # use mongodb scheme
from   bson.objectid import ObjectId    # handle bson format
sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) )
sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) + '/src' )
from   arguments import *   # Pass command line arguments into app.py

### Set database
args = getArgs()         
if args.username : url = 'mongodb://' + args.username + ':' + args.password + '@' + args.host + ':' + str(args.port) 
else :             url = 'mongodb://'                                             + args.host + ':' + str(args.port) 
client = MongoClient( url )
yarrdb = client[args.db]
fs = gridfs.GridFS( yarrdb )
dbv = args.version

### Set log file
log_dir = './log'
if not os.path.isdir(log_dir): 
    os.mkdir(log_dir)
now = datetime.datetime.now() 
log_filename = now.strftime('{}/logConvert_%m%d_%H%M.txt'.format(log_dir))
log_file = open( log_filename, 'w' )

### Set database.json 
home = os.environ['HOME']
filepath = '{}/.yarr/database.json'.format(home)
with open(filepath, 'r') as f: file_json = json.load(f)
file_stages = file_json.get('stage', [])
file_dcs = file_json.get('environment', [])
if file_stages == [] or file_dcs == []:
    print( 'There is no database config: {}'.format(filepath) )
    print( 'Prepare the config file by running dbLogin.sh in YARR SW' )
    sys.exit()

#################################################################
#################################################################

### Function 
def input_v( message ) :
    answer = ''
    if args.fpython == 2 : answer = raw_input( message ) 
    if args.fpython == 3 : answer =     input( message )
    return answer

def input_answer( message ):
    answer = ''
    while not answer == 'y' and not answer == 'n':
        answer = input_v( message )
    print( ' ' )
    return answer

def update_mod(collection, query):
    yarrdb[collection].update(query, 
        { 
            '$set': { 
                'sys.rev'  : int(yarrdb[collection].find_one(query)['sys']['rev']+1), 
                'sys.mts'  : datetime.datetime.utcnow() 
            }
        }, 
        multi=True
    ) 

def update_ver(collection, query, ver): 
    yarrdb[collection].update( query, { '$set': { 'dbVersion': ver }}, multi=True ) 

def is_png(b):
    return bool(re.match(br"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", b[:8]))

def is_pdf(b):
    return bool(re.match(b"^%PDF", b[:4]))

def set_institution(address, user_id): 
    query = { '_id': ObjectId(user_id) }
    thisUser = yarrdb.user.find_one( query )
    inst_doc = { 'institution': 'null', 'address': address, 'name': thisUser['userName'] }
    if not yarrdb.institution.find_one( inst_doc ):
        time_now = datetime.datetime.utcnow()
        inst_doc.update({ 
            'sys': {
                'rev': 0,
                'cts': time_now,
                'mts': time_now },
            'dbVersion': dbv
        })                       
        yarrdb.institution.insert( inst_doc ) 
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t [Insert] institution doc: {}\n'.format(address) ) )

def set_user(doc): 
    if 'user_id' in doc:
        query = { '_id': ObjectId(doc['user_id']) }
        user = yarrdb.user.find_one( query )
        return user

    if 'userIdentity' in doc:
        name = doc['userIdentity']
        institution = doc.get('institution', 'Unknown')
    else:
        name = 'Unknown'
        institution = 'Unknown'
    user_doc = { 
        'userName'    : name,
        'institution' : institution,
        'userIdentity': 'default',
        'userType'    : 'readWrite'
    }
    user = yarrdb.user.find_one( user_doc )
    if user: return user

    time_now = datetime.datetime.utcnow()
    user_doc.update({ 
        'sys': {
            'rev': 0,
            'cts': time_now,
            'mts': time_now },
        'dbVersion': dbv
    })
    user_id = yarrdb.user.insert( user_doc )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t [Insert] user doc: {}\n'.format(name) ) )
    set_institution(institution, user_id)

    query = { '_id': user_id }
    user = yarrdb.user.find_one( query )
    return user

def set_env(thisCtr, tr_id): 
    if not 'environments' in thisCtr: return
    tr_query = { '_id': ObjectId(tr_id) }
    thisRun = yarrdb.testRun.find_one( tr_query )
    if 'environment' in thisRun: return
    date = thisRun['startTime']
    address = thisRun['address']
    time_now = datetime.datetime.utcnow()
    env_doc = { 
        'sys': {
            'rev': 0,
            'cts': time_now,
            'mts': time_now },
        'type': 'data' 
    }
    for env in thisCtr['environments']:
        key = env['key']
        description = env.get('description', 'null') 
        value = env['value']
        if not key in file_dcs: log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[WARNING] Undefined environmental key: {}\n'.format(key) ) )
        if description == 'null': log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[WARNING] The description is not written: {}\n'.format(key) ) )
        if not key in env_doc: env_doc.update({ key: [] })
        env_doc[key].append({
            'data': [
                { 
                    'date' : date,
                    'value': value 
                }
            ],
            'description': description 
        })
    env_id = yarrdb.environment.insert( env_doc ) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Insert] environment doc\n' ) )
    query = { '_id': env_id }
    update_ver( 'environment', query, dbv ) 
    yarrdb.testRun.update( tr_query, { '$set': { 'environment': str(env_id) }}) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] testRun doc: {}\n'.format(thisRun['runNumber']) ) )

def update_testrun(ctr, user, plots):
    tr_query = { '_id': ObjectId(ctr['testRun']) }
    thisRun = yarrdb.testRun.find_one( tr_query )
    doc = { 
        'testType' : thisRun['testType'],
        'runNumber': thisRun['runNumber'],
        'address'  : user['institution'],
        'user_id'  : str(user['_id']),
        'dbVersion': dbv 
    } 
    thisTestRun = yarrdb.testRun.find_one( doc )
    if not thisTestRun:
        stage = ctr.get('stage', 'null')
        if not stage in file_stages: log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[WARNING] Undefined this stage: {}\n'.format(stage) ) )
        date = thisRun['date']
        time_now = datetime.datetime.utcnow()
        doc.update({ 
            'sys': {
                'rev': 0,
                'cts': time_now,
                'mts': time_now },
            'startTime'   : date,
            'passed'      : True,
            'state'       : 'ready',
            'targetCharge': -1,
            'targetTot'   : -1,
            'comments'    : [],
            'defects'     : [],
            'stage'       : stage,
            'finishTime'  : date,
            'plots'       : plots,
            'display'     : thisRun.get('display',False),
            'dbVersion'   : dbv 
        })  
        tr_id = yarrdb.testRun.insert( doc ) 
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] testRun doc: {0}\n'.format(thisRun['runNumber']) ) )
    else:
        tr_id = thisTestRun['_id']
        if len(plots) > thisTestRun['plots']:
            query = { '_id': tr_id }
            yarrdb.testRun.update( query, { '$set': { 'plots': plots }} )
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] testRun doc: {0}\n'.format(thisRun['runNumber']) ) )
        if thisRun.get('display', False) and not thisTestRun['display']:
            yarrdb.testRun.update( query, { '$set': { 'display': thisRun['display'] }} ) 
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] testRun doc: {0}\n'.format(thisRun['runNumber']) ) )
    if not thisRun.get('dbVersion','') == dbv:
        yarrdb.testRun.remove( tr_query ) #REMOVE
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Remove] testRun doc: {0}\n'.format(thisRun['runNumber']) ) )

    return tr_id

def for_json(attachment, chipType, ctr_query):
    code = attachment['code']
    contentType = attachment['contentType']
    binary = fs.get(ObjectId(code)).read()
    shaHashed = hashlib.sha256(binary).hexdigest()
    json_data = json.loads(binary) 
    doc = yarrdb.fs.files.find_one({ 'dbVersion': dbv, 'hash': shaHashed })
    if doc:
        fs.delete( ObjectId(code) )
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t\t\t[Delete] grid doc: chipCfg.json\n' ) )
        code = str(doc['_id'])
    else:
        fs.delete( ObjectId(code) )
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t\t\t[Delete] grid doc: chipCfg.json\n' ) )
        code = fs.put( binary, filename='chipCfg.json', hash=shaHashed, dbVersion=dbv )   # Update
        query = { 'files_id': code }
        update_ver( 'fs.chunks', query, dbv )
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t\t\t[Insert] grid doc: chipCfg.json\n' ) )

    chipId = ''
    if chipType in json_data:
        if chipType == 'FE-I4B':
            chipId = json_data[chipType]['Parameter']['chipId']
        elif chipType == 'RD53A':
            chipId = json_data[chipType]['Parameter']['ChipId']
    time_now = datetime.datetime.utcnow()
    config_id = yarrdb.config.insert({
        'sys'      : {
            'rev': 0,
            'cts': time_now,
            'mts': time_now 
        },
        'filename' : 'chipCfg.json',
        'chipType' : chipType,
        'title'    : 'chipCfg',
        'format'   : 'fs.files',
        'data_id'  : code, 
        'dbVersion': dbv
    })
    yarrdb.componentTestRun.update( ctr_query, { '$set': { '{}Cfg'.format(contentType): str(config_id) }}) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t\t\t[Update] grid doc: chipCfg.json\n' ) )

    return chipId

def for_data(attachment, name, plots, ctr_query, contentType):
    code = attachment['code']
    filename = attachment['filename']
    if name in filename:       filename = filename.split(name)[1][1:].replace('_','-')
    elif 'chipId' in filename: filename = filename.split('chipId')[1][2:].replace('_','-')
    else:                      filename = filename[filename.rfind('_')+1:]
    for plot in plots:
        if plot in attachment['filename']: filename = plot

    binary = fs.get(ObjectId(code)).read()
    fs.delete( ObjectId(code) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t\t\t[Delete] grid doc: {0}.{1}\n'.format(filename, contentType) ) )
    code = fs.put( binary, filename='{0}.{1}'.format(filename, contentType), dbVersion=dbv )   # Update
    yarrdb.componentTestRun.update( ctr_query, { 
        '$push': { 
            'attachments': { 
                'code'       : code,
                'dateTime'   : attachment['dateTime'],
                'title'      : filename, 
                'description': 'describe',
                'contentType': contentType,
                'filename'   : '{0}.{1}'.format(filename, contentType) 
            }
        }
    })
    query = { 'files_id': ObjectId(code) }
    update_ver( 'fs.chunks', query, dbv )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t\t\t[Update] grid doc: {0}.{1}\n'.format(filename, contentType) ) )

    return filename

def for_broken(attachment, ctr_query):
    code = attachment['code']
    yarrdb.componentTestRun.update( ctr_query, { 
        '$push': { 
            'broken' : { 
                'key'        : attachment['filename'],
                'dateTime'   : attachment['dateTime'],
                'code'       : code,
                'contentType': attachment['contentType'] 
            }
        }
    }) 
    query = { '_id': ObjectId(code) }
    update_ver( 'fs.files', query, -1 )
    query = { 'files_id': ObjectId(code) }
    update_ver( 'fs.chunks', query, -1 )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t\t\t[Broken] grid doc: {0}.{1}\n'.format(attachment['filename'], attachment['contentType']) ) )
    
    return True

#################################################################
#################################################################

### Main function
start_time = datetime.datetime.now() 
start_update_time = ''
finish_update_time = ''
log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start] convertDB.py\n' ))

### convert database scheme
print( '# Conversion flow' )
print( '\t1. Replicate : python copyDB.py    : {0}      ---> {1}_copy'.format( args.db, args.db ) )
print( '\t2. Convert   : python convertDB.py : {0}(old) ---> {1}(new)'.format( args.db, args.db ) )
print( '\t3. Confirm   : python confirmDB.py : {0}(new) ---> {1}(confirmed)'.format( args.db, args.db ) )
print( ' ' )
print( '# This is the stage of step2. Convert' )
print( '# It is recommended to run "copyDB.py" first.' )
print( ' ' )
answer = input_answer( '# Do you convert db scheme? (y/n) > ' )
if answer == 'y' :
    # modify module document
    print( '# Convert database scheme: {}'.format(args.db) )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ==============================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Convert] database: {}\n'.format(args.db) ) )
    
    start_update_time = datetime.datetime.now() 
    query = { 
        'componentType' : 'Module',
        'dbVersion'     : { '$ne': dbv } 
    }
    module_entries = yarrdb.component.find( query )
    moduleid_entries = []
    for module in module_entries:
        moduleid_entries.append( str(module['_id']) )
    for moduleid in moduleid_entries:
        query = { '_id': ObjectId(moduleid) }
        module = yarrdb.component.find_one( query )
    
        mo_serialNumber = module['serialNumber']
        mo_query = { '_id': module['_id'] }
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Module: {}'.format(mo_serialNumber)) )
    
        ### convert module - testRun (if registered)
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ----------------------------------------------\n' ) )
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start] Module: {}\n'.format( module['serialNumber'] ) ) )
    
        query = { 'component': str(module['_id']),
                  'dbVersion': { '$ne': dbv } }
        run_entries = yarrdb.componentTestRun.find( query )
        runid_entries = []
        for run in run_entries:
            runid_entries.append( str(run['_id']) )
        for runid in runid_entries:
            ctr_query = { '_id': ObjectId(runid) }
            thisCtr = yarrdb.componentTestRun.find_one( query )
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tComponentTestRun: #{}\n'.format( thisCtr['runNumber'] ) ) )
            tr_query = { '_id': ObjectId(thisCtr['testRun']) }
            thisRun = yarrdb.testRun.find_one( tr_query )
            user = set_user( thisRun ) 
    
            ### attachments
            attachments = thisRun.get('attachments',[])
            plots = []
            maybe_broken = False
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\tAttachments:\n' ) )
            for attachment in attachments:
                code = attachment.get('code')
                bin_data =  fs.get( ObjectId(code) ).read()
                if is_png( bin_data ):
                    try:
                        data_name = for_data( attachment, mo_serialNumber, plots, ctr_query, 'png' )
                        plots.append( data_name )
                    except:
                        maybe_broken = for_broken( attachment, ctr_query )
                elif is_pdf( bin_data ):
                    try:
                        data_name = for_data( attachment, mo_serialNumber, plots, ctr_query, 'pdf' )
                        plots.append( data_name )
                    except:
                        maybe_broken = for_broken( attachment, ctr_query ) 
                elif 'Histo' in bin_data.split('\n')[0][0:7]:
                    try:
                        data_name = for_data( attachment, mo_serialNumber, plots, ctr_query, 'dat' )
                        plots.append( data_name )
                    except:
                        maybe_broken = for_broken( attachment, ctr_query ) 
                else:
                    try:
                        json_data = json.loads( bin_data )
                        for_json( attachment, chipType, ctr_query ) 
                    except:
                        maybe_broken = for_broken( attachment, ctr_query ) 
    
            plots = list(set(plots))
    
            ### testRun
            tr_id = update_testrun( thisCtr, user, plots ) 
    
            ### environment
            set_env( thisCtr, str(tr_id) ) 
    
            yarrdb.componentTestRun.update( ctr_query,
                                            { '$set': { 'tx'       : -1,
                                                        'rx'       : -1,
                                                        'testRun'  : str(tr_id) }}) 
            yarrdb.componentTestRun.update( ctr_query,
                                            { '$unset': { 'stage': '',
                                                          'environments': '' }} ) 
            update_ver( 'componentTestRun', ctr_query, dbv ) 
            update_mod( 'componentTestRun', ctr_query ) 
    
            if (maybe_broken):
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t\t\t[Broken] change db version -> -1\n' ) )
                update_ver( 'componentTestRun', ctr_query, -1 ) 
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] componentTestRun doc: {0} - {1}\n'.format(mo_serialNumber, thisRun['runNumber']) ) )
    
        # modify chip documents
        query = { 'parent': str(module['_id']) }
        child_entries = yarrdb.childParentRelation.find( query )
        childid_entries = []
        for child in child_entries:
            childid_entries.append( str(child['_id']) )
        chip_num = len(childid_entries)
        for childid in childid_entries:
            query = { '_id': ObjectId(childid) }
            child = yarrdb.childParentRelation.find_one( query )
            ch_query = { '_id': ObjectId(child['child']) }
            chip = yarrdb.component.find_one( ch_query )
            ### convert chip - testRun (if registered)
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Chip: {}\n'.format( chip['serialNumber'] ) ) )
    
            chipType = chip['componentType']
            chipName = chip['name']
            chipId = ''
            multiparent = False
    
            ### componentTestRun (chip)
            query = { 'component': str(chip['_id']),
                      'dbVersion': { '$ne': dbv } }
            run_entries = yarrdb.componentTestRun.find( query )
            if not run_entries.count() == 0:
                runid_entries = []
                for run in run_entries:
                    runid_entries.append( str(run['_id']) )
                for runid in runid_entries:
                    query = { '_id': ObjectId(runid) }
                    thisCtr = yarrdb.componentTestRun.find_one( query )
                    ctr_query = { '_id': thisCtr['_id'] }
                    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tComponentTestRun: {0}-{1}\n'.format( chip['serialNumber'], thisCtr['runNumber'] ) ) )
                    tr_query = { '_id': ObjectId(thisCtr['testRun']) }
                    thisRun = yarrdb.testRun.find_one( tr_query )
                    user = set_user( thisRun ) #user
    
                    ### attachments
                    attachments = thisRun.get('attachments',[])
                    plots = []
                    maybe_broken = False
                    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\tAttachments:\n' ) )
                    for attachment in attachments:
                        code = attachment.get('code')
                        bin_data =  fs.get( ObjectId(code) ).read()
                        if is_png( bin_data ):
                            try:
                                data_name = for_data( attachment, chipName, plots, ctr_query, 'png' ) 
                                plots.append( data_name )
                            except:
                                maybe_broken = for_broken( attachment, ctr_query )
                        elif is_pdf( bin_data ):
                            try:
                                data_name = for_data( attachment, chipName, plots, ctr_query, 'pdf' ) 
                                plots.append( data_name )
                            except:
                                maybe_broken = for_broken( attachment, ctr_query ) 
                        elif 'Histo' in bin_data.split('\n')[0][0:7]:
                            try:
                                data_name = for_data( attachment, chipName, plots, ctr_query, 'dat' ) 
                                plots.append( data_name )
                            except:
                                maybe_broken = for_broken( attachment, ctr_query ) 
                        else:
                            try:
                                json_data = json.loads( bin_data )
                                chipId = for_json( attachment, chipType, ctr_query ) 
                            except:
                                maybe_broken = for_broken( attachment, ctr_query ) 
    
                    plots = list(set(plots))
    
                    ### testRun
                    tr_id = update_testrun( thisCtr, user, plots ) 
    
                    ### environment 
                    set_env( thisCtr, str(tr_id) )             
    
                    yarrdb.componentTestRun.update( ctr_query,
                                                    { '$set': { 'tx'       : -1,
                                                                'rx'       : -1,
                                                                'testRun'  : str(tr_id) }}) 
                    yarrdb.componentTestRun.update( ctr_query,
                                                    { '$unset': { 'stage': '',
                                                                  'environments': '' }} )   
                    update_ver( 'componentTestRun', ctr_query, dbv ) 
                    update_mod( 'componentTestRun', ctr_query )      
    
                    if (maybe_broken):
                        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Broken] change db version -> 1\n' ) )
                        update_ver( '\t\tcomponentTestRun', ctr_query, -1 ) 
                    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] componentTestRun doc: {0} - {1}\n'.format(chip['serialNumber'], thisRun['runNumber']) ) )
    
                    ### insert module - testRun (if registered)
                    query = { 'component': str(mo_query['_id']), 'testRun': str(tr_id) }
                    mo_ctr = yarrdb.componentTestRun.find_one( query )
                    if not mo_ctr:
                        time_now = datetime.datetime.utcnow()
                        mo_ctr_doc = { 'sys': {
                                            'rev': 0,
                                            'cts': time_now,
                                            'mts': time_now },
                                       'component': str(mo_query['_id']),
                                       'testRun'  : str(tr_id),
                                       'state'    : '...',
                                       'testType' : thisRun['testType'],
                                       'qaTest'   : False,
                                       'runNumber': thisRun['runNumber'],
                                       'passed'   : True,
                                       'problems' : True,
                                       'tx'       : -1,
                                       'rx'       : -1,
                                       'dbVersion': dbv }
                        yarrdb.componentTestRun.insert( mo_ctr_doc )
                        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Insert] componentTestRun doc: {0} - {1}\n'.format(mo_serialNumber, thisRun['runNumber']) ) )
            else:
                query = { 'component': str(chip['_id']),
                          'dbVersion': dbv }
                run_entries = yarrdb.componentTestRun.find( query )
                if not run_entries.count() == 0:
                    multiparent = True
                    for run in run_entries:
                        ### insert module - testRun (if registered)
                        query = { 'component': str(mo_query['_id']), 'testRun': run['testRun'] }
                        mo_ctr = yarrdb.componentTestRun.find_one( query )
                        if not mo_ctr:
                            query = { '_id': ObjectId(run['testRun']) }
                            thisRun = yarrdb.testRun.find_one( query )
                            time_now = datetime.datetime.utcnow()
                            mo_ctr_doc = { 'sys': {
                                                'rev': 0,
                                                'cts': time_now,
                                                'mts': time_now },
                                           'component': str(mo_query['_id']),
                                           'testRun'  : run['testRun'],
                                           'state'    : '...',
                                           'testType' : thisRun['testType'],
                                           'qaTest'   : False,
                                           'runNumber': thisRun['runNumber'],
                                           'passed'   : True,
                                           'problems' : True,
                                           'tx'       : -1,
                                           'rx'       : -1,
                                           'dbVersion': dbv }
                            yarrdb.componentTestRun.insert( mo_ctr_doc )
                            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Insert] componentTestRun doc: {0} - {1}\n'.format(mo_serialNumber, thisRun['runNumber']) ) )
   
            if chipId == '':
                if 'chipId' in chipName:
                    chipId = int(chipName[chipName.find('chipId')+6])
                else:
                    if chipType == 'FE-I4B':
                        chipId = 1
                    elif chipType == 'RD53A':
                        chipId = 0
    
            ### component (chip)
            if not chip.get('dbVersion') == dbv:
                user = set_user( chip ) #user
                yarrdb.component.update( ch_query,
                                         { '$set': { 'address'      : user['institution'],
                                                     'user_id'      : str(user['_id']),
                                                     'componentType': 'Front-end Chip',
                                                     'chipType'     : chipType,
                                                     'chipId'       : int(chipId) }} ) 
                yarrdb.component.update( ch_query,
                                         { '$unset': { 'institution' : '',
                                                       'userIdentity': '' }} )         
                update_ver( 'component', ch_query, dbv ) 
                update_mod( 'component', ch_query ) 
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Update] chip doc: {0}\n'.format(chip['serialNumber']) ) )
    
            ### childParentRelation
            cpr_query = { '_id': child['_id'] } 
            yarrdb.childParentRelation.update( cpr_query,
                                               { '$set': { 'status': 'active',
                                                           'chipId': int(chipId) }} ) 
            update_ver( 'childParentRelation', cpr_query, dbv ) 
            update_mod( 'childParentRelation', cpr_query )    
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Update] cpr doc: {0}\n'.format(chip['serialNumber']) ) )

        ### confirmation
        query = { 'component': str(mo_query['_id']) }
        run_entries = yarrdb.componentTestRun.find( query )
        run_list = []
        for run in run_entries:
            run_list.append({ 'testRun': run['testRun'] })
        child_list = []
        for childid in childid_entries:
            query = { '_id': ObjectId(childid) }
            child = yarrdb.childParentRelation.find_one( query )
            child_list.append({ 'component': child['child'] })
        if not run_list == [] and not child_list == []:
            query = { '$and': [{'$or': child_list}, {'$or': run_list}] }
            entries = yarrdb.componentTestRun.find(query).count()
            if not entries == len(child_list)*len(run_list):
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Confirmation of all chips' ) )
                for run in run_list:
                    query = { '_id': ObjectId(run['testRun']) }
                    thisRun = yarrdb.testRun.find_one( query ) 
                    for child in child_list:
                        query = { '_id': ObjectId(child['component']) }
                        query = { 'component': child['component'], 'testRun': run['testRun'] }
                        ch_ctr = yarrdb.componentTestRun.find_one( query )
                        if not ch_ctr:
                            time_now = datetime.datetime.utcnow()
                            ch_ctr_doc = { 'sys': {
                                                'rev': 0,
                                                'cts': time_now,
                                                'mts': time_now },
                                           'component': child['component'],
                                           'testRun'  : run['testRun'],
                                           'state'    : '...',
                                           'testType' : thisRun['testType'],
                                           'qaTest'   : False,
                                           'runNumber': thisRun['runNumber'],
                                           'passed'   : True,
                                           'problems' : True,
                                           'tx'       : -1,
                                           'rx'       : -1,
                                           'dbVersion': dbv }
                            yarrdb.componentTestRun.insert( ch_ctr_doc )
                            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Insert] componentTestRun doc: {0} - {1}\n'.format(chip['serialNumber'], thisRun['runNumber']) ) )
        ### component (module)
        user = set_user( module ) #user
        yarrdb.component.update( mo_query,
                                 { '$set': { 'address' : user['institution'],
                                             'chipType': chipType,
                                             'children': chip_num,
                                             'user_id' : str(user['_id']) }} ) 
        yarrdb.component.update( mo_query,
                                 { '$unset': { 'institution' : '',
                                               'userIdentity': '' }} )         
        query = { 'parent': str(mo_query['_id']), 'dbVersion': { '$ne': dbv } }
        update_ver( 'component', mo_query, dbv ) 
        update_mod( 'component', mo_query )      
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Update] module doc: {}\n'.format(mo_serialNumber) ) )
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish] Module: {}\n'.format(mo_serialNumber) ) )
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Done.') )
    
    finish_update_time = datetime.datetime.now() 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ==============================================\n' ) )
    print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
    print( '\t# Succeeded in conversion.' )
    print( ' ' )

finish_time = datetime.datetime.now()
log_file.write( '\n====        Operation Time        ====\n' )
total_time = datetime.timedelta(seconds=(finish_time-start_time).total_seconds())
log_file.write( 'Total time: ' + str(total_time) + '\n' )
log_file.write( start_time.strftime(  '\tStart: %Y-%m-%dT%H:%M:%S:%f' ) + '\n' )
log_file.write( finish_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f' ) + '\n' )
if not start_update_time == '':
    total_update_time = datetime.timedelta(seconds=(finish_update_time-start_update_time).total_seconds())
    log_file.write( '--------------------------------------\n' )
    log_file.write( 'Update total time:  ' + str(total_update_time) + '\n' )
    log_file.write( start_update_time.strftime( '\tStart: %Y-%m-%dT%H:%M:%S:%f\n' ) )
    log_file.write( finish_update_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f\n' ) )
log_file.write( '======================================' )
log_file.close()

print( start_time.strftime( '# Start time: %Y-%m-%dT%H:%M:%S' ) ) 
print( finish_time.strftime( '# Finish time: %Y-%m-%dT%H:%M:%S' ) ) 
print( '# Total time: ' + str(total_time) + ' [s]' ) 
print( ' ' )
print( '# The path to log file: {}'.format(log_filename) )
print( ' ' )
print( '# Exit ...' )
sys.exit()     
