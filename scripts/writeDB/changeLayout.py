"""
script for convert databaase scheme

log file ---> loCgCh_%m%d_%H%M.txt
replicated DB ---> <dbName>_copy
"""

##### import #####
import os, sys, datetime, json, re, time
import gridfs # gridfs system 
from   pymongo       import MongoClient # use mongodb scheme
from   bson.objectid import ObjectId    # handle bson format

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)) )
sys.path.append( SCRIPT_DIR )
sys.path.append( SCRIPT_DIR + "/src" )

from   arguments import *   # Pass command line arguments into app.py

##### setting about dbs #####
args = getArgs()         
if args.username : url = "mongodb://" + args.username + ":" + args.password + "@" + args.host + ":" + str(args.port) 
else :             url = "mongodb://"                                             + args.host + ":" + str(args.port) 
client = MongoClient( url )
yarrdb = client[args.db]
userdb = client[args.userdb]
fs = gridfs.GridFS( yarrdb )

now = datetime.datetime.now() 
log_filename = now.strftime("logCh_%m%d_%H%M.txt")
log_file = open( log_filename, 'w' )

##### function #####
def input_v( message ) :
    answer = ""
    if args.fpython == 2 : answer = raw_input( message ) 
    if args.fpython == 3 : answer =     input( message )
    return answer

def update_mod(collection, query):
    yarrdb[collection].update(query, 
                                {'$set': { 'sys.rev'  : int(yarrdb[collection].find_one(query)['sys']['rev']+1), 
                                           'sys.mts'  : datetime.datetime.utcnow() }}, 
                                multi=True)

def update_ver(collection, query, ver):
    yarrdb[collection].update(query, 
                                {'$set': { 'dbVersion': ver }}, 
                                multi=True)

def is_png(b):
    return bool(re.match(br"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", b[:8]))

def is_pdf(b):
    return bool(re.match(b"^%PDF", b[:4]))

def get_user( doc ):
    if 'user_id' in doc:
        query = { '_id': ObjectId(doc['user_id']) }
        user = yarrdb.user.find_one( query )
        userName    = user['userName']
        institution = user['institution']
    elif 'userIdentity' in doc:
        userName    = doc.get('userIdentity')
        institution = doc.get('institution')
    else:
        userName    = 'Unknown'
        institution = 'Unknown'
    user_doc = { 'userName'    : userName,
                 'institution' : institution,
                 'userIdentity': 'default',
                 'userType'    : 'readWrite'
               }
    user = yarrdb.user.find_one( user_doc )
    user_id = ""
    if not user:
        time_now = datetime.datetime.utcnow()
        user_doc.update({ 'sys': {
                              'rev': 0,
                              'cts': time_now,
                              'mts': time_now },
                          'dbVersion': 2
                        })                       #UPDATE
        user_id = yarrdb.user.insert( user_doc ) #INSERT
        log_file.write( '[Insert] user doc: {}\n'.format(userName) )
        log_file.write( '         '  + str(user_id) + '\n' )
    else:
        user_id = user.get('_id')
    query = { '_id': user_id }
    user = yarrdb.user.find_one( query )

    return user

def insert_env( run, tr_id ):
    query = { '_id': ObjectId(tr_id) }
    thisRun = yarrdb.testRun.find_one( query )
    date = thisRun['startTime']
    cite = thisRun['cite']
    for env in run.get('environments', []):
        env_doc = env
        env_doc.update({ 'date': date, 'cite': cite })
        thisEnv = yarrdb.environment.find_one( env_doc )
        if thisEnv:
            env_id = thisEnv['_id']
        else:
            time_now = datetime.datetime.utcnow()
            env_doc.update({ 'date': date, 
                             'sys': {
                                 'rev': 0,
                                 'cts': time_now,
                                 'mts': time_now },
                             'dbVersion': 2
                           })                             #UPDATE
            env_id = yarrdb.environment.insert( env_doc ) #INSERT
            log_file.write( '[Insert] environment doc: {}\n'.format(env.get('key')) )

