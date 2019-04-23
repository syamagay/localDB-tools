"""
script for confirmation database scheme
log file ---> log/loConvert_%m%d_%H%M.txt
"""

### Import 
import os, sys, datetime, json, re
import gridfs # gridfs system 
from   pymongo       import MongoClient, ASCENDING # use mongodb scheme
from   bson.objectid import ObjectId               # handle bson format
sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) )
sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) + '/src' )
from   arguments import *   # Pass command line arguments into app.py

### Set database
args = getArgs()         
if args.username : url = 'mongodb://' + args.username + ':' + args.password + '@' + args.host + ':' + str(args.port) 
else :             url = 'mongodb://'                                             + args.host + ':' + str(args.port) 
client = MongoClient( url )
yarrdb = client[args.db]
copydb = client['{}_copy'.format(args.db)]
fs = gridfs.GridFS( yarrdb )
dbv = args.version

### Set log file
log_dir = './log'
if not os.path.isdir(log_dir): os.mkdir(log_dir)
now = datetime.datetime.now() 
log_filename = now.strftime("{}/logConfirm_%m%d_%H%M.txt".format(log_dir))
log_file = open( log_filename, 'w' )

# Set database.json
home = os.environ['HOME']
filepath = '{}/.yarr/database.json'.format(home)
with open(filepath, 'r') as f: file_json = json.load(f)
file_stages = file_json.get('stage', [])
file_dcs = file_json.get('environment', [])
if file_stages == [] or file_dcs == []:
    print( '# There is no database config: {}'.format(filepath) )
    print( '# Prepare the config file by running dbLogin.sh in YARR SW' )
    sys.exit()

#################################################################
#################################################################

### Function 
def set_time(date):
    DIFF_FROM_UTC = args.timezone 
    time = (date+datetime.timedelta(hours=DIFF_FROM_UTC)).strftime('%Y/%m/%d %H:%M:%S')
    return time

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

def input_number( message, len_list ):
    final_num = ''
    while final_num == '' :
        num = ''
        while num == '' :
            num = input_v( message ) 
        if not num.isdigit() : 
            print( '[WARNING] Input item is not number, enter agein. ')
        elif not int(num) < len_list : 
            print( '[WARNING] Input number is not included in the list, enter agein. ')
        else :
            final_num = int(num)
    return final_num

def write_log( text ):
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S {}\n'.format(text) ) )

def update_mod(collection, query):
    yarrdb[collection].update(query, 
        { '$set': { 
              'sys.rev'  : int(yarrdb[collection].find_one(query)['sys']['rev']+1), 
              'sys.mts'  : datetime.datetime.utcnow() }
        }, 
        multi=True
    )
def update_ver(collection, query, ver):
    yarrdb[collection].update(query, 
        { '$set': { 'dbVersion': ver }}, 
        multi=True
    )

def is_png(b):
    return bool(re.match(br"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", b[:8]))

def is_pdf(b):
    return bool(re.match(b"^%PDF", b[:4]))

##################################################################
##################################################################

### Main function
start_time         = datetime.datetime.now() 
start_update_time  = ''
finish_update_time = ''
#log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start] confirmDB.py \n' ) )
write_log( '[Start] confirmDB.py' ) 

# convert database scheme
print( '# Conversion flow' )
print( '\t1. Replicate : python copyDB.py    : {0}      ---> {1}_copy'.format( args.db, args.db ) )
print( '\t2. Convert   : python convertDB.py : {0}(old) ---> {1}(new)'.format( args.db, args.db ) )
print( '\t3. Confirm   : python confirmDB.py : {0}(new) ---> {1}(confirmed)'.format( args.db, args.db ) )
print( '\t\t1. module data' )
print( '\t\t2. stage name' )
print( '\t\t3. environment key' )
print( '\t\t4. file data' )
print( '\t\t5. chip data' )
print( '\t\t6. check all data' )
print( ' ' )
print( '# This is the stage of step3. Confirm' )
print( '# It must be run after step2. Convert' )
print( ' ' )
query = { 'dbVersion': dbv }
if yarrdb.component.find( query ).count() == 0:
    print( '# There are no component with "dbVersion: {0}" in DB : {1}.'.format(dbv, args.db) )
    print( '# Conversion might not have been finished.' )
    print( '# Run "python convert.py --config ../../conf.yml" to convert the scheme of DB.' )
    print( ' ' )
    print( '# Exit ... ' )
    sys.exit()
