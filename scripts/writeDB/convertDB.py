"""
script for conversion databaase scheme
log file ---> log/loConvert_%m%d_%H%M.txt
"""

### Import 
import os, sys, datetime, json, re, hashlib
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
localdb = client[args.db]
fs = gridfs.GridFS( localdb )
dbv = args.version
olddbv = args.oldversion

### Set log file
log_dir = './log'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
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

def write_log( text ):
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S {}\n'.format(text) ) )

def update_mod(collection, query):
    entries = localdb[collection].find( query )
    timestamp = datetime.datetime.utcnow()
    for entry in entries:
        query = { '_id': entry['_id'] }
        if entry.get('sys'):
            rev = entry['sys']['rev']+1
        else:
            rev = 0
            localdb[collection].update( query, { '$set': { 'sys': { 'cts': timestamp } }})
        localdb[collection].update(query, 
            { 
                '$set': { 
                    'sys.rev'  : int(rev), 
                    'sys.mts'  : timestamp 
                }
            }
        ) 

def update_ver(collection, query, ver):
    localdb[collection].update( query, { '$set': { 'dbVersion': ver }}, multi=True )

def is_png(b):
    return bool(re.match(br"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", b[:8]))

def is_pdf(b):
    return bool(re.match(b"^%PDF", b[:4]))

### Main function
start_time = datetime.datetime.now() 
start_update_time = ''
finish_update_time = ''
write_log( '[Start] convertDB.py' )