def update_testrun( run, user, plots ):
    tr_query = { '_id': ObjectId(run['testRun']) }
    thisRun = yarrdb.testRun.find_one( tr_query )

    tr_doc = { 'testType'    : thisRun['testType'],
               'runNumber'   : thisRun['runNumber'],
               'cite'        : user['institution'],
               'user_id'     : str(user['_id']) } 
    thisTestRun = yarrdb.testRun.find_one( tr_doc )
    if not thisTestRun:
        stage = run.get('stage', 'null')
        date = thisRun['date']
        time_now = datetime.datetime.utcnow()
        tr_doc.update({ 'sys': {
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
                        'ctrlCfg'     : '...',
                        'finishTime'  : date,
                        'plots'       : plots,
                        'display'     : thisRun.get('display',False),
                        'dbVersion'   : 2 })    #UPDATE
        tr_id = yarrdb.testRun.insert( tr_doc ) #INSERT
        log_file.write( '[Update] testRun doc: {0}\n'.format(thisRun['runNumber']) )
    else:
        tr_id = thisTestRun['_id']
        if len(plots) > thisTestRun['plots']:
            query = { '_id': tr_id }
            yarrdb.testRun.update( query,
                                   { '$set': { 'plots': plots }} ) #UPDATE
            log_file.write( '[Update] testRun doc: {0}\n'.format(thisRun['runNumber']) )

    if not thisRun.get('dbVersion','') == 2:
        rtr_id = yarrdb.testRun.remove( tr_query ) #REMOVE
        log_file.write( '[Remove] testRun doc: {0}\n'.format(thisRun['runNumber']) )

    return tr_id

def for_json( attachment, chipType, ctr_query ):
    code = attachment['code']
    contentType = attachment['contentType']
    json_name = ""
    json_data = json.loads( fs.get( ObjectId(code)).read() ) 
    chipId = ''
    if chipType in json_data:
        if chipType == "FE-I4B":
            chipId = json_data[chipType]['Parameter']['chipId']
        elif chipType == "RD53A":
            chipId = json_data[chipType]['Parameter']['ChipId']
    json_doc = { 'title'    : 'chipCfg',
                 'chipType' : chipType,
                 'filename' : '{}Cfg.json'.format(contentType),
                 'dataType' : 'default',
                 'data'     : json_data,
                 'dbVersion': 2 }
    thisJson = yarrdb.json.find_one( json_doc )
    if thisJson:
        json_id = thisJson['_id']
    else:
        json_id = yarrdb.json.insert( json_doc ) #INSERT
    yarrdb.componentTestRun.update( ctr_query,
                                    { '$set': { '{}Cfg'.format( contentType ): str(json_id) }} ) #UPDATE
    fs.delete( ObjectId(code) ) #REMOVE
    log_file.write( '\t\t\t\t[Insert] json doc: {}Cfg.json\n'.format(contentType) )

    return chipId

def for_dat( attachment, ctr_query ):
    code = attachment['code']
    dat_data = fs.get( ObjectId(code)).read() 
    dat_list = dat_data.split('\n')
    dat_line = 0
    dat_id = ""
    dat_name = ""
    data_doc = { 'type'      : dat_list[0][0:7],
                 'name'      : dat_list[1],
                 'xaxisTitle': dat_list[2],
                 'yaxisTitle': dat_list[3],
                 'zaxisTitle': dat_list[4],
                 'xbins'     : float(dat_list[5].split(' ')[0]),
                 'xlow'      : float(dat_list[5].split(' ')[1]),
                 'xhigh'     : float(dat_list[5].split(' ')[2]) }
    if dat_list[0][0:7] == 'Histo2d':
        data_doc.update({ 'ybins': float(dat_list[6].split(' ')[0]),
                          'ylow' : float(dat_list[6].split(' ')[1]),
                          'yhigh': float(dat_list[6].split(' ')[2]) })
        dat_line = 1
    elif dat_list[0][0:7] == 'Histo3d':
        data_doc.update({ 'ybins': float(dat_list[6].split(' ')[0]),
                          'ylow' : float(dat_list[6].split(' ')[1]),
                          'yhigh': float(dat_list[6].split(' ')[2]), 
                          'zbins': float(dat_list[7].split(' ')[0]),
                          'zlow' : float(dat_list[7].split(' ')[1]),
                          'zhigh': float(dat_list[7].split(' ')[2]) })
        dat_line = 2
    data_doc.update({ 'underflow': float(dat_list[6+dat_line].split(' ')[0]),
                      'overflow' : float(dat_list[6+dat_line].split(' ')[1]) })
    if len(dat_list) < 8+dat_line : 
        data_doc.update({ 'dat': [] })
    else:
        if dat_list[0][0:7] == 'Histo1d':
            dat = []
            for xbin in range(int(data_doc['xbins'])):
                dat.append(float(dat_list[7+dat_line].split(' ')[xbin]))
            data_doc.update({ 'dat': dat })
        elif dat_list[0][0:7] == 'Histo2d':
            dat = []
            for ybin in range(int(data_doc['ybins'])):
                in_dat = []
                for xbin in range(int(data_doc['xbins'])):
                    in_dat.append(float(dat_list[7+ybin+dat_line].split(' ')[xbin]))
                dat.append(in_dat)
            data_doc.update({ 'dat': dat })
        elif dat_list[0][0:7] == 'Histo3d':
            dat = []
            for ybin in range(int(data_doc['ybins'])):
                in_dat = []
                for xbin in range(int(data_doc['xbins'])):
                    for zbin in range(int(data_doc['zbins'])):
                        in_dat.append(float(dat_list[7+ybin+dat_line].split(' ')[xbin*data_doc['zbins']+zbin]))
                dat.append(in_dat)
            data_doc.update({ 'dat': dat })
        else:
            data_doc.update({ 'dat': [] })
    dat_doc = { 'filename' : '{}.dat'.format(data_doc['name']),
                'data'     : data_doc,
                'dbVersion': 2 }
    thisDat = yarrdb.dat.find_one( dat_doc )
    if thisDat:
        dat_id = thisDat['_id']
    else:
        dat_id = yarrdb.dat.insert( dat_doc ) #INSERT
    yarrdb.componentTestRun.update( ctr_query,
                                    { '$push': { 'attachments': { 'code': str(dat_id),
                                                                  'dateTime': datetime.datetime.utcnow(),
                                                                  'title': data_doc['name'], 
                                                                  'description': 'describe',
                                                                  'contentType': 'dat',
                                                                  'filename': '{}.dat'.format(data_doc['name']) }}}) #UPDATE
    fs.delete( ObjectId(code) ) #REMOVE
    dat_name = data_doc['name']
    log_file.write( '\t\t\t\t[Insert] dat doc: {}.dat\n'.format(data_doc['name']) )

    return dat_name

def for_image( attachment, name, plots, ctr_query, contentType ):
    code = attachment['code']
    filename = ""
    bin_data = fs.get( ObjectId( code )).read()
    filename = attachment['filename'][len(name)+1:]
    query = { '_id': ObjectId(code) }
    update_ver( 'fs.files', query, 2 ) #UPDATE
    query = { 'files_id': ObjectId(code) }
    update_ver( 'fs.chunks', query, 2 ) #UPDATE
    for plot in plots:
        if plot in attachment['filename']:
            filename = plot
    
    yarrdb.componentTestRun.update( ctr_query,
                                    { '$push': { 'attachments': { 'code'       : code,
                                                                  'dateTime'   : datetime.datetime.utcnow(),
                                                                  'title'      : filename, 
                                                                  'description': 'describe',
                                                                  'contentType': contentType,
                                                                  'filename'   : '{0}.{1}'.format(filename, contentType) }}}) #UPDATE
    log_file.write( '\t\t\t\t[Insert] grid doc: {0}.{1}\n'.format(filename, contentType) )

    return filename

def for_broken( attachment, ctr_query ):
    code = attachment['code']
    yarrdb.componentTestRun.update( ctr_query,
                                    { '$push': { 'broken' : { 
                                                    'key'        : attachment['filename'],
                                                    'code'       : code,
                                                    'contentType': attachment['contentType'] }}}) #UPDATE
    query = { '_id': ObjectId(code) }
    update_ver( 'fs.files', query, 1 ) #UPDATE
    query = { 'files_id': ObjectId(code) }
    update_ver( 'fs.chunks', query, 1 ) #UPDATE
    log_file.write( '\t\t\t\t[Broken] grid doc: {0}.{1}\n'.format(attachment['filename'], attachment['contentType']) )
    
    return True

#################################################################
# Main function
start_time         = datetime.datetime.now() 
start_copy_time    = ""
finish_copy_time   = ""
start_update_time  = ""
finish_update_time = ""

# restore from backup database
answer = ""
while answer == "" :
    answer = input_v( '# Do you make it back to the originl DB : {0}_copy ---> {1} ? (y/n) > '.format( args.db, args.db ) )
if answer == 'y' :
    print( '\t# Restoring ...' )
    start_copy_time = datetime.datetime.now() 
    log_file.write( '[Remove] database: {}\n'.format(args.db) )
    client.drop_database( args.db )
    log_file.write( '[Restore] database: {0}_copy ---> database: {1}\n'.format(args.db, args.db) )
    client.admin.command( 'copydb',
                          fromdb='{}_copy'.format( args.db ),
                          todb='{}'.format( args.db ) )#COPY 
    finish_copy_time = datetime.datetime.now() 
    client.drop_database( '{}_copy'.format(args.db) )
    print( '\t# Succeeded to Restore.' )
print( ' ' )

# convert database scheme
answer = ""
while answer == "" :
    answer = input_v( '# Do you convert db scheme : {0}(old) ---> {1}(new) ? (y/n) > '.format( args.db, args.db ) )
if not answer == 'y' :
    finish_time = datetime.datetime.now()
    log_file.write( '\n==== Operation Time ====\n' )
    log_file.write( start_time.strftime( 'start:  %M:%S:%f' ) + '\n' )
    log_file.write( finish_time.strftime( 'finish: %M:%S:%f' ) + '\n' )
    total_time = datetime.timedelta(seconds=(finish_time-start_time).total_seconds())
    log_file.write( 'Total:  ' + str(total_time) + '\n' )
    if not start_copy_time == "":
        log_file.write( '\n' + start_copy_time.strftime( 'copy start:  %M:%S:%f' ) + '\n' )
        log_file.write( finish_copy_time.strftime( 'copy finish: %M:%S:%f' ) + '\n' )
        total_copy_time = datetime.timedelta(seconds=(finish_copy_time-start_copy_time).total_seconds())
        log_file.write( 'Copy total:  ' + str(total_copy_time) + '\n' )
    log_file.write( '========================' )
    print(" ")
    print("# Exit ...")
    sys.exit()     
print( ' ' )

# copy database for buckup
start_copy_time = ""
print( '# Copy database to "{}_copy" for replica'.format(args.db) )
cursor = client.list_databases()
copy_db='{}_copy'.format(args.db)
if copy_db in [db.get("name","") for db in cursor]:
    print( '\t# Already been replicated.' )
else:
    print( '\t# Replicating ...' )
    start_copy_time = datetime.datetime.now() 
    client.admin.command( 'copydb',
                          fromdb=args.db,
                          todb='{}_copy'.format(args.db)) #COPY
    finish_copy_time = datetime.datetime.now() 
    print( '\t# Succeeded to replicate.' )
print( ' ' )

# modify module document
print( '# Convert database scheme: {}'.format(args.db) )
print( '\t# Converting ...' )

start_update_time = datetime.datetime.now() 

query = { 'componentType' : 'Module',
          'dbVersion'     : { '$ne': 2 } }
module_entries = yarrdb.component.find( query )
moduleid_entries = []
for module in module_entries:
    moduleid_entries.append( str(module['_id']) )
    
#for module in module_entries:
for moduleid in moduleid_entries:
    query = { '_id': ObjectId(moduleid) }
    module = yarrdb.component.find_one( query )

    mo_serialNumber = module['serialNumber']
    mo_query = { '_id': module['_id'] }

    log_file.write( '\n==============================================\n' )
    log_file.write( '[Start] Module: {}\n'.format( module['serialNumber'] ) )
    log_file.write( '----------------------------------------------\n' )

    query = { 'component': str(module['_id']),
              'dbVersion': { '$ne': 2 } }
    run_entries = yarrdb.componentTestRun.find( query )
    runid_entries = []
    for run in run_entries:
        runid_entries.append( str(run['_id']) )
    for runid in runid_entries:
        query = { '_id': ObjectId(runid) }
        run = yarrdb.componentTestRun.find_one( query )
        ctr_query = { '_id': run['_id'] }
        log_file.write( '\nComponentTestRun: {0}-{1}\n'.format( mo_serialNumber, run['runNumber'] ) )
        tr_query = { '_id': ObjectId(run['testRun']) }
        thisRun = yarrdb.testRun.find_one( tr_query )
        user = get_user( thisRun ) #user

        ### attachments
        attachments = thisRun.get('attachments',[])
        plots = []
        maybe_broken = False
        log_file.write( '\t\tAttachments:\n' )
        for attachment in attachments:
            code = attachment.get('code')
            bin_data =  fs.get( ObjectId(code) ).read()
            if is_png( bin_data ):
                try:
                    image_name = for_image( attachment, mo_serialNumber, plots, ctr_query, 'png' )
                    plots.append( image_name )
                except:
                    maybe_broken = for_broken( attachment, ctr_query )
            elif is_pdf( bin_data ):
                try:
                    image_name = for_image( attachment, mo_serialNumber, plots, ctr_query, 'pdf' )
                    plots.append( image_name )
                except:
                    maybe_broken = for_broken( attachment, ctr_query )
            elif 'Histo' in bin_data.split('\n')[0][0:7]:
                try:
                    dat_name = for_dat( attachment, ctr_query )
                    plots.append( dat_name )
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
        tr_id = update_testrun( run, user, plots )

        ### environment
        insert_env( run, str(tr_id) )

        yarrdb.componentTestRun.update( ctr_query,
                                        { '$set': { 'tx'       : -1,
                                                    'rx'       : -1,
                                                    'testRun'  : str(tr_id) }})
        yarrdb.componentTestRun.update( ctr_query,
                                        { '$unset': { 'stage': '',
                                                      'environments': '' }} ) #UPDATE
        update_ver( 'componentTestRun', ctr_query, 2 )
        update_mod( 'componentTestRun', ctr_query ) #UPDATE

        if (maybe_broken):
            log_file.write( '\t\t\t\t[Broken] change db version -> 1\n' )
            update_ver( 'componentTestRun', ctr_query, 1 )
        log_file.write( '[Update] componentTestRun doc: {0} - {1}\n'.format(mo_serialNumber, thisRun['runNumber']) )

    # modify chip documents
    query = { 'parent': str(module['_id']) }
    child_entries = yarrdb.childParentRelation.find( query )
    childid_entries = []
    for child in child_entries:
        childid_entries.append( str(child['_id']) )
    for childid in childid_entries:
        query = { '_id': ObjectId(childid) }
        child = yarrdb.childParentRelation.find_one( query )
        ch_query = { '_id': ObjectId(child['child']) }
        chip = yarrdb.component.find_one( ch_query )
        log_file.write( '\n----------------------------------------------\n' )
        log_file.write( 'Chip: {}\n'.format( chip['serialNumber'] ) )
        log_file.write( '----------------------------------------------\n' )

        chipType = chip['componentType']
        chipName = chip['name']
        chipId = ''

        ### componentTestRun (chip)
        query = { 'component': str(chip['_id']),
                  'dbVersion': { '$ne': 2 } }
        run_entries = yarrdb.componentTestRun.find( query )
        runid_entries = []
        for run in run_entries:
            runid_entries.append( str(run['_id']) )
        for runid in runid_entries:
            query = { '_id': ObjectId(runid) }
            run = yarrdb.componentTestRun.find_one( query )
            ctr_query = { '_id': run['_id'] }
            log_file.write( '\nComponentTestRun: {0}-{1}\n'.format( chip['serialNumber'], run['runNumber'] ) )
            tr_query = { '_id': ObjectId(run['testRun']) }
            thisRun = yarrdb.testRun.find_one( tr_query )
            user = get_user( thisRun ) #user

            ### attachments
            attachments = thisRun.get('attachments',[])
            plots = []
            maybe_broken = False
            log_file.write( '\t\tAttachments:\n' )
            for attachment in attachments:
                code = attachment.get('code')
                bin_data =  fs.get( ObjectId(code) ).read()
                if is_png( bin_data ):
                    try:
                        image_name = for_image( attachment, chipName, plots, ctr_query, 'png' )
                        plots.append( image_name )
                    except:
                        maybe_broken = for_broken( attachment, ctr_query )
                elif is_pdf( bin_data ):
                    try:
                        image_name = for_image( attachment, chipName, plots, ctr_query, 'pdf' )
                        plots.append( image_name )
                    except:
                        maybe_broken = for_broken( attachment, ctr_query )
                elif 'Histo' in bin_data.split('\n')[0][0:7]:
                    try:
                        dat_name = for_dat( attachment, ctr_query )
                        plots.append( dat_name )
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
            tr_id = update_testrun( run, user, plots ) #UPDATE

            ### environment 
            insert_env( run, str(tr_id) )              #UPDATE

            yarrdb.componentTestRun.update( ctr_query,
                                            { '$set': { 'tx'       : -1,
                                                        'rx'       : -1,
                                                        'testRun'  : str(tr_id) }}) #UPDATE
            yarrdb.componentTestRun.update( ctr_query,
                                            { '$unset': { 'stage': '',
                                                          'environments': '' }} )   #UPDATE
            update_ver( 'componentTestRun', ctr_query, 2 ) #UPDATE
            update_mod( 'componentTestRun', ctr_query )    #UPDATE

            if (maybe_broken):
                log_file.write( '[Broken] change db version -> 1\n' )
                update_ver( 'componentTestRun', ctr_query, 1 ) #UPDATE
            log_file.write( '[Update] componentTestRun doc: {0} - {1}\n'.format(chip['serialNumber'], thisRun['runNumber']) )

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
                               'dbVersion': 2 }
                mo_ctr_id = yarrdb.componentTestRun.insert( mo_ctr_doc ) #INSERT
                log_file.write( '[Insert] componentTestRun doc: {0} - {1}\n'.format(mo_serialNumber, thisRun['runNumber']) )

        if chipId == '':
            if 'chipId' in chipName:
                chipId = int(chipName[chipName.find('chipId')+6])
            else:
                if chipType == "FE-I4B":
                    chipId = 1
                elif chipType == "RD53A":
                    chipId = 0

        ### component (chip)
        user = get_user( chip ) #user
        yarrdb.component.update( ch_query,
                                 { '$set': { 'cite'         : user['institution'],
                                             'user_id'      : str(user['_id']),
                                             'componentType': 'Front-end Chip',
                                             'chipType'     : chipType,
                                             'chipId'       : int(chipId) }} ) #UPDATE
        yarrdb.component.update( ch_query,
                                 { '$unset': { 'institution' : '',
                                               'userIdentity': '' }} )         #UPDATE

        update_ver( 'component', ch_query, 2 )
        update_mod( 'component', ch_query ) #UPDATE
        log_file.write( '\n[Update] chip doc: {0}\n'.format(chip['serialNumber']) )

        ### childParentRelation
        cpr_query = { '_id': child['_id'] }
        cpr_id = yarrdb.childParentRelation.find_one( cpr_query )['_id']
        update_ver( 'childParentRelation', cpr_query, 2 ) #UPDATE
        update_mod( 'childParentRelation', cpr_query )    #UPDATE
        log_file.write( '\n[Update] cpr doc: {0}\n'.format(chip['serialNumber']) )

        log_file.write( '----------------------------------------------\n' )

    ### component (module)
    user = get_user( module ) #user
    yarrdb.component.update( mo_query,
                             { '$set': { 'cite'    : user['institution'],
                                         'chipType': chipType,
                                         'user_id' : str(user['_id']) }} ) #UPDATE
    yarrdb.component.update( mo_query,
                             { '$unset': { 'institution' : '',
                                           'userIdentity': '' }} )          #UPDATE

    update_ver( 'component', mo_query, 2 ) #UPDATE
    update_mod( 'component', mo_query )    #UPDATE
    log_file.write( '[Update] module doc: {}\n'.format(mo_serialNumber) )
    log_file.write( '\n[Finish] Module: {}\n'.format( mo_serialNumber ) )
    now_time = datetime.datetime.now()
    log_file.write( now_time.strftime( '[Time] %M:%S:%f' ) + '\n' )
    log_file.write( '==============================================\n' )
    time.sleep( 2 )