answer = input_answer( '# Do you confirm new db? (y/n) > ' )
if answer == 'y' :
    #############
    ### Component
    print( '# Confirm the component data ...' )
    print( ' ' )
    write_log( '================================================================' )
    write_log( '[Confirmation] component' )
    write_log( '[Start]' )
    query = { 'componentType': { '$ne':'Module' } }
    chip_entries = yarrdb.component.find( query )
    chipIds = []
    for chip in chip_entries:
        chipIds.append( str(chip['_id']) )
    for chipId in chipIds:
        query = { 'child': chipId }
        child_entries = yarrdb.childParentRelation.find( query )
        if child_entries.count() > 1:
            parents = []
            for cpr in child_entries:
                query = { '_id': ObjectId(cpr['parent']) }
                thisModule = yarrdb.component.find_one( query )
                parents.append({ 'serialNumber': thisModule['serialNumber'], 'children': thisModule['children'], '_id': cpr['parent'] })
            final_answer = ''
            while final_answer == '':
                query = { '_id': ObjectId(chipId) }
                thisChip = yarrdb.component.find_one( query )
                print( '# The chip {} has more than one parent module'.format(thisChip['serialNumber']) )
                print( '# Select one from the list.' )
                print( ' ' )
                print( '----- parent list -----' )
                for parent in parents:
                    print( '{0:^3} : {1:^10} (children: {2:^4})'.format( parents.index(parent), parent['serialNumber'], parent['children'] ) )
                print( '{0:^3}'.format(len(parents)) + ' : unknown ---> skip to select this module' )
                print(' ')
                parent_num = input_number( '# Enter module number >> ', len(parents)+1 )
                print(' ')
                # Confirmation before convert
                print( '{:^46}'.format( '###### Confirmation before the convert ######' ) )
                print( '{:^46}'.format( '---------------------------------------------' ) )
                for parent in parents:
                    txt = ''
                    if parent_num == len(parents):                txt = 'skip'
                    elif not parents.index(parent) == parent_num: txt = 'delete'
                    else:                                         txt = 'select'
                    print( '{0:^3} : {1:^10} (children: {2:^4}) ---> {3:^8}'.format( parents.index(parent), parent['serialNumber'], parent['children'], txt ) )
                print( ' ' )
                answer = input_answer( '# Do you continue to convert for changing DB scheme? (y/n) > ' )
                if answer == 'y':
                    final_answer = 'y'
                else:
                    print( '# Check again.' ) 
                    print( ' ' )
            if answer == 'y' : 
                if parent_num == len(parents): continue
                print( '# Start the convert...' )
                # Conversion
                write_log( '\t\t[Convert]' )
                write_log( '\t\t[Start]' )
                parent_id = parents[parent_num]['_id']
                for parent in parents:
                    if not parents.index(parent) == parent_num:
                        query = { 'component': parent['_id'] }
                        run_entries = yarrdb.componentTestRun.find( query )
                        for run in run_entries:
                            query = { 'component': parent_id, 'testRun': run['testRun'] }
                            if not yarrdb.componentTestRun.find( query ):
                                query = { '_id': run['_id'] }
                                yarrdb.componentTestRun.update( query, 
                                                                { '$set': { 'component': parent_id } }) #UPDATE
                                update_mod( 'componentTestRun', query ) #UPDATE
                                write_log( '\t\t[Update] {0:<7}: {1:<20} -> {2:<20}'.format(run['runNumber'], parent['serialNumber'], parents[parent_num]['serialNumber']) )
                            else:
                                if 'attachments' in run:
                                    query = { '_id': run['_id'] }
                                    yarrdb.componentTestRun.update( query, 
                                                                    { '$set': { 'component': parent_id } }) #UPDATE
                                    update_mod( 'componentTestRun', query ) #UPDATE
                                    write_log( '\t\t[Update] {0:<7}: {1:<20} -> {2:<20}'.format(run['runNumber'], parent['serialNumber'], parents[parent_num]['serialNumber']) )
                                else:
                                    query = { '_id': run['_id'] }
                                    yarrdb.componentTestRun.remove( query )
                                    write_log( '\t\t[Remove] {0:<7}: {1:<20}'.format(run['runNumber'], parent['serialNumber']) ) 
                        query = { 'parent': parent['_id'] }
                        child_entries = yarrdb.childParentRelation.find( query )
                        for child in child_entries:
                            query = { '_id': ObjectId(child['child']) }
                            thisChip = yarrdb.component.find_one( query )
                            query = { 'parent': parent_id, 'child': child['child'] }
                            if yarrdb.childParentRelation.find_one( query ):
                                query = { '_id': child['_id'] }
                                yarrdb.childParentRelation.remove( query )
                                write_log( '\t\t[Remove] {0:<20} - {1:<20}'.format( thisChip['serialNumber'], parent['serialNumber']) )
                            else:
                                query = { '_id': child['_id'] }
                                yarrdb.childParentRelation.update( query,
                                                                   { '$set': { 'parent': parent_id }})
                                write_log( '\t\t[Update] {0:<20} - {1:<20} -> {2:<20}'.format(thisChip['serialNumber'], parent['serialNumber'], parents[parent_num]['serialNumber']) ) 
                        query = { '_id': ObjectId(parent['_id']) }
                        yarrdb.component.remove( query ) 
                        write_log( '\t\t[Remove] {0:<20}'.format(parent['serialNumber']) ) 

                query = { 'parent': parent_id }
                yarrdb.childParentRelation.update( query,
                                                   { '$set': { 'status': 'active' }},
                                                   multi=True )
                update_ver( 'childParentRelation', query, dbv ) #UPDATE
                update_mod( 'childParentRelation', query ) #UPDATE
                write_log( '\t\t[Update] {0:<20} - {1:<20}'.format(thisChip['serialNumber'], parents[parent_num]['serialNumber']) ) 
                children = yarrdb.childParentRelation.find( query ).count()
                query = { '_id': ObjectId(parent_id) } 
                thisModule = yarrdb.component.find_one( query )
                if not thisModule['children'] == children:
                    yarrdb.component.update( query,
                                             { '$set': { 'children': children }} )
                update_ver( 'component', query, dbv ) #UPDATE
                update_mod( 'component', query ) #UPDATE
                write_log( '\t\t[Update] {0:<20}'.format(parents[parent_num]['serialNumber']) ) 
                write_log( '\t\t[Finish]' ) 
                print( '# Done.' )
                print( ' ' )
        if child_entries.count() == 0:
            query = { '_id': ObjectId(chipId) }
            thisChip = yarrdb.component.find_one( query )
            query = { '_id': ObjectId(chipId) }
            yarrdb.component.remove( query )
            write_log( '[Not found/Delete] relational documents (run/cpr): {}'.format( thisChip['serialNumber'] )  ) 
    query = { 'componentType': 'Module' }
    module_entries = yarrdb.component.find( query )
    moduleIds = []
    for module in module_entries:
        moduleIds.append( str(module['_id']) )
    for moduleId in moduleIds:
        query = { 'parent': moduleId }
        child_entries = yarrdb.childParentRelation.find( query )
        print( child_entries.count() )
        if child_entries.count() == 0:
            query = { '_id': ObjectId(moduleId) }
            thisModule = yarrdb.component.find_one( query )
            query = { '_id': ObjectId(moduleId) }
            yarrdb.component.remove( query )
            write_log( '[Not found/Delete] relational documents (run/cpr): {}'.format( thisModule['serialNumber'] ) ) 
    write_log( '[Finish]' )
    print( '# Finish' )
    print( ' ' )

    #########
    ### stage
    print( '# Confirm the stage name ...' )
    print( ' ' )
    write_log( '================================================================' )
    write_log( '[Confirmation] stage' )
    write_log( '[Start]' )
    runs = yarrdb.testRun.find()
    runIds = []
    for run in runs:
        runIds.append(str(run['_id']))
    stages = {}
    for runId in runIds:
        query = { '_id': ObjectId(runId) }
        thisRun = yarrdb.testRun.find_one( query )
        stage = thisRun.get('stage', 'null')
        if stage in file_stages: continue
        write_log( '\t\t{0:^7}: {1:^20}'.format(thisRun['runNumber'], stage) )
        if not stage in stages:
            stages.update({ stage: {} })
        query = { 'testRun': runId }
        component_entries = yarrdb.componentTestRun.find( query )
        for component in component_entries:
            query = { 'componentType': 'Module', '_id': ObjectId(component['component']) }
            thisComponent = yarrdb.component.find_one( query )
            if thisComponent:
                if not thisComponent['serialNumber'] in stages[stage]:
                    stages[stage].update({ thisComponent['serialNumber']: { 'first': thisRun['startTime'], 'last': thisRun['startTime'] }})
                else:
                    if thisRun['startTime'] > stages[stage][thisComponent['serialNumber']]['last']: stages[stage][thisComponent['serialNumber']]['last'] = thisRun['startTime']
                    if thisRun['startTime'] < stages[stage][thisComponent['serialNumber']]['first']: stages[stage][thisComponent['serialNumber']]['first'] = thisRun['startTime']
    if not stages == {}:
        final_answer = ''
        stages_copy = stages.copy() 
        while final_answer == '':
            # Confirm the stage name
            stages = stages_copy.copy()
            for stage in stages:
                if stage in file_stages: continue
                print( '#########################################' )
                print( '###        {0:^19}        ###'.format(stage) )
                print( '#########################################' )
                print( '  {0:^11} : {1:^10} - {2:^10}  '.format( 'Module', 'from', 'to' ) )
                print( '-----------------------------------------' )
                for component in stages[stage]:
                    print( '  {0:^11} : {1:^10} - {2:^10}  '.format( component, stages[stage][component]['first'].strftime('%Y.%m.%d'), stages[stage][component]['last'].strftime('%Y.%m.%d') ) )
                print( '-----------------------------------------' )
                print( ' ' )
                print( '# This stage name is not written in {0}'.format(filepath) ) 
                print( '# Then, it must be changed to the name in following list. (The stage name registered before is recorded as comment.' )
                print( '# Select the stage from the list after checking data (ref {})'.format(log_filename) )
                print( ' ' )
                print( '----- stage list -----' )
                for file_stage in file_stages:
                    print( ' {0:<3}'.format(file_stages.index(file_stage)) + ' : ' + file_stage )
                print( ' {0:<3}'.format(len(file_stages)) + ' : unknown ---> skip to convert this stage name' )
                print(' ')
                stage_num = input_number( '# Enter stage number >> ', len(file_stages)+1 )
                if stage_num == len(file_stages): stages[stage] = 'unknown'
                else:                             stages[stage] = file_stages[stage_num] 
                print(' ')
    
            # Confirmation before convert
            print( '{:^46}'.format( '###### Confirmation before the convert ######' ) )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            print( '{0:^20} ---> {1:^20}'.format( 'before the convert', 'after the convert' ) )
            for stage in stages:
                if stages[stage] == 'unknown':
                    print( '{0:^20} ---> {1:^20}'.format( stage, stage + ' (no convert)' ) )
                else:
                    print( '{0:^20} ---> {1:^20}'.format( stage, stages[stage] ) )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            print( ' ' )
            answer = input_answer( '# Do you continue to convert their names for changing DB scheme? (y/n) > ' )
            if answer == 'y':
                final_answer = 'y'
            else:
                print( '# Check again.' ) 
                print( ' ' )
        if answer == 'y' : 
            print( '# Start the convert...' )
            # Conversion
            write_log( '\t\t[Convert]' )
            write_log( '\t\t[Start]' )
            for runId in runIds:
                query = { '_id': ObjectId(runId) }
                thisRun = yarrdb.testRun.find_one( query )
                stage = thisRun.get('stage', 'null')
                if stage in file_stages: continue
                if stages[stage] == 'unknown': continue
                user = thisRun['user_id']
                yarrdb.testRun.update( query, { '$push': { 'comments': { 'user_id': user, 'comment': 'The stage neme registered before is "{}"'.format(stage) }}})

                yarrdb.testRun.update( query,
                                                { '$set': { 'stage': stages[stage] }}) #UPDATE
                update_mod( 'testRun', query ) #UPDATE
                write_log( '\t\t[Update] {0:<7}: {1:<20} -> {2:<20}'.format(thisRun['runNumber'], stage, stages[stage]) ) 
            write_log( '\t\t[Finish]' ) 
            # Confirmation after convert
            mistake = False
            write_log( '\t\t[Confirmation] after convert' )
            write_log( '\t\t[Start]' ) 
            for runId in runIds:
                query = { '_id': ObjectId(runId) }
                thisRun = yarrdb.testRun.find_one( query )
                stage = thisRun.get('stage','null')
                if stage in file_stages: continue
                write_log( '\t\t\t\t{0:^7}: {1:^20}'.format(thisRun['runNumber'], stage) )
                mistake=True
    
            if not mistake:
                print( '# Complete the convert of the stage name.' )
                write_log( '\t\t[Finish]' )
                write_log( '\t\t[Success] complete the convert of the stage name.' )
            else:
                print( '# There are still unregistered stage name, check log file: {}.'.format(log_filename) )
                write_log( '\t\t[Finish]' )
                write_log( '\t\t[Failure] There are still unregistered stage name.' )
    else:
        write_log( '[Finish]' )
        write_log( '[Success] complete the convert of the stage name.' )
    print( '# Finish' )
    print( ' ' )

    #############
    # environment
    print( '# Confirm the environmental key ...' )
    print( ' ' )
    mistake = False
    keys = {}
    write_log( '================================================================' )
    write_log( '[Confirmation] environment' )
    write_log( '[Start]' ) 
    
    environments = yarrdb.environment.find()
    envIds = []
    for env in environments:
        envIds.append(str(env['_id']))
    # Check the environmental key registered in environment document
    keys = {}
    for envId in envIds:
        env_query = { '_id': ObjectId(envId),
                      'type': 'data' }
        cut_query = { 'sys': 0, 'type': 0, 'dbVersion': 0, '_id': 0 }
        thisEnv = yarrdb.environment.find_one( env_query, cut_query )
        query = { 'environment': envId }
        thisRun = yarrdb.testRun.find_one( query )
        for env_key in thisEnv:
            for data in thisEnv[env_key]:
                description = data.get('description', 'null')
                if description == 'null':
                    print( '######################################' )
                    print( '### {0:^7} : {0:^20} ###'.format(env_key) )
                    print( '######################################' )
                    print( ' ' )
                    print( '# The key does not have description.' ) 
                    print( '# Fill the description of this environmental key after checking data (ref {}), or "n" if unknown key'.format(log_filename) )
                    print( '# e.g.) Low Voltage [V]' )
                    print( ' ' )
                    answer = input_answer( '# Write description (unknown ---> enter "n") >> ' )
                    if answer == 'n':
                        print( '# Skipped' )
                        print( ' ' )
                        continue
                    description = answer
                    yarrdb.environment.update( env_query,
                                               { '$set': { '{0}.0.description'.format(env_key): description }})
                    update_mod( 'environment', env_query ) #UPDATE
                    write_log( '\t\t[Update] {0:<7}: {1:<20} {2:<23}'.format(thisRun['runNumber'], env_key, description) ) 
                    print( '# Added description "{0}" to {1}'.format( description, env_key ) )
                    print( ' ' )
                if env_key in file_dcs: continue
                write_log( '\t\t{0:^7}: {1:^20}({2:^20})'.format(thisRun['runNumber'], env_key, description) )
                if not env_key in keys:
                    keys.update({ env_key: description })
    if not keys == {}:  
        keys_copy = keys.copy()
        final_answer = ''
        while final_answer == '':
            # Confirm the environmental key name
            keys = keys_copy.copy()
            for key in keys:
                if key in file_dcs: continue
                print( '#############################################################' )
                print( '### {0:^20} : {1:^30} ###'.format(key, keys[key]) )
                print( '#############################################################' )
                print( ' ' )
                print( '# This key is not written in {0}'.format(filepath) ) 
                print( '# Then, it must be changed to the name in following list. (The key name registered before is recorded as comment.)' )
                print( '# Select the environmental key from the list after checking data (ref {})'.format(log_filename) )
                print( ' ' )
                print( '----- key list -----' )
                for file_env in file_dcs:
                    print( ' {0:<3}'.format(file_dcs.index(file_env)) + ' : ' + file_env )
                print( ' {0:<3}'.format(len(file_dcs)) + ' : unknown ---> skip to convert this stage name' )
                print(' ')
                env_num = input_number( '# Enter key number >> ', len(file_dcs)+1 )
                if env_num == len(file_dcs): keys[key] = 'unknown'
                else:                        keys[key] = file_dcs[env_num] 
                print( ' ' )
            # Confirmation before convert
            print( '{:^46}'.format( '###### Confirmation before the convert ######' ) )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            print( '{0:^20} ---> {1:^20}'.format( 'before the convert', 'after the convert' ) )
            for key in keys:
                if keys[key] == 'unknown':
                    print( '{0:^20} ---> {1:^20}'.format( key, key + 'no convert' ) )
                else:
                    print( '{0:^20} ---> {1:^20}'.format( key, keys[key] ) )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            print( ' ' )
            answer = input_answer( '# Do you continue to convert their key names for changing DB scheme? (y/n) > ' )
            if answer == 'y':
                final_answer = 'y'
            else:
                print( '# Check again.' )
                print( ' ' )
        if answer == 'y' : 
            print( '# Start the convert...' )
            print( ' ' )
            # Conversion
            write_log( '\t\t[Convert]' )
            write_log( '\t\t[Start]' )
            for envId in envIds:
                env_query = { '_id': ObjectId(envId),
                          'type': 'data' }
                cut_query = { 'sys': 0, 'type': 0, 'dbVersion': 0, '_id': 0 }
                thisEnv = yarrdb.environment.find_one( env_query, cut_query )
                for env_key in thisEnv:
                    if env_key in file_dcs: continue
                    if keys[env_key] == 'unknown': continue
                    env_dict = thisEnv[env_key][0]
                    yarrdb.environment.update( env_query,
                                               { '$push': { keys[env_key]: env_dict }})
                    yarrdb.environment.update( env_query,
                                               { '$unset': { env_key: '' }})
                    query = { 'environment': envId }
                    yarrdb.testRun.update( query, { '$push': { 'comments': { 'user_id': user, 'comment': 'The environmental key registered before is "{}"'.format(env_key) }}})

                    update_mod( 'environment', env_query ) #UPDATE
                    write_log( '\t\t[Update] {0:<7}: {1:<20} -> {2:<20}'.format(thisRun['runNumber'], env_key, keys[env_key]) )
            mistake = False
            write_log( '\t\t[Finish]' )
            write_log( '\t\t[Confirmation] after convert' )
            write_log( '\t\t[Start]' ) 
            for envId in envIds:
                env_query = { '_id': ObjectId(envId),
                          'type': 'data' }
                cut_query = { 'sys': 0, 'type': 0, 'dbVersion': 0, '_id': 0 }
                thisEnv = yarrdb.environment.find_one( env_query, cut_query )
                query = { 'environment': envId }
                thisRun = yarrdb.testRun.find_one( query )
                for env_key in thisEnv:
                    for data in thisEnv[env_key]:
                        description = data.get('description', 'null')
                        if env_key in file_dcs and description != 'null': continue
                        write_log( '\t\t\t\t{0:<7}: {1:<20}({2:^20})'.format(thisRun['runNumber'], key, description) )
                        mistake=True
            if not mistake:
                print( '# Complete the convert of the environmental key name.' )
                write_log( '\t\t[Finish]' )
                write_log( '\t\t[Success] complete the convert of the environmental key name.' )
            else:
                print( '# There are still unregistered environmental key name, check log file: {}.'.format(log_filename) )
                write_log( '\t\t[Finish]' )
                write_log( '\t\t[Failure] There are still unregistered environmental key name.' )
            print( ' ' )
    else:
        write_log( '[Finish]' )
        write_log( '[Success] complete the convert of the environmental key name.' )
    print( '# Finish' )
    print( ' ' )

    ###########
    ### testRun
    print( '# Checking test data ...' )
    print( ' ' )
    query = { 'dbVersion': { '$ne': dbv } }
    run_entries = yarrdb.testRun.find( query )
    write_log( '================================================================' )
    write_log( '[Confirmation] test run data' )
    write_log( '[Start]' )
    for run in run_entries:
        query = { 'testRun': str(run['_id']) }
        if yarrdb.componentTestRun.find( query ).count() == 0:
            query = { '_id': run['_id'] }
            yarrdb.testRun.remove( query )
            write_log( '[Not found/Delete] relational documents : {}'.format( run['runNumber'] ) ) 
    write_log( '[Finish]' ) 
    print( '# Finish' )
    print( ' ' )
 
    #####################
    ### check broken data
    if not os.path.isdir( './broken_files' ):
        os.mkdir( './broken_files' )
    print( '# Checking broken data ...' )
    print( ' ' )
    query = { 'dbVersion': { '$ne': dbv } }
    run_entries = yarrdb.componentTestRun.find( query )
    write_log( '================================================================' )
    write_log( '[Confirmation] broken files' )
    write_log( '[Start]' )
    for run in run_entries:
        runNumber = run['runNumber']
        write_log( '\t\t[Start] ComponentTestRun: {}'.format(runNumber) )
        broken_data = run.get( 'broken', [] )
        broken_num = len(broken_data)
        write_log( '\t\tNumber Of Broken Data: {}'.format(broken_num) )
        num = 0
        for data in broken_data:
            bin_data = fs.get( ObjectId( data['code'] )).read()
            query = { '_id': ObjectId( data['code'] ) }
            thisFile = yarrdb.fs.files.find_one( query )
            if not bin_data:
                write_log( '\t\t[Not found/Delete] chunks data {0}_{1}: '.format(runNumber, thisFile['filename']) ) 
                fs.delete( ObjectId(data['code']) )
                query = { '_id': run['_id'] }
                yarrdb.componentTestRun.update( query, { '$pull': { 'broken': { 'code': data['code'] }}} )
                num = num + 1
            else:
                if is_png( bin_data ):
                    print( '[PNG] Found chunks data ---> ./broken_files/{0}_{1}_{2}.png\n'.format(runNumber, data['key'], num) )
                    write_log( '\t\t[Found/Delete] chunks data (png) {0}: {1}'.format(thisFile['filename'], runNumber) )
                    fin = open('./broken_files/{0}_{1}_{2}.png'.format(runNumber, data['key'], num), 'wb')
                    fin.write(bin_data)
                    fin.close()
                elif is_pdf( bin_data ):
                    print( '[PDF] Found chunks data ---> ./broken_files/{0}_{1}_{2}.pdf\n'.format(runNumber, data['key'], num) )
                    write_log( '\t\t[Found/Delete] chunks data (pdf) {0}: {1}'.format(thisFile['filename'], runNumber) ) 
                    fin = open('./broken_files/{0}_{1}_{2}.pdf'.format(runNumber, data['key'], num), 'wb')
                    fin.write(bin_data)
                    fin.close()
                else:
                    print( '[JSON/DAT] Found chunks data ---> ./{0}_{1}_{2}.dat\n'.format(runNumber, data['key'], num) )
                    write_log( '\t\t[Found/Delete] chunks data (json/dat) {0}: {1}'.format(thisFile['filename'], runNumber) ) 
                    fin = open('./broken_files/{0}_{1}_{2}.dat'.format(runNumber, data['key'], num), 'wb')
                    fin.write(bin_data)
                    fin.close()
                fs.delete( ObjectId(data['code']) )
                query = { '_id': run['_id'] }
                yarrdb.componentTestRun.update( query, { '$pull': { 'broken': { 'code': data['code'] }}} )
                num = num + 1
    
        if broken_num == num:
            query = { '_id': run['_id'] }
            yarrdb.componentTestRun.update( query,
                                            { '$unset': { 'broken' : '' }} )
            yarrdb.componentTestRun.update( query,
                                            { '$set': { 'dbVersion' : dbv }} )
            write_log( '\t\t[Update] componentTestRun doc: ' + str(run['_id']) )
        else:
            write_log( '\t\t[WARNING][Unupdate] componentTestRun doc: ' + str(run['_id']) )
        write_log( '\t\tNumber Of Delete Data: {}'.format(num) ) 
        write_log( '\t\t[Finish]' )
    write_log( '[Finish]' )
    print( '# Finish' )
    print( ' ' )
    
    # check fs.files
    print( '# Checking fs.files ...' )
    print( ' ' )
    query = { 'dbVersion': { '$ne': dbv } }
    file_entries = yarrdb.fs.files.find( query )
    file_num = file_entries.count()
    num = 0
    write_log( '================================================================' )
    write_log( '[Confirmation] unupdated fs.files' )
    write_log( '[Start]' )
    write_log( 'Number Of Unupdated Data: {}'.format(file_num) )
    for thisFile in file_entries:
        bin_data = fs.get( thisFile['_id'] ).read()
        if bin_data:
            if is_png( bin_data ): 
                write_log( '[Found/Delete] files data (png) {}'.format(thisFile['filename']) )
                fin = open('./broken_files/files_{}.png '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            elif is_pdf( bin_data ): 
                write_log( '[Found/Delete] files data (pdf) {}'.format(thisFile['filename']) ) 
                fin = open('./broken_files/files_{}.pdf '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            else:
                write_log( '[Found/Delete] files data (json/dat) {}'.format(thisFile['filename']) )
                fin = open('./broken_files/files_{}.dat '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            num = num + 1
            fs.delete( ObjectId(thisFile['_id']) )
        else:
            write_log( '[Not found/Delete] chunks data {}'.format(thisFile['filename']) )
            fs.delete( thisFile['_id'] )
    write_log( '[Finish]' )
    print( '# Finish' )
    print( ' ' )

    # check fs.chunks
    print( '# Checking fs.chunks ...' )
    print( ' ' )
    query = { 'dbVersion': { '$ne': dbv } }
    chunk_entries = yarrdb.fs.chunks.find( query )
    chunk_num = chunk_entries.count()
    num = 0
    write_log( '================================================================' )
    write_log( '[Confirmation] unupdated fs.chunks' )
    write_log( '[Start]' )
    write_log( 'Number Of Unupdated Data: {}'.format(chunk_num) )
    for chunks in chunk_entries:
        query = { '_id': chunks['files_id'] }
        thisFile = yarrdb.fs.files.find_one( query )
        bin_data = chunks['data']
        if thisFile:
            if is_png( bin_data ): 
                write_log( '[Found/Delete] chunks data (png) {0}'.format(thisFile['filename']) ) 
                fin = open('./broken_files/chunk_{}.png '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            elif is_pdf( bin_data ): 
                write_log( '[Found/Delete chunks data (pdf) {0}'.format(thisFile['filename']) ) 
                fin = open('./broken_files/chunk_{}.pdf '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            else:
                write_log( '[Found/Delete] chunks data (json/dat) {0}'.format(thisFile['filename']) ) 
                fin = open('./broken_files/chunk_{}.dat '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            num = num + 1
            fs.delete( ObjectId(chunks['files_id']) )
        else:
            write_log( '[Not found/Delete] files data' + str(chunks['files_id']) )
            query = { '_id': chunks['_id'] }
            yarrdb.fs.chunks.remove( query )
    print( '# Finish' )
    print( ' ' )
    
    # check every collection
    confirmation = True
    print( '# Checking every collection ...' )
    print( ' ' )
    cols = yarrdb.collection_names()
    write_log( '================================================================' )
    write_log( '[Confirmation] unupdated document' )
    write_log( '[Start]' )
    # component
    col = 'component'
    write_log( 'Collection: {}'.format(col) )
    write_log( '\t\tUnupdated documents: {0}'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), copydb[col].find().count()==yarrdb[col].find().count() ))
    query = { 'componentType': 'Module' }
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Module', copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), copydb[col].find( query ).count()==yarrdb[col].find( query ).count() ))
    query = { 'componentType': { '$ne': 'Module' } }
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Chip', copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), copydb[col].find( query ).count()==yarrdb[col].find( query ).count() ))
    query = { 'chipType': 'FE-I4B', 'componentType': { '$ne': 'Module' } }
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'FE-I4B', copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), copydb[col].find(query).count()==yarrdb[col].find(query).count() ))
    query = { 'chipType': 'RD53A', 'componentType': { '$ne': 'Module' } }
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'RD53A', copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), copydb[col].find(query).count()==yarrdb[col].find(query).count() ))
    write_log( '----------------------------------------------------------------' )

    # childParentRelation
    col = 'childParentRelation'
    write_log( 'Collection: {}'.format(col) )
    write_log( '\t\tUnupdated documents: {0}'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), copydb[col].find().count()==yarrdb[col].find().count() ))
    query = { 'status': 'active' }
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Active', copydb[col].find().count(), yarrdb[col].find( query ).count(), copydb[col].find().count()==yarrdb[col].find( query ).count() ))
    write_log( '----------------------------------------------------------------' )

    # componentTestRun
    col = 'componentTestRun'
    write_log( 'Collection: {}'.format(col) )
    write_log( '\t\tUnupdated documents: {0}'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    write_log( '\t\t{0:<35}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))
    write_log( '\t\t{0:<35}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), '---' ))
    component_entries = yarrdb.component.find()
    componentIds = []
    for component in component_entries:
        componentIds.append( str(component['_id']) )
    for componentId in componentIds:
        query = { '_id': ObjectId(componentId) }
        thisComponent = yarrdb.component.find_one( query )
        query = { 'component': componentId }
        if thisComponent['componentType'] == 'Module':
            write_log( '\t\tscan entries ({0:^20}): {1:^10} ---> {2:^10} {3:^6}'.format( thisComponent['serialNumber'], copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), '---' ))
        else:
            write_log( '\t\tscan entries ({0:^20}): {1:^10} ---> {2:^10} {3:^6}'.format( thisComponent['serialNumber'], copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), copydb[col].find( query ).count()==yarrdb[col].find( query ).count() ))
    write_log( '----------------------------------------------------------------' )
 
    # testRun
    col = 'testRun'
    write_log( 'Collection: {}'.format(col) )
    write_log( '\t\tUnupdated documents: {0}'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), '---' ))
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'testRuns', copydb[col].find().count(), yarrdb[col].find().count(), copydb[col].find().count()==yarrdb[col].find().count() ))
    query = { 'display': True }
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'display', copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), copydb[col].find(query).count()==yarrdb[col].find(query).count() ))
    query = { 'environment': { '$exists': True } }
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'environment', yarrdb[col].find( query ).count(), yarrdb.environment.find().count(), yarrdb[col].find( query ).count()==yarrdb.environment.find().count() ))
    write_log( '----------------------------------------------------------------' )

    # fs.files
    col = 'fs.files'
    write_log( 'Collection: {}'.format(col) )
    write_log( '\t\tUnupdated documents: {0}'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), '---' ))
    write_log( '----------------------------------------------------------------' )

    # fs.chunks
    col = 'fs.chunks'
    write_log( 'Collection: {}'.format(col) )
    write_log( '\t\tUnupdated documents: {0}'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))
    write_log( '\t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), '---' ))
    write_log( '----------------------------------------------------------------' ) 

    # emulate basic function
    write_log( 'Emulation' ) 
    write_log( '\t\t[Start]' ) 
    query = { 'componentType': 'Module' }
    module_entries = yarrdb.component.find( query )
    moduleIds = []
    for module in module_entries:
        moduleIds.append( str(module['_id']) )
    for moduleId in moduleIds:
        query = { '_id': ObjectId(moduleId) }
        thisModule = yarrdb.component.find_one( query )
        query = { 'parent': moduleId }
        child_entries = yarrdb.childParentRelation.find( query )
        if not thisModule['children'] == child_entries.count():
            write_log( '\t\t[WARNING] Not match the number of children: {}'.format(thisModule['serialNumber']) ) 
            write_log( '\t\t          The module has children: {} in component document'.format(thisModule['children']) ) 
            write_log( '\t\t          The child entries connected by CPrelation document'.format( child_entries.count() ) ) 
            confirmation = False
        query = { 'component': moduleId }
        run_entries = yarrdb.componentTestRun.find( query )
        for child in child_entries:
            query = { '_id': ObjectId(child['child']) }
            thisChip = yarrdb.component.find_one( query )
            if not thisChip:
                write_log( '\t\t[WARNING] Not found chip: {0} - {1}'.format(thisModule['serialNumber'], child['chipId']) ) 
                confirmation = False
            query = { 'component': child['child'] }
            if not yarrdb.componentTestRun.find( query ).count() == run_entries.count():
                write_log( '\t\t[WARNING] Not match the number of testRun: {0} (chipId: {1})'.format(thisModule['serialNumber'], child['chipId']) ) 
                write_log( '\t\t          The module has test entries: {}'.format( run_entries.count() ) ) 
                write_log( '\t\t          The chip has test entries: {}'.format( yarrdb.componentTestRun.find( query ).count() ) ) 
                confirmation = False
        for run in run_entries:
            query = { '_id': ObjectId(run['testRun']) }
            thisRun = yarrdb.testRun.find_one( query )
            if not thisRun:
                write_log( '\t\t[WARNING] Not found testRun: {0} - {1}'.format(thisModule['serialNumber'], run['runNumber']) ) 
                confirmation = False
    write_log( '\t\t[Finish]' ) 
    if confirmation:
        print( '# Confirmed no problems with the conversion of DB scheme.' )
        print( '# The replica of DB can be deleted by python copyDB.py.' )
        print( ' ' )
    else:
        print( '# Confirmed some problems with the conversion of DB scheme.' )
        print( '# Please check the log file for detail.' )
        print( ' ' )
    write_log( '[Finish]' ) 
    write_log( '================================================================' ) 
    print( '# Finish' )
    print( ' ' )

finish_time = datetime.datetime.now() 
write_log( '====        Operation Time        ====' )
total_time = datetime.timedelta(seconds=(finish_time-start_time).total_seconds())
write_log( 'Total time:  ' + str(total_time) + ' [s]' )
write_log( start_time.strftime(  '\tStart: %Y-%m-%dT%H:%M:%S:%f' ) )
write_log( finish_time.strftime( '\tFinish: %Y-%m-%dT%H:%M:%S:%f' ) )
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