### convert database scheme
print( '# Conversion flow' )
print( '\t1. Replicate : python copyDB.py    : {0}      ---> {1}_copy'.format( args.db, args.db ) )
print( '\t2. Convert   : python convertDB.py : {0}(old) ---> {1}(new)'.format( args.db, args.db ) )
print( '\t3. Confirm   : python confirmDB.py : {0}(new) ---> {1}(confirmed)'.format( args.db, args.db ) )
print( ' ' )
print( '# This is the stage of step2. Convert' )
print( '# It is recommended to run "copyDB.py" first.' )
print( ' ' )
print( '{:^34}'.format('Database information') )
print( '----------------------------------' )
print( ' name: {}'.format( args.db ) )
print( ' version (before conversion): {}'.format( olddbv ) )
print( ' version (after conversion):  {}'.format( dbv ) )
print( '----------------------------------' )
print( ' ' )
answer = input_answer( '# Do you convert db scheme? (y/n) > ' )
if answer == 'y' :
    if olddbv == 0.5:
        ### Function
        def set_institution(address, user_id):
            query = { '_id': ObjectId(user_id) }
            thisUser = localdb.user.find_one( query )
            inst_doc = { 'institution': 'null', 'address': address, 'name': thisUser['userName'] }
            if localdb.institution.find_one( inst_doc ): return
            inst_id = localdb.institution.insert( inst_doc ) 
            query = { '_id': inst_id }
            update_mod( 'institution', query )
            update_ver( 'institution', query, dbv )
            write_log( '\t\t[Insert] institution doc: {}'.format(address) ) 
        
        def set_user(doc):  #for old-v
            if 'user_id' in doc:
                query = { '_id': ObjectId(doc['user_id']) }
                user = localdb.user.find_one( query )
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
            user = localdb.user.find_one( user_doc )
            if user: return user
        
            user_id = localdb.user.insert( user_doc )
            query = { '_id': user_id }
            update_ver( 'user', query, dbv )
            update_mod( 'user', query )
            write_log( '\t\t [Insert] user doc: {}'.format(name) ) 
            set_institution(institution, user_id)
            query = { '_id': user_id }
            user = localdb.user.find_one( query )
            return user
        
        def set_env(thisCtr, tr_id): 
            if not 'environments' in thisCtr: return ''
            tr_query = { '_id': ObjectId(tr_id) }
            thisRun = localdb.testRun.find_one( tr_query )
            if 'environment' in thisRun: return ''
            date = thisRun['startTime']
            environments = thisCtr['environments']
            env_doc = { 'type': 'data' }
            for env in environments:
                key = env['key']
                description = env.get('description', 'null') 
                value = env['value']
                if not key in file_dcs: write_log( '\t\t[WARNING] Undefined environmental key: {}'.format(key) )
                if description == 'null': write_log( '\t\t[WARNING] The description is not written: {}'.format(key) )
                if not key in env_doc: 
                    env_doc.update({ key: [] })
                    env_doc[key].append({
                        'data': [
                            { 
                                'date' : date,
                                'value': value 
                            }
                        ],
                        'description': description 
                    })
                else:
                    for data in env_doc[key]:
                        if data['description'] == description:
                            env_doc[key][env_doc[key].index(data)]['data'].append({
                                'date': date,
                                'value': value
                            })
                        else:
                            env_doc[key].append({
                                'data': [
                                    { 
                                        'date' : date,
                                        'value': value 
                                    }
                                ],
                                'description': description 
                            })
        
            env_id = localdb.environment.insert( env_doc ) 
            query = { '_id': env_id }
            update_ver( 'environment', query, dbv )
            update_mod( 'environment', query ) 
            write_log( '\t\t[Insert] environment doc' )
            return env_id
        
        def update_testrun(thisCtr, user, plots):
            tr_query = { '_id': ObjectId(thisCtr['testRun']) }
            thisRun = localdb.testRun.find_one( tr_query )
            doc = { 
                'testType' : thisRun['testType'],
                'runNumber': thisRun['runNumber'],
                'address'  : user['institution'],
                'user_id'  : str(user['_id']),
                'dbVersion': dbv 
            } 
            thisTestRun = localdb.testRun.find_one( doc )
            if not thisTestRun:
                stage = thisCtr.get('stage', 'null')
                if not stage in file_stages: write_log( '\t\t[WARNING] Undefined this stage: {}'.format(stage) )
                date = thisRun['date']
                doc.update({ 
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
                    'display'     : thisRun.get('display',False)
                })  
                tr_id = localdb.testRun.insert( doc ) 
                env_id = set_env( thisCtr, str(tr_id) )
                query = { '_id': tr_id }
                if not env_id == '':
                    localdb.testRun.update( query, { '$set': { 'environment': str(env_id) }})
                update_ver( 'testRun', query, dbv ) 
                update_mod( 'testRun', query ) 
                write_log( '\t\t[Insert] testRun doc: {0}'.format(thisRun['runNumber']) )
            else:
                tr_id = thisTestRun['_id']
                query = { '_id': tr_id }
                if len(plots) > thisTestRun['plots']:
                    localdb.testRun.update( query, { '$set': { 'plots': plots }} )
                if thisRun.get('display', False) and not thisTestRun['display']:
                    localdb.testRun.update( query, { '$set': { 'display': thisRun['display'] }} ) 
                env_id = set_env( thisCtr, str(tr_id) )
                if not env_id == '':
                    localdb.testRun.update( query, { '$set': { 'environment': str(env_id) }})
        
            if not thisRun.get('dbVersion', '') == dbv:
                localdb.testRun.remove( tr_query ) #REMOVE
                write_log( '\t\t[Delete] testRun doc: {0}'.format(thisRun['runNumber']) )
        
            return tr_id
        
        def for_json(attachment, chipType, ctr_query):
            code = attachment['code']
            contentType = attachment['contentType']
            binary = fs.get(ObjectId(code)).read()
            shaHashed = hashlib.sha256(binary).hexdigest()
            json_data = json.loads(binary) 
            doc = localdb.fs.files.find_one({ 'dbVersion': dbv, 'hash': shaHashed })
            if doc:
                fs.delete( ObjectId(code) )
                code = str(doc['_id'])
            else:
                fs.delete( ObjectId(code) )
                code = fs.put( binary, filename='chipCfg.json', hash=shaHashed ) 
                query = { '_id': code }
                update_ver( 'fs.files', query, dbv ) 
                update_mod( 'fs.files', query ) 
                query = { 'files_id': code }
                update_ver( 'fs.chunks', query, dbv )
                update_mod( 'fs.chunks', query )
                write_log( '\t\t\t\t\t\t[Insert] grid doc: chipCfg.json' )
        
            chipId = ''
            if chipType in json_data:
                if chipType == 'FE-I4B':
                    chipId = json_data[chipType]['Parameter']['chipId']
                elif chipType == 'RD53A':
                    chipId = json_data[chipType]['Parameter']['ChipId']
            config_id = localdb.config.insert({
                'filename' : 'chipCfg.json',
                'chipType' : chipType,
                'title'    : 'chipCfg',
                'format'   : 'fs.files',
                'data_id'  : str(code)
            })
            query = { '_id': config_id }
            update_ver( 'config', query, dbv )
            update_mod( 'config', query )
            write_log( '\t\t\t\t\t\t[Delete/Insert] config doc: chipCfg.json' )
            localdb.componentTestRun.update( ctr_query, { '$set': { '{}Cfg'.format(contentType): str(config_id) }}) 
        
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
            code = fs.put( binary, filename='{0}.{1}'.format(filename, contentType) ) 
            localdb.componentTestRun.update( ctr_query, { 
                '$push': { 
                    'attachments': { 
                        'code'       : str(code),
                        'dateTime'   : attachment['dateTime'],
                        'title'      : filename, 
                        'description': 'describe',
                        'contentType': contentType,
                        'filename'   : '{0}.{1}'.format(filename, contentType) 
                    }
                }
            })
            query = { '_id': code }
            update_ver( 'fs.files', query, dbv ) 
            update_mod( 'fs.files', query ) 
            query = { 'files_id': code }
            update_ver( 'fs.chunks', query, dbv )
            update_mod( 'fs.chunks', query )
            write_log( '\t\t\t\t\t\t[Delete/Insert] grid doc: {0}.{1}'.format(filename, contentType) )
        
            return filename
        
        def for_broken(attachment, ctr_query):
            code = attachment['code']
            localdb.componentTestRun.update( ctr_query, { 
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
            update_mod( 'fs.files', query ) 
            query = { 'files_id': ObjectId(code) }
            update_ver( 'fs.chunks', query, -1 )
            update_mod( 'fs.chunks', query )
            write_log( '\t\t\t\t\t\t[Broken] grid doc: {0}.{1}'.format(attachment['filename'], attachment['contentType']) )
            
            return True
        
        #################################################################
        #################################################################
        ### Main function
        # modify module document
        print( '# Convert database scheme: {}'.format(args.db) )
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
        write_log( '==============================================' )
        write_log( '[Convert] database: {}'.format(args.db) )
        
        start_update_time = datetime.datetime.now() 
        query = { 
            'componentType' : 'Module',
            'dbVersion'     : { '$ne': dbv } 
        }
        module_entries = localdb.component.find( query )
        moduleid_entries = []
        for module in module_entries:
            moduleid_entries.append( str(module['_id']) )
        for moduleid in moduleid_entries:
            query = { '_id': ObjectId(moduleid) }
            module = localdb.component.find_one( query )
        
            mo_serialNumber = module['serialNumber']
            mo_query = { '_id': module['_id'] }
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Module: {}'.format(mo_serialNumber)) )
        
            ### convert module - testRun (if registered)
            write_log( '----------------------------------------------' )
            write_log( '[Start] Module: {}'.format( module['serialNumber'] ) )
        
            query = { 'component': str(module['_id']),
                      'dbVersion': { '$ne': dbv } }
            run_entries = localdb.componentTestRun.find( query )
            runid_entries = []
            for run in run_entries:
                runid_entries.append( str(run['_id']) )
            for runid in runid_entries:
                ctr_query = { '_id': ObjectId(runid) }
                thisCtr = localdb.componentTestRun.find_one( query )
                write_log( '\t\tComponentTestRun: #{}'.format( thisCtr['runNumber'] ) )
                tr_query = { '_id': ObjectId(thisCtr['testRun']) }
                thisRun = localdb.testRun.find_one( tr_query )
                user = set_user( thisRun ) 
        
                ### attachments
                attachments = thisRun.get('attachments',[])
                plots = []
                maybe_broken = False
                write_log( '\t\t\t\tAttachments:' )
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
        
                localdb.componentTestRun.update( ctr_query,
                                                { '$set': { 'tx'       : -1,
                                                            'rx'       : -1,
                                                            'testRun'  : str(tr_id) }}) 
                localdb.componentTestRun.update( ctr_query,
                                                { '$unset': { 'stage': '',
                                                              'environments': '' }} ) 
                if (maybe_broken):
                    write_log( '\t\t\t\t\t\t[Broken] change db version -> -1' )
                    update_ver( 'componentTestRun', ctr_query, -1 ) 
                else:
                    update_ver( 'componentTestRun', ctr_query, dbv ) 
                update_mod( 'componentTestRun', ctr_query ) 
        
            # modify chip documents
            query = { 'parent': str(module['_id']) }
            child_entries = localdb.childParentRelation.find( query )
            childid_entries = []
            for child in child_entries:
                childid_entries.append( str(child['_id']) )
            chip_num = len(childid_entries)
            for childid in childid_entries:
                query = { '_id': ObjectId(childid) }
                child = localdb.childParentRelation.find_one( query )
                ch_query = { '_id': ObjectId(child['child']) }
                chip = localdb.component.find_one( ch_query )
                ### convert chip - testRun (if registered)
                write_log( 'Chip: {}'.format( chip['serialNumber'] ) )
        
                chipType = chip['componentType']
                chipName = chip['name']
                chipId = ''
        
                ### componentTestRun (chip)
                query = { 'component': str(chip['_id']),
                          'dbVersion': { '$ne': dbv } }
                run_entries = localdb.componentTestRun.find( query )
                if not run_entries.count() == 0:
                    runid_entries = []
                    for run in run_entries:
                        runid_entries.append( str(run['_id']) )
                    for runid in runid_entries:
                        ctr_query = { '_id': ObjectId(runid) }
                        thisCtr = localdb.componentTestRun.find_one( ctr_query )
                        write_log( '\t\tComponentTestRun: #{}'.format( thisCtr['runNumber'] ) )
                        tr_query = { '_id': ObjectId(thisCtr['testRun']) }
                        thisRun = localdb.testRun.find_one( tr_query )
                        user = set_user( thisRun ) #user
        
                        ### attachments
                        attachments = thisRun.get('attachments',[])
                        plots = []
                        maybe_broken = False
                        write_log( '\t\t\t\tAttachments:' )
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
        
                        localdb.componentTestRun.update( ctr_query,
                                                        { '$set': { 'tx'       : -1,
                                                                    'rx'       : -1,
                                                                    'testRun'  : str(tr_id) }}) 
                        localdb.componentTestRun.update( ctr_query,
                                                        { '$unset': { 'stage': '',
                                                                      'environments': '' }} )   
                        if (maybe_broken):
                            write_log( '\t\t[Broken] change db version -> 1' )
                            update_ver( '\t\tcomponentTestRun', ctr_query, -1 ) 
                        else:
                            update_ver( 'componentTestRun', ctr_query, dbv ) 
                        update_mod( 'componentTestRun', ctr_query )      
        
                        ### insert module - testRun (if registered)
                        query = { 'component': str(mo_query['_id']), 'testRun': str(tr_id) }
                        mo_ctr = localdb.componentTestRun.find_one( query )
                        if not mo_ctr:
                            mo_ctr_doc = { 
                                'component': str(mo_query['_id']),
                                'testRun'  : str(tr_id),
                                'state'    : '...',
                                'testType' : thisRun['testType'],
                                'qaTest'   : False,
                                'runNumber': thisRun['runNumber'],
                                'passed'   : True,
                                'problems' : True,
                                'tx'       : -1,
                                'rx'       : -1 
                            }
                            mo_ctr_id = localdb.componentTestRun.insert( mo_ctr_doc )
                            query = { '_id': mo_ctr_id }
                            update_ver( 'componentTestRun', query, dbv )
                            update_mod( 'componentTestRun', query )
                            write_log( '\t\t[Insert] componentTestRun doc: {0} - {1}'.format(mo_serialNumber, thisRun['runNumber']) )
                else:
                    query = { 'component': str(chip['_id']),
                              'dbVersion': dbv }
                    run_entries = localdb.componentTestRun.find( query )
                    if not run_entries.count() == 0:
                        for run in run_entries:
                            ### insert module - testRun (if registered)
                            query = { 'component': str(mo_query['_id']), 'testRun': run['testRun'] }
                            mo_ctr = localdb.componentTestRun.find_one( query )
                            if not mo_ctr:
                                query = { '_id': ObjectId(run['testRun']) }
                                thisRun = localdb.testRun.find_one( query )
                                mo_ctr_doc = { 
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
                                }
                                mo_ctr_id = localdb.componentTestRun.insert( mo_ctr_doc )
                                query = { '_id': mo_ctr_id }
                                update_ver( 'componentTestRun', query, dbv )
                                update_mod( 'componentTestRun', query )
                                write_log( '\t\t[Insert] componentTestRun doc: {0} - {1}'.format(mo_serialNumber, thisRun['runNumber']) )
        
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
                    localdb.component.update( ch_query,
                                             { '$set': { 'address'      : user['institution'],
                                                         'user_id'      : str(user['_id']),
                                                         'componentType': 'Front-end Chip',
                                                         'chipType'     : chipType,
                                                         'chipId'       : int(chipId) }} ) 
                    localdb.component.update( ch_query,
                                             { '$unset': { 'institution' : '',
                                                           'userIdentity': '' }} )         
                    update_ver( 'component', ch_query, dbv ) 
                    update_mod( 'component', ch_query )
        
                ### childParentRelation
                cpr_query = { '_id': child['_id'] } 
                localdb.childParentRelation.update( cpr_query, { 
                    '$set': { 
                        'status': 'active',
                        'chipId': int(chipId) 
                    }
                }) 
                update_ver( 'childParentRelation', cpr_query, dbv ) 
                update_mod( 'childParentRelation', cpr_query )    
        
            ### confirmation
            query = { 'component': str(mo_query['_id']) }
            run_entries = localdb.componentTestRun.find( query )
            run_list = []
            for run in run_entries:
                run_list.append({ 'testRun': run['testRun'] })
            child_list = []
            for childid in childid_entries:
                query = { '_id': ObjectId(childid) }
                child = localdb.childParentRelation.find_one( query )
                child_list.append({ 'component': child['child'] })
            if not run_list == [] and not child_list == []:
                query = { '$and': [{'$or': child_list}, {'$or': run_list}] }
                entries = localdb.componentTestRun.find(query).count()
                if not entries == len(child_list)*len(run_list):
                    write_log( 'All chips' )
                    for run in run_list:
                        query = { '_id': ObjectId(run['testRun']) }
                        thisRun = localdb.testRun.find_one( query ) 
                        for child in child_list:
                            query = { '_id': ObjectId(child['component']) }
                            query = { 'component': child['component'], 'testRun': run['testRun'] }
                            ch_ctr = localdb.componentTestRun.find_one( query )
                            if not ch_ctr:
                                ch_ctr_doc = { 
                                    'component': child['component'],
                                    'testRun'  : run['testRun'],
                                    'state'    : '...',
                                    'testType' : thisRun['testType'],
                                    'qaTest'   : False,
                                    'runNumber': thisRun['runNumber'],
                                    'passed'   : True,
                                    'problems' : True,
                                    'tx'       : -1,
                                    'rx'       : -1
                                }
                                ch_ctr_id = localdb.componentTestRun.insert( ch_ctr_doc )
                                query = { '_id': ch_ctr_id }
                                update_ver( 'componentTestRun', query, dbv )
                                update_mod( 'componentTestRun', query )
                                write_log( '\t\t[Insert] componentTestRun doc: {0} - {1}'.format(chip['serialNumber'], thisRun['runNumber']) )
            ### component (module)
            user = set_user( module ) #user
            localdb.component.update( mo_query,
                                     { '$set': { 'address' : user['institution'],
                                                 'chipType': chipType,
                                                 'children': chip_num,
                                                 'user_id' : str(user['_id']) }} ) 
            localdb.component.update( mo_query,
                                     { '$unset': { 'institution' : '',
                                                   'userIdentity': '' }} )         
            query = { 'parent': str(mo_query['_id']), 'dbVersion': { '$ne': dbv } }
            update_ver( 'component', mo_query, dbv ) 
            update_mod( 'component', mo_query )  
            write_log( '[Finish] Module: {}'.format(mo_serialNumber) )
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Done.') )
        
        finish_update_time = datetime.datetime.now() 
        write_log( '==============================================' )
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]') )
        print( '\t# Succeeded in conversion.' )
        print( ' ' )

    if olddbv == 0.8:
        ### Function
        def set_institution(address, user_id):
            query = { '_id': ObjectId(user_id) }
            thisUser = localdb.user.find_one( query )
            inst_doc = { 'institution': 'null', 'address': address, 'name': thisUser['userName'] }
            if localdb.institution.find_one( inst_doc ): return
            inst_id = localdb.institution.insert( inst_doc ) 
            query = { '_id': inst_id }
            update_mod( 'institution', query )
            update_ver( 'institution', query, dbv )
            write_log( '\t\t[Insert] institution doc: {}'.format(address) ) 
        
        def set_user(doc):  #for old-v
            if 'user_id' in doc:
                query = { '_id': ObjectId(doc['user_id']) }
                user = localdb.user.find_one( query )
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
            user = localdb.user.find_one( user_doc )
            if user: return user
        
            user_id = localdb.user.insert( user_doc )
            query = { '_id': user_id }
            update_ver( 'user', query, dbv )
            update_mod( 'user', query )
            write_log( '\t\t [Insert] user doc: {}'.format(name) ) 
            set_institution(institution, user_id)
            query = { '_id': user_id }
            user = localdb.user.find_one( query )
            return user
        
        def set_env( thisRun ):
            if 'environment' in thisRun: return ''
            start = thisRun.get('startTime')
            finish = thisRun.get('finishTime', start+datetime.timedelta(minutes=1))
            query = { '$and': [ 
                { 'date': { '$gt': start - datetime.timedelta(minutes=1) }}, 
                { 'date': { '$lt': finish + datetime.timedelta(minutes=1) }} 
            ]}
            environments = localdb.environment.find( query )
            if environments.count() == 0: return ''
            env_doc = { 'type': 'data' }
            for env in environments:
                key = env['key']
                description = env.get('description', 'null') 
                value = env['value']
                date        = env['date']
                if not key in file_dcs: write_log( '\t\t[WARNING] Undefined environmental key: {}'.format(key) )
                if description == 'null': write_log( '\t\t[WARNING] The description is not written: {}'.format(key) )
                if not key in env_doc: 
                    env_doc.update({ key: [] })
                    env_doc[key].append({
                        'data': [
                            { 
                                'date' : date,
                                'value': value 
                            }
                        ],
                        'description': description 
                    })
                else:
                    for data in env_doc[key]:
                        if data['description'] == description:
                            env_doc[key][env_doc[key].index(data)]['data'].append({
                                'date': date,
                                'value': value
                            })
                        else:
                            env_doc[key].append({
                                'data': [
                                    { 
                                        'date' : date,
                                        'value': value 
                                    }
                                ],
                                'description': description 
                            })
        
            env_id = localdb.environment.insert( env_doc ) 
            query = { '_id': env_id }
            update_ver( 'environment', query, dbv )
            update_mod( 'environment', query ) 
            write_log( '\t\t[Insert] environment doc' )
            return env_id
        
        def update_testrun(thisRun):
            env_id = set_env( thisRun )
            if thisRun['dbVersion'] == dbv: return
            query = { '_id': thisRun['_id'] }
            if not env_id == '':
                localdb.testRun.update( query, { '$set': { 'environment': str(env_id) }})
            update_ver( 'testRun', query, dbv )
            update_mod( 'testRun', query )
            set_institution(thisRun['address'], thisRun['user_id'])
        
        def for_json(code):
            query = { '_id': ObjectId(code) }
            json_data = localdb.json.find_one( query )
            filename = json_data['filename']
            title = json_data['title']
            chipType = json_data['chipType']
            if title == 'chipCfg': filename = 'chipCfg.json'
            path = 'tmp.json'
            with open(path, 'w') as f:
                json.dump( json_data['data'], f, indent=4 )
            binary_image = open(path, 'rb')
            binary = binary_image.read()
            shaHash = hashlib.sha256(binary)
            shaHashed = shaHash.hexdigest()
            data_doc = localdb.fs.files.find_one({ 'dbVersion': dbv, 'hash': shaHashed })
            if data_doc:
                data = str(data_doc['_id'])
            else:
                data = fs.put( binary, filename=filename )   
                f_query = { '_id': data }
                c_query = { 'files_id': data }
                localdb.fs.files.update( f_query,
                                        { '$set': { 'hash': shaHashed }})
                update_ver( 'fs.files', f_query, dbv ) 
                update_mod( 'fs.files', f_query ) 
                update_ver( 'fs.chunks', c_query, dbv )
                update_mod( 'fs.chunks', c_query )
                write_log( '\t\t\t\t\t\t[Insert] grid doc: {0}'.format(filename) )
            config_doc = { 
                'filename': filename, 
                'chipType': chipType,
                'title'   : title,    
                'format'  : 'fs.files',
                'data_id' : str(data) 
            }
            config_id = localdb.config.insert( config_doc )
            query = { '_id': config_id }
            update_ver( 'config', query, dbv )
            update_mod( 'config', query )
            write_log( '\t\t\t\t\t\t[Insert] config doc: {}'.format(title) )
        
            return str(config_id)
        
        def for_data(attachment, ctr_query):
            code = attachment['code']
            binary = fs.get(ObjectId(code)).read()
            fs.delete( ObjectId(code) )
            localdb.componentTestRun.update( ctr_query, { 
                '$pull': { 
                    'attachments': { 
                        'code': code 
                    }
                }
            }) 
            code = fs.put( binary, filename=attachment['filename'] ) 
            attachment.update({ 'code': str(code) })
            localdb.componentTestRun.update( ctr_query, { 
                '$push': { 
                    'attachments': attachment
                }
            })
            query = { '_id': code }
            update_ver( 'fs.files', query, dbv )
            update_mod( 'fs.files', query )
            query = { 'files_id': code }
            update_ver( 'fs.chunks', query, dbv )
            update_mod( 'fs.chunks', query )
            write_log( '\t\t\t\t\t\t[Delete/Insert] grid doc: {0}'.format(attachment['filename']) )
        
        def for_dat( attachment, ctr_query ):
            code = attachment['code']
            query = { '_id': ObjectId(code) }
            thisData = localdb.dat.find_one( query )
            thisDat = thisData['data']
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
            localdb.componentTestRun.update( ctr_query, { '$pull': { 'attachments': { 'code': code }}}) 
            code = fs.put( binary, filename=thisData['filename'] )  
            attachment.update({ 'code': str(code) })
            localdb.componentTestRun.update( ctr_query, { '$push': { 'attachments': attachment }})
            query = { '_id': code }
            update_ver( 'fs.files', query, dbv )
            update_mod( 'fs.files', query )
            query = { 'files_id': code }
            update_ver( 'fs.chunks', query, dbv )
            update_mod( 'fs.chunks', query )
            write_log( '\t\t\t\t\t\t[Insert] grid doc: {0}'.format(attachment['filename']) )
        
        #################################################################
        #################################################################
        
        ### Main function
        # modify module document
        print( '# Convert database scheme: {}'.format(args.db) )
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
        write_log( '==============================================' )
        write_log( '[Convert] database: {}'.format(args.db) )
        
        start_update_time = datetime.datetime.now() 
        query = { 
            'componentType' : 'Module',
            'dbVersion'     : { '$ne': dbv } 
        }
        module_entries = localdb.component.find( query )
        moduleid_entries = []
        for module in module_entries:
            moduleid_entries.append( str(module['_id']) )
        for moduleid in moduleid_entries:
            query = { '_id': ObjectId(moduleid) }
            module = localdb.component.find_one( query )
        
            mo_serialNumber = module['serialNumber']
            mo_query = { '_id': module['_id'] }
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Module: {}'.format(mo_serialNumber)) )
        
            ### convert module - testRun (if registered)
            write_log( '----------------------------------------------' )
            write_log( '[Start] Module: {}'.format( module['serialNumber'] ) )
        
            query = { 'component': str(module['_id']),
                      'dbVersion': { '$ne': dbv } }
            run_entries = localdb.componentTestRun.find( query )
            runid_entries = []
            for run in run_entries:
                runid_entries.append( str(run['_id']) )
            for runid in runid_entries:
                ctr_query = { '_id': ObjectId(runid) }
                thisCtr = localdb.componentTestRun.find_one( query )
                write_log( '\t\tComponentTestRun: #{}'.format( thisCtr['runNumber'] ) )
                attachments = thisCtr.get('attachments',[])
                write_log( '\t\t\t\tAttachments:' )
                for attachment in attachments:
                    code = attachment.get('code')
                    if attachment['contentType'] == 'dat':
                        for_dat( attachment, ctr_query )
                    else:
                        for_data( attachment, ctr_query )
        
                if thisCtr.get('afterCfg', False):
                    config_id = for_json( thisCtr['afterCfg'] )
                    localdb.componentTestRun.update( ctr_query, { '$set': { 'afterCfg': str(config_id) }}) 
                if thisCtr.get('beforeCfg', False):
                    config_id = for_json( thisCtr['beforeCfg'] )
                    localdb.componentTestRun.update( ctr_query, { '$set': { 'beforeCfg': str(config_id) }}) 
        
                ### testRun
                tr_query = { '_id': ObjectId(thisCtr['testRun']) }
                thisRun = localdb.testRun.find_one( tr_query )
                if thisRun['dbVersion'] == dbv: continue
                if thisRun.get('ctrlCfg', False):
                    config_id = for_json( thisRun['ctrlCfg'] )
                    localdb.componentTestRun.update( tr_query, { '$set': { 'ctrlCfg': str(config_id) }}) 
                if thisRun.get('scanCfg', False):
                    config_id = for_json( thisRun['scanCfg'] )
                    localdb.componentTestRun.update( tr_query, { '$set': { 'scanCfg': str(config_id) }}) 
                update_testrun( thisRun ) 
                set_institution(module['address'], module['user_id'])
                update_ver( 'componentTestRun', ctr_query, dbv ) 
                update_mod( 'componentTestRun', ctr_query ) 
        
            # modify chip documents
            query = { 'parent': str(module['_id']) }
            child_entries = localdb.childParentRelation.find( query )
            childid_entries = []
            for child in child_entries:
                childid_entries.append( str(child['_id']) )
            chip_num = len(childid_entries)
            for childid in childid_entries:
                query = { '_id': ObjectId(childid) }
                child = localdb.childParentRelation.find_one( query )
                ch_query = { '_id': ObjectId(child['child']) }
                chip = localdb.component.find_one( ch_query )
                ### convert chip - testRun (if registered)
                write_log( 'Chip: {}'.format( chip['serialNumber'] ) )
        
                chipId = chip['chipId']
        
                ### componentTestRun (chip)
                query = { 'component': str(chip['_id']),
                          'dbVersion': { '$ne': dbv } }
                run_entries = localdb.componentTestRun.find( query )
                if not run_entries.count() == 0:
                    runid_entries = []
                    for run in run_entries:
                        runid_entries.append( str(run['_id']) )
                    for runid in runid_entries:
                        ctr_query = { '_id': ObjectId(runid) }
                        thisCtr = localdb.componentTestRun.find_one( ctr_query )
                        write_log( '\t\tComponentTestRun: #{}'.format( thisCtr['runNumber'] ) )
                        attachments = thisCtr.get('attachments',[])
                        write_log( '\t\t\t\tAttachments:' ) 
                        for attachment in attachments:
                            code = attachment.get('code')
                            if attachment['contentType'] == 'dat':
                                for_dat( attachment, ctr_query ) 
                            else:
                                for_data( attachment, ctr_query ) 
                        if thisCtr.get('afterCfg', False):
                            config_id = for_json( thisCtr['afterCfg'] )
                            localdb.componentTestRun.update( ctr_query, { '$set': { 'afterCfg': str(config_id) }}) 
                        if thisCtr.get('beforeCfg', False):
                            config_id = for_json( thisCtr['beforeCfg'] )
                            localdb.componentTestRun.update( ctr_query, { '$set': { 'beforeCfg': str(config_id) }}) 
            
                        ### testRun
                        tr_query = { '_id': ObjectId(thisCtr['testRun']) }
                        thisRun = localdb.testRun.find_one( tr_query )
                        if thisRun['dbVersion'] == dbv: continue
                        if thisRun.get('ctrlCfg', False):
                            config_id = for_json( thisRun['ctrlCfg'] )
                            localdb.componentTestRun.update( tr_query, { '$set': { 'ctrlCfg': str(config_id) }}) 
                        if thisRun.get('scanCfg', False):
                            config_id = for_json( thisRun['scanCfg'] )
                            localdb.componentTestRun.update( tr_query, { '$set': { 'scanCfg': str(config_id) }}) 
                        update_testrun( thisRun ) 
                        update_ver( 'componentTestRun', ctr_query, dbv ) 
                        update_mod( 'componentTestRun', ctr_query, dbv ) 
        
                        ### insert module - testRun (if registered)
                        query = { 'component': str(mo_query['_id']), 'testRun': str(tr_query['_id']) }
                        mo_ctr = localdb.componentTestRun.find_one( query )
                        if not mo_ctr:
                            mo_ctr_doc = { 
                                'component': str(mo_query['_id']),
                                'testRun'  : str(tr_query['_id']),
                                'state'    : '...',
                                'testType' : thisRun['testType'],
                                'qaTest'   : False,
                                'runNumber': thisRun['runNumber'],
                                'passed'   : True,
                                'problems' : True,
                                'tx'       : -1,
                                'rx'       : -1 
                            }
                            mo_ctr_id = localdb.componentTestRun.insert( mo_ctr_doc )
                            query = { '_id': mo_ctr_id }
                            update_ver( 'componentTestRun', query, dbv )
                            update_mod( 'componentTestRun', query )
                            write_log( '\t\t[Insert] componentTestRun doc: {0} - {1}'.format(mo_serialNumber, thisRun['runNumber']) )
                else:
                    query = { 'component': str(chip['_id']),
                              'dbVersion': dbv }
                    run_entries = localdb.componentTestRun.find( query )
                    if not run_entries.count() == 0:
                        for run in run_entries:
                            ### insert module - testRun (if registered)
                            query = { 'component': str(mo_query['_id']), 'testRun': run['testRun'] }
                            mo_ctr = localdb.componentTestRun.find_one( query )
                            if not mo_ctr:
                                query = { '_id': ObjectId(run['testRun']) }
                                thisRun = localdb.testRun.find_one( query )
                                mo_ctr_doc = { 
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
                                }
                                mo_ctr_id = localdb.componentTestRun.insert( mo_ctr_doc )
                                query = { '_id': mo_ctr_id }
                                update_ver( 'componentTestRun', query, dbv )
                                update_mod( 'componentTestRun', query )
                                write_log( '\t\t[Insert] componentTestRun doc: {0} - {1}'.format(mo_serialNumber, thisRun['runNumber']) )
        
        
                ### component (chip)
                if not chip.get('dbVersion') == dbv:
                    localdb.component.update( ch_query, { '$unset': { 'name' : '' }})
                    update_ver( 'component', ch_query, dbv ) 
                    update_mod( 'component', ch_query )
                    set_institution(chip['address'], chip['user_id'])
        
                    ### childParentRelation
                    cpr_query = { '_id': child['_id'] } 
                    localdb.childParentRelation.update( cpr_query, {
                        '$set': { 
                            'status': 'active',
                            'chipId': int(chipId) 
                        }
                    })
                    update_ver( 'childParentRelation', cpr_query, dbv )
                    update_mod( 'childParentRelation', cpr_query )    
        
            ### confirmation
            query = { 'component': str(mo_query['_id']) }
            run_entries = localdb.componentTestRun.find( query )
            run_list = []
            for run in run_entries:
                run_list.append({ 'testRun': run['testRun'] })
            child_list = []
            for childid in childid_entries:
                query = { '_id': ObjectId(childid) }
                child = localdb.childParentRelation.find_one( query )
                child_list.append({ 'component': child['child'] })
            if not run_list == [] and not child_list == []:
                query = { '$and': [{'$or': child_list}, {'$or': run_list}] }
                entries = localdb.componentTestRun.find(query).count()
                if not entries == len(child_list)*len(run_list):
                    write_log( 'All chips' )
                    for run in run_list:
                        query = { '_id': ObjectId(run['testRun']) }
                        thisRun = localdb.testRun.find_one( query ) 
                        for child in child_list:
                            query = { '_id': ObjectId(child['component']) }
                            query = { 'component': child['component'], 'testRun': run['testRun'] }
                            ch_ctr = localdb.componentTestRun.find_one( query )
                            if not ch_ctr:
                                ch_ctr_doc = { 
                                    'component': child['component'],
                                    'testRun'  : run['testRun'],
                                    'state'    : '...',
                                    'testType' : thisRun['testType'],
                                    'qaTest'   : False,
                                    'runNumber': thisRun['runNumber'],
                                    'passed'   : True,
                                    'problems' : True,
                                    'tx'       : -1,
                                    'rx'       : -1
                                }
                                ch_ctr_id = localdb.componentTestRun.insert( ch_ctr_doc )
                                query = { '_id': ch_ctr_id }
                                update_ver( 'componentTestRun', query, dbv )
                                update_mod( 'componentTestRun', query )
                                write_log( '\t\t[Insert] componentTestRun doc: {0} - {1}'.format(chip['serialNumber'], thisRun['runNumber']) )
            ### component (module)
            localdb.component.update( mo_query, { '$set': { 'children': chip_num }} )
            query = { 'parent': str(mo_query['_id']), 'dbVersion': { '$ne': dbv } }
            update_ver( 'component', mo_query, dbv ) 
            update_mod( 'component', mo_query )  
            write_log( '[Finish] Module: {}'.format(mo_serialNumber) )
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Done.') )
        
        for data in localdb.json.find():
            query = { '_id': data['_id'] }
            filename = data['filename']
            localdb.json.remove( query ) 
            write_log( '[Delete] json doc: {0}'.format(filename) )
        localdb.drop_collection( 'json' )
        for data in localdb.dat.find():
            query = { '_id': data['_id'] }
            filename = data['filename']
            localdb.dat.remove( query ) 
            write_log( '[Delete] dat doc: {0}'.format(filename) )
        localdb.drop_collection( 'dat' )
        for data in localdb.environment.find():
            if data['dbVersion'] == dbv: continue
            query = { '_id': data['_id'] }
            key = data['key']
            localdb.environment.remove( query ) 
            write_log( '[Delete] env doc: {0}'.format(key) )
        
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