finish_update_time = datetime.datetime.now() 
print( '\t# Succeeded to convert.' )
print( '# Finish.' )

finish_time = datetime.datetime.now()
log_file.write( '\n==== Operation Time ====\n' )
log_file.write( start_time.strftime( 'start:  %M:%S:%f' ) + '\n' )
log_file.write( finish_time.strftime( 'finish: %M:%S:%f' ) + '\n' )
total_time = datetime.timedelta(seconds=(finish_time-start_time).total_seconds())
log_file.write( 'Total:  ' + str(total_time) + '\n' )
if not start_copy_time == "":
    log_file.write( '\n' + start_copy_time.strftime( 'copy start:  %M:%S:%f' ) + '\n' )
    log_file.write( finish_copy_time.strftime( 'copy finish: %M:%S:%f' ) + '\n' )
    total_copy_time = datetime.timedelta(seconds=(finish_copy_time-start_copy_time).total_seconds())
    log_file.write( 'Copy total:  ' + str(total_copy_time) + '\n' )
if not start_update_time == "":
    log_file.write( '\n' + start_update_time.strftime( 'update start:  %M:%S:%f' ) + '\n' )
    log_file.write( finish_update_time.strftime( 'update finish: %M:%S:%f' ) + '\n' )
    total_update_time = datetime.timedelta(seconds=(finish_update_time-start_update_time).total_seconds())
    log_file.write( 'Update total:  ' + str(total_update_time) + '\n' )
log_file.write( '========================' )

log_file.close()

print( '# Log file: {}.'.format(log_filename) )
