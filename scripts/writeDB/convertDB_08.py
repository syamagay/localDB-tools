"""
script for convert databaase scheme
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

def write_log( text ):
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S {}\n'.format(text) ) )

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
    yarrdb[collection].update( query, {'$set': { 'dbVersion': ver }}, multi=True )

def is_png(b):
    return bool(re.match(br"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", b[:8]))

def is_pdf(b):
    return bool(re.match(b"^%PDF", b[:4]))

def set_institution(address, user_id):
    query = { '_id': ObjectId(user_id) }
    thisUser = yarrdb.user.find_one( query )
    inst_doc = { 'institution': 'null', 'address': address, 'name': thisUser['userName'] }
    if yarrdb.institution.find_one( inst_doc ): continue
    time_now = datetime.datetime.utcnow()
    inst_doc.update({ 
        'sys': {
            'rev': 0,
            'cts': time_now,
            'mts': time_now },
        'dbVersion': dbv
    }) 
    yarrdb.institution.insert( inst_doc ) 
    write_log( '\t\t[Insert] institution doc: {}'.format(address) ) 

def set_env( thisRun ):
    if 'environment' in thisRun: return ''
    start = thisRun.get('startTime')
    finish = thisRun.get('finishTime', start+datetime.timedelta(minutes=1))
    query = { '$and': [ 
        { 'date': { '$gt': start - datetime.timedelta(minutes=1) }}, 
        { 'date': { '$lt': finish + datetime.timedelta(minutes=1) }} 
    ]}
    environments = yarrdb.environment.find( query )
    if environments.count() == 0: return ''
    time_now = datetime.datetime.utcnow()
    env_doc = { 
        'sys': {
            'rev': 0,
            'cts': time_now,
            'mts': time_now },
        'type': 'data' 
    }
    for env in environments:
        if not env['key'] in file_dcs: 
            write_log( '\t\t[WARNING] Undefined environmental key: {}'.format(env['key']) )
        if not 'description' in env: 
            write_log( '\t\t[WARNING] The description is not written: {}'.format(env['key']) )
        key         = env['key']
        description = env.get('description', 'null') 
        value       = env['value']
        date        = env['date']
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

    env_id = yarrdb.environment.insert( env_doc ) 
    query = { '_id': env_id }
    update_ver( 'environment', query, dbv )
    write_log( '\t\t[Insert] environment doc' )
    return env_id

def update_testrun( thisRun ):
    env_id = set_env( thisRun )
    if thisRun['dbVersion'] == dbv: return
    query = { '_id': thisRun['_id'] }
    if not env_id == '':
        yarrdb.testRun.update( query, { '$set': { 'environment': str(env_id) }})
    update_ver( 'testRun', query, dbv )
    update_mod( 'testRun', query )
    set_institution(thisRun['address'], thisRun['user_id'])
    write_log( '\t\t[Update] testRun doc: {}'.format(thisRun['runNumber']) )

def for_json( code ):
    query = { '_id': ObjectId(code) }
    json_data = yarrdb.json.find_one( query )
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
    data_doc = yarrdb.fs.files.find_one({ 'dbVersion': dbv, 'hash': shaHashed })
    if data_doc:
        data = str(data_doc['_id'])
    else:
        data = fs.put( binary, filename=filename )   
        f_query = { '_id': data }
        c_query = { 'files_id': data }
        yarrdb.fs.files.update( f_query,
                                { '$set': { 'hash': shaHashed }})
        update_ver( 'fs.files', f_query, dbv ) 
        update_ver( 'fs.chunks', c_query, dbv )
        write_log( '\t\t\t\t\t\t[Insert] grid doc: {0}'.format(filename) )
    time_now = datetime.datetime.utcnow()
    config_doc = { 'sys': {
                       'rev': 0,
                       'cts': time_now,
                       'mts': time_now 
                   },
                   'filename': filename, 
                   'chipType': chipType,
                   'title'   : title,    
                   'format'  : 'fs.files',
                   'data_id' : str(data) }
    config_id = yarrdb.config.insert( config_doc )
    write_log( '\t\t\t\t\t\t[Insert] config doc: {}'.format(title) )
    query = { '_id': config_id }
    update_ver( 'config', query, dbv )

    return str(config_id)

def for_data( attachment, ctr_query ):
    code = attachment['code']
    binary = fs.get(ObjectId(code)).read()
    fs.delete( ObjectId(code) )
    write_log( '\t\t\t\t\t\t[Delete] grid doc: {}'.format(attachment['filename']) )
    yarrdb.componentTestRun.update( ctr_query, { 
        '$pull': { 
            'attachments': { 
                'code': code 
            }
        }
    }) 
    code = fs.put( binary, filename=attachment['filename'], dbVersion=dbv ) 
    attachment.update({ 'code': code })
    yarrdb.componentTestRun.update( ctr_query, { 
        '$push': { 
            'attachments': attachment
        }
    })
    query = { 'files_id': ObjectId(code) }
    update_ver( 'fs.chunks', query, dbv )
    write_log( '\t\t\t\t\t\t[Insert] grid doc: {0}'.format(attachment['filename']) )

def for_dat( attachment, ctr_query ):
    code = attachment['code']
    query = { '_id': ObjectId(code) }
    thisData = yarrdb.dat.find_one( query )
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
    fs.delete( ObjectId(code) )
    write_log( '\t\t\t\t\t\t[Delete] grid doc: {}'.format(attachment['filename']) )
    yarrdb.componentTestRun.update( ctr_query, { 
        '$pull': { 
            'attachments': { 
                'code': code 
            }
        }
    }) 
    code = fs.put( binary, filename=thisData['filename'], dbVersion=dbv )  
    attachment.update({ 'code': code })
    yarrdb.componentTestRun.update( ctr_query, { 
        '$push': { 
            'attachments': attachment
        }
    })
    query = { 'files_id': ObjectId(code) }
    update_ver( 'fs.chunks', query, dbv )
    write_log( '\t\t\t\t\t\t[Insert] grid doc: {0}'.format(attachment['filename']) )

#################################################################
# Main function
start_time         = datetime.datetime.now() 
start_update_time  = ''
finish_update_time = ''
write_log( '[Start] convertDB.py' )

# convert database scheme
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
    write_log( '==============================================' )
    write_log( '[Convert] database: {}'.format(args.db) )
    
    start_update_time = datetime.datetime.now() 
    query = { 'componentType' : 'Module',
              'dbVersion'     : { '$ne': dbv } }
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
        write_log( '----------------------------------------------' )
        write_log( '[Start] Module: {}'.format( module['serialNumber'] ) )
    
        query = { 'component': str(module['_id']),
                  'dbVersion': { '$ne': dbv } }
        run_entries = yarrdb.componentTestRun.find( query )
        runid_entries = []
        for run in run_entries:
            runid_entries.append( str(run['_id']) )
        for runid in runid_entries:
            ### conponentTestRun
            ctr_query = { '_id': ObjectId(runid) }
            thisCtr = yarrdb.componentTestRun.find_one( query )
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
                yarrdb.componentTestRun.update( ctr_query,
                                                { '$set': { 'afterCfg': str(config_id) }}) 
                write_log( '\t\t\t\t\t\t[Update] componentTestRun: afterCfg' )
            if thisCtr.get('beforeCfg', False):
                config_id = for_json( thisCtr['beforeCfg'] )
                yarrdb.componentTestRun.update( ctr_query,
                                                { '$set': { 'beforeCfg': str(config_id) }}) 
                write_log( '\t\t\t\t\t\t[Update] componentTestRun: beforeCfg' )

            ### testRun
            tr_query = { '_id': ObjectId(thisCtr['testRun']) }
            thisRun = yarrdb.testRun.find_one( tr_query )
            if thisRun['dbVersion'] == dbv: continue
            if thisRun.get('ctrlCfg', False):
                config_id = for_json( thisRun['ctrlCfg'] )
                yarrdb.componentTestRun.update( tr_query,
                                                { '$set': { 'ctrlCfg': str(config_id) }}) 
                write_log( '\t\t\t\t\t\t[Update] testRun: ctrlCfg' )
            if thisRun.get('scanCfg', False):
                config_id = for_json( thisRun['scanCfg'] )
                yarrdb.componentTestRun.update( tr_query,
                                                { '$set': { 'scanCfg': str(config_id) }}) 
                write_log( '\t\t\t\t\t\t[Update] testRun: scanCfg' )
            update_testrun( thisRun ) 
            set_institution(module['address'], module['user_id'])
            update_ver( 'componentTestRun', ctr_query, dbv ) 
            write_log( '\t\t[Update] componentTestRun doc: {0} - {1}'.format(mo_serialNumber, thisRun['runNumber']) )
    
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
            write_log( 'Chip: {}'.format( chip['serialNumber'] ) )
    
            chipId = chip['chipId']
    
            ### componentTestRun (chip)
            query = { 'component': str(chip['_id']),
                      'dbVersion': { '$ne': dbv } }
            run_entries = yarrdb.componentTestRun.find( query )
            if not run_entries.count() == 0:
                runid_entries = []
                for run in run_entries:
                    runid_entries.append( str(run['_id']) )
                for runid in runid_entries:
                    ### componentTestRun
                    ctr_query = { '_id': ObjectId(runid) }
                    thisCtr = yarrdb.componentTestRun.find_one( ctr_query )
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
                        yarrdb.componentTestRun.update( ctr_query,
                                                        { '$set': { 'afterCfg': str(config_id) }}) 
                        write_log( '\t\t\t\t\t\t[Update] componentTestRun: afterCfg' )
                    if thisCtr.get('beforeCfg', False):
                        config_id = for_json( thisCtr['beforeCfg'] )
                        yarrdb.componentTestRun.update( ctr_query,
                                                        { '$set': { 'beforeCfg': str(config_id) }}) 
                        write_log( '\t\t\t\t\t\t[Update] componentTestRun: beforeCfg' )
        
                    ### testRun
                    tr_query = { '_id': ObjectId(thisCtr['testRun']) }
                    thisRun = yarrdb.testRun.find_one( tr_query )
                    if thisRun['dbVersion'] == dbv: continue
                    if thisRun.get('ctrlCfg', False):
                        config_id = for_json( thisRun['ctrlCfg'] )
                        yarrdb.componentTestRun.update( tr_query,
                                                        { '$set': { 'ctrlCfg': str(config_id) }}) 
                        write_log( '\t\t\t\t\t\t[Update] testRun: ctrlCfg' )
                    if thisRun.get('scanCfg', False):
                        config_id = for_json( thisRun['scanCfg'] )
                        yarrdb.componentTestRun.update( tr_query,
                                                        { '$set': { 'scanCfg': str(config_id) }}) 
                        write_log( '\t\t\t\t\t\t[Update] testRun: scanCfg' )
                    update_testrun( thisRun ) 
                    update_ver( 'componentTestRun', ctr_query, dbv ) 
                    write_log( '\t\t[Update] componentTestRun doc: {0} - {1}'.format(mo_serialNumber, thisRun['runNumber']) )
    
            ### component (chip)
            if not chip.get('dbVersion') == dbv:
                yarrdb.component.update( ch_query,
                                         { '$unset': { 'name' : '' }})
                update_ver( 'component', ch_query, dbv ) 
                update_mod( 'component', ch_query )
                set_institution(chip['address'], chip['user_id'])
                write_log( '[Update] chip doc: {0}'.format(chip['serialNumber']) )
    
                ### childParentRelation
                cpr_query = { '_id': child['_id'] } 
                yarrdb.childParentRelation.update( cpr_query,
                                                   { '$set': { 'status': 'active',
                                                               'chipId': int(chipId) }} )
                update_ver( 'childParentRelation', cpr_query, dbv )
                update_mod( 'childParentRelation', cpr_query )    
                write_log( '[Update] cpr doc: {0}'.format(chip['serialNumber']) )

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
                write_log( 'Confirmation of all chips' )
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
                            write_log( '\t\t[Insert] componentTestRun doc: {0} - {1}'.format(chip['serialNumber'], thisRun['runNumber']) )
        ### component (module)
        yarrdb.component.update( mo_query,
                                 { '$set': { 'children': chip_num }} )
        query = { 'parent': str(mo_query['_id']), 'dbVersion': { '$ne': dbv } }
        if yarrdb.childParentRelation.find( query ).count() == 0:
            update_ver( 'component', mo_query, dbv ) 
            write_log( '[Update] module doc: {}'.format(mo_serialNumber) )
        else:
            update_ver( 'component', mo_query, -1 )
            write_log( '[Unupdate] module doc: {}'.format(mo_serialNumber) )
        update_mod( 'component', mo_query )  
        write_log( '[Finish] Module: {}'.format(mo_serialNumber) )
        print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S Done.') )
    
    for data in yarrdb.json.find():
        query = { '_id': data['_id'] }
        filename = data['filename']
        yarrdb.json.remove( query ) 
        write_log( '[Delete] json doc: {0}'.format(filename) )
    yarrdb.drop_collection( 'json' )
    for data in yarrdb.dat.find():
        query = { '_id': data['_id'] }
        filename = data['filename']
        yarrdb.dat.remove( query ) 
        write_log( '[Delete] dat doc: {0}'.format(filename) )
    yarrdb.drop_collection( 'dat' )
    for data in yarrdb.environment.find():
        if data['dbVersion'] == dbv: continue
        query = { '_id': data['_id'] }
        key = data['key']
        yarrdb.environment.remove( query ) 
        write_log( '[Delete] env doc: {0}'.format(key) )

    finish_update_time = datetime.datetime.now() 
    write_log( '==============================================' )
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
