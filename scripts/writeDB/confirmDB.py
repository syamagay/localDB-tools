"""
script for remove testRun data 

necessary information
- admin name     : required at login as admin
- admin password : required at login as admin
"""

##### import #####
import os, sys, datetime, json, re
import gridfs # gridfs system 
from   pymongo       import MongoClient, ASCENDING # use mongodb scheme
from   bson.objectid import ObjectId               # handle bson format

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)) )
sys.path.append( SCRIPT_DIR )
sys.path.append( SCRIPT_DIR + '/src' )

from   arguments import *   # Pass command line arguments into app.py

##### setting about dbs #####
args = getArgs()         
if args.username : url = 'mongodb://' + args.username + ':' + args.password + '@' + args.host + ':' + str(args.port) 
else :             url = 'mongodb://'                                             + args.host + ':' + str(args.port) 
client = MongoClient( url )
yarrdb = client[args.db]
userdb = client[args.userdb]
copydb = client['{}_copy'.format(args.db)]
fs = gridfs.GridFS( yarrdb )
dbv = args.version

log_dir = './log'
if not os.path.isdir(log_dir): 
    os.mkdir(log_dir)
now = datetime.datetime.now() 
log_filename = now.strftime("{}/logCo_%m%d_%H%M.txt".format(log_dir))
log_file = open( log_filename, 'w' )

##### function #####
def set_time(date):
    DIFF_FROM_UTC = args.timezone 
    time = (date+datetime.timedelta(hours=DIFF_FROM_UTC)).strftime('%Y/%m/%d %H:%M:%S')
    return time
def input_v( message ) :
    answer = ''
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
##################################################################
# Main function
start_time         = datetime.datetime.now() 
start_update_time  = ''
finish_update_time = ''
log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start] confirmDB.py \n' ) )

# Check database.json
home = os.environ['HOME']
filepath = '{}/.yarr/address'.format(home)
with open(filepath, 'r') as f: file_address = f.read().split()[0]
filepath = '{}/.yarr/database.json'.format(home)
with open(filepath, 'r') as f: file_json = json.load(f)
file_stages = file_json.get('stage', [])
file_dcs = file_json.get('environment', [])
if file_stages == [] or file_dcs == []:
    print( '# There is no database config: {}'.format(filepath) )
    print( '# Prepare the config file by running dbLogin.sh in YARR SW' )
    sys.exit()

# convert database scheme
print( '# Converting flow' )
print( '\t1. Replicate : python copyDB.py    : {0}      ---> {1}_copy'.format( args.db, args.db ) )
print( '\t2. Convert   : python convertDB.py : {0}(old) ---> {1}(new)'.format( args.db, args.db ) )
print( '\t3. Confirm   : python confirmDB.py : {0}(new) ---> {1}(confirmed)'.format( args.db, args.db ) )
print( '\t\t1. stage name' )
print( '\t\t2. environment key' )
print( '\t\t3. MAC address' )
print( '\t\t4. file data' )
print( '\t\t5. component data' )
print( '\t\t6. check all data' )
print( ' ' )
print( '# This is the stage of step3. Confirm' )
print( '# It must be run after step2. Convert' )
print( ' ' )
answer = ''
while not answer == 'y' and not answer == 'n':
    answer = input_v( '# Do you confirm new db? (y/n) > ' )
if answer == 'y' :
    #########
    ### stage
    print( '# Confirm the stage name ...' )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Confirmation] stage\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start]\n' ) )
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
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:^7}: {1:^20}\n'.format(thisRun['runNumber'], stage) ) )
        if not stage in stages:
            stages.update({ stage: [] })
        stages[stage].append(thisRun['runNumber'])
    if not stages == {}:
        final_answer = ''
        while final_answer == '':
            # Confirm the stage name
            for stage in stages:
                if stage in file_stages: continue
                print( ' ' )
                print( '############################' )
                print( '### {0:^20} ###'.format(stage) )
                print( '############################' )
                print( 'This stage is not written in {0}'.format(filepath) ) 
                print( 'Then, it must be changed to the name in following list.' )
                print( 'Select the stage from the list after checking data (ref {})'.format(log_filename) )
                print( ' ' )
                print( '----- stage list -----' )
                for file_stage in file_stages:
                    print( ' {0:<3}'.format(file_stages.index(file_stage)) + ' : ' + file_stage )
                print( ' {0:<3}'.format(len(file_stages)) + ' : unknown' )
                print(' ')
                stage_num = ''
                while stage_num == '' :
                    num = ''
                    while num == '' :
                        num = input_v( '# Enter stage number >> ' ) 
                    if not num.isdigit() : 
                        print( '[WARNING] Input item is not number, enter agein. ')
                    elif not int(num) < len(file_stages)+1 : 
                        print( '[WARNING] Input number is not included in the stage list, enter agein. ')
                    else :
                        stage_num = int(num)
                if stage_num == len(file_stages):
                    stages[stage] = 'unknown'
                else:
                    stages[stage] = file_stages[stage_num] 
    
            # Confirmation before convert
            print( ' ' )
            print( '{:^46}'.format( '###### Confirmation before the convert ######' ) )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            print( '{0:^20} ---> {1:^20}'.format( 'before the convert', 'after the convert' ) )
            for stage in stages:
                print( '{0:^20} ---> {1:^20}'.format( stage, stages[stage] ) )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            print( ' ' )
            answer = ''
            while not answer == 'y' and not answer == 'n':
                answer = input_v( '# Do you continue to convert their names for changing DB scheme? (y/n) > ' )
            print( ' ' )
            if answer == 'y':
                final_answer = 'y'
            else:
                print( '# Check again.' ) )
        if answer == 'y' : 
            print( '# Start the convert...' )
            # Converting
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Convert]\n' ) )
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Start]\n' ) )
            for runId in runIds:
                query = { '_id': ObjectId(runId) }
                thisRun = yarrdb.testRun.find_one( query )
                stage = thisRun.get('stage', 'null')
                if stage in file_stages: continue
                if stages[stage] == 'unknown': continue
                yarrdb.testRun.update( query,
                                                { '$set': { 'stage': stages[stage] }}) #UPDATE
                update_mod( 'testRun', query ) #UPDATE
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] {0:<7}: {1:<20} -> {2:<20}\n'.format(thisRun['runNumber'], stage, stages[stage]) ) )
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Finish]\n' ) )
            # Confirmation after convert
            mistake = False
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Confirmation] after convert\n' ) )
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Start]\n' ) ) 
            for runId in runIds:
                query = { '_id': ObjectId(runId) }
                thisRun = yarrdb.testRun.find_one( query )
                stage = thisRun.get('stage','null')
                if stage in file_stages: continue
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t{0:^7}: {1:^20}\n'.format(thisRun['runNumber'], stage) ) )
                mistake=True
    
            if not mistake:
                print( '# Complete the convert of the stage name.' )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Finish]\n' ) )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Success] complete the convert of the stage name.\n' ) )
            else:
                print( '# There are still unregistered stage name, check log file: {}.'.format(log_filename) )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Finish]\n' ) )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Failure] There are still unregistered stage name.\n' ) )
    else:
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish]\n' ) )
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Success] complete the convert of the stage name.\n' ) )
    print( ' ' )

    #############
    # environment
    print( '# Confirm the environmental key ...' )
    mistake = False
    keys = {}
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Confirmation] environment\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start]\n' ) )
    
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
                    print( ' ' )
                    print( '######################################' )
                    print( '### {0:^7} : {0:^20} ###'.format(env_key) )
                    print( '######################################' )
                    print( 'The key does not have description.' ) 
                    print( 'Fill the description of this environmental key after checking data (ref {}), or "n" if unknown key'.format(log_filename) )
                    print( ' ' )
                    answer = ''
                    while answer == '' :
                        answer = input_v( '# Write description (unknown ---> enter "n") >> ' ) 
                    if answer == 'n': continue
                    description = answer
                    yarrdb.environment.update( env_query,
                                               { '$set': { '{0}.0.description'.format(env_key): description }})
                    update_mod( 'environment', env_query ) #UPDATE
                    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] {0:<7}: {1:<20} {2:<23}\n'.format(thisRun['runNumber'], env_key, description) ) )
                if env_key in file_dcs: continue
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:^7}: {1:^20}({2:^20})\n'.format(thisRun['runNumber'], env_key, description) ) )
                if not env_key in keys:
                    keys.update({ env_key: description })
    if not keys == {}:  
        final_answer = ''
        while final_answer == '':
            # Confirm the environmental key name
            for key in keys:
                if key in file_dcs: continue
                print( ' ' )
                print( '#############################################################' )
                print( '### {0:^20} : {1:^30} ###'.format(key, keys[key]) )
                print( '#############################################################' )
                print( 'This key is not written in {0}'.format(filepath) ) 
                print( 'Then, it must be changed to the name in following list.' )
                print( 'Select the environmental key from the list after checking data (ref {})'.format(log_filename) )
                print( ' ' )
                print( '----- key list -----' )
                for file_env in file_dcs:
                    print( ' {0:<3}'.format(file_dcs.index(file_env)) + ' : ' + file_env )
                print( ' {0:<3}'.format(len(file_dcs)) + ' : unknown' )
                print(' ')
                env_num = ''
                while env_num == '' :
                    num = ''
                    while num == '' :
                        num = input_v( '# Enter key number >> ' ) 
                    if not num.isdigit() : 
                        print( '[WARNING] Input item is not number, enter agein. ')
                    elif not int(num) < len(file_dcs)+1 : 
                        print( '[WARNING] Input number is not included in the environmental key list, enter agein. ')
                    else :
                        env_num = int(num)
                if env_num == len(file_dcs):
                    keys[key] = 'unknown'
                else:
                    keys[key] = file_dcs[env_num] 
            # Confirmation before convert
            print( ' ' )
            print( '{:^46}'.format( '###### Confirmation before the convert ######' ) )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            print( '{0:^20} ---> {1:^20}'.format( 'before the convert', 'after the convert' ) )
            for key in keys:
                print( '{0:^20} ---> {1:^20}'.format( key, keys[key] ) )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            print( ' ' )
            answer = ''
            while not answer == 'y' and not answer == 'n':
                answer = input_v( '# Do you continue to convert their key names for changing DB scheme? (y/n) > ' )
            print( ' ' )
            if answer == 'y':
                final_answer = 'y'
            else:
                print( '# Check again.' )
        if answer == 'y' : 
            print( '# Start the convert...' )
            # Converting
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Convert]\n' ) )
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Start]\n' ) )
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
                    update_mod( 'environment', env_query ) #UPDATE
                    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] {0:<7}: {1:<20} -> {2:<20}\n'.format(thisRun['runNumber'], env_key, keys[env_key]) ) )
            mistake = False
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Finish]\n' ) )
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Confirmation] after convert\n' ) )
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Start]\n' ) ) 
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
                        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t\t\t{0:<7}: {1:<20}({2:^20})\n'.format(thisRun['runNumber'], key, description) ) )
                        mistake=True
            if not mistake:
                print( '# Complete the convert of the environmental key name.' )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Finish]\n' ) )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Success] complete the convert of the environmental key name.\n' ) )
            else:
                print( '# There are still unregistered environmental key name, check log file: {}.'.format(log_filename) )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Finish]\n' ) )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Failure] There are still unregistered environmental key name.\n' ) )
    else:
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish]\n' ) )
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Success] complete the convert of the environmental key name.\n' ) )
    print( ' ' )

    ############
    # user check
    print( '# Confirm user ...' )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Confirmation] user data\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start]\n' ) )
    users = yarrdb.user.find()
    userIds = []
    for user in users:
        userIds.append(str(user['_id']))
    print( ' ' )
    print( '----- user list -----' )
    print( '{:^46}'.format( '---------------------------------------------' ) )
    for userId in userIds:
        query = { '_id': ObjectId(userId) }
        thisUser = yarrdb.user.find_one( query )
        print( ' {0:<3} : {1:^25} {2:^15}'.format(userIds.index(userId), thisUser['institution'], thisUser['userName']) )
    print( '{:^46}'.format( '---------------------------------------------' ) )
    print( ' ' )
    answer = ''
    while not answer == 'y' and not answer == 'n':
        answer = input_v( '# Is there your data in the list? (y/n) > ' )
    print( ' ' )
    while answer == 'y':
        user_num = ''
        while user_num == '':
            num = ''
            while num == '':
                num = input_v( '# Enter the user number of your data >> ' )
            if not num.isdigit() : 
                print( '[WARNING] Input item is not number, enter agein. ')
            elif not int(num) < len(userIds): 
                print( '[WARNING] Input number is not included in the user list, enter agein. ')
            else :
                user_num = int(num)
        user_query = { '_id': ObjectId(userIds[user_num]) }
        thisUser = yarrdb.user.find_one( user_query )
        answer = ''
        print( ' ' )
        while not answer == 'y' and not answer == 'n':
            answer = input_v( '# Is your name correct : {}? (y/n) > '.format(thisUser['userName']) )
        if not answer == 'y':
            answer = ''
            print( ' ' )
            while answer == '' :
                answer = input_v( '# Input your name > ' )
            userName = answer
        else:
            userName = thisUser['userName']
        answer = ''
        print( ' ' )
        while not answer == 'y' and not answer == 'n':
            answer = input_v( '# Is the name of the institution correct : {}? (y/n) > '.format(thisUser['institution']) )
        if not answer == 'y':
            answer = ''
            print( ' ' )
            while answer == '' :
                answer = input_v( '# Input the name of the institution > ' )
            instName = answer
        else:
            instName = thisUser['institution']
        answer = ''
        print( ' ' )
        while not answer == 'y' and not answer == 'n':
            answer = input_v( '# Do you want to set identification key? (y/n ---> "default") > ' )
        if answer == 'y':
            answer = ''
            print( ' ' )
            while answer == '' :
                answer = input_v( '# Input the identification key > ' )
            idkey = answer
        else:
            idkey = thisUser['userIdentity']

        print( ' ' )
        print( '{:^46}'.format( '###### Confirmation before the convert ######' ) )
        print( '{:^46}'.format( '---------------------------------------------' ) )
        print( 'user name   : {}'.format(userName) )
        print( 'institution : {}'.format(instName) )
        print( 'userIdentity: {}'.format(idkey) ) 
        print( '{:^46}'.format( '---------------------------------------------' ) )
        print( ' ' )
        answer = ''
        while not answer == 'y' and not answer == 'n':
            answer = input_v( '# Do you continue to convert their names for changing DB scheme? (y/n) > ' )
        if answer == 'y' : 
            print( '# Start the convert...' )
            # Converting
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Convert]\n' ) )
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Start]\n' ) )
            user_doc = { 'institution':  instName,
                         'userName':     userName,
                         'userIdentity': idkey }
            user_data = yarrdb.user.find_one( user_doc )
            user_id = str(user_query['_id']) 
            if user_data:
                if not str(user_data['_id']) == str(user_query['_id']):
                    user_id = str(user_data['_id'])
                    yarrdb.user.remove( user_query )
                    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Remove] user data : ' + str(user_query['_id']) ) )
                    query = { 'user_id': str(user_query['_id']) }
                    yarrdb.component.update( query, { '$set': { 'user_id': user_id }}, multi=True )
                    yarrdb.testRun.update( query, { '$set': { 'user_id': user_id }}, multi=True )
            else:
                yarrdb.user.update( user_query,
                                    { '$set': user_doc }) #UPDATE
                update_mod( 'user', user_query ) #UPDATE
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] user data {0}'.format(userName) ) )
        print( ' ' )
        print( '----- user list -----' )
        print( '{:^46}'.format( '---------------------------------------------' ) )
        query = { '_id': { '$ne': ObjectId(user_id) }}
        users = yarrdb.user.find(query)
        userIds = []
        for user in users:
            userIds.append(str(user['_id']))
        for userId in userIds:
            query = { '_id': ObjectId(userId) }
            thisUser = yarrdb.user.find_one( query )
            print( ' {0:<3} : {1:^25} {2:^15}'.format(userIds.index(userId), thisUser['institution'], thisUser['userName']) )
        print( '{:^46}'.format( '---------------------------------------------' ) )
        print( ' ' )
        answer = ''
        while not answer == 'y' and not answer == 'n':
            answer = input_v( '# Is there your data in the list? (y/n) > ' )
        print( ' ' )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish]\n' ) )

    #############
    # MAC address
    print( '# Confirm the MAC address ...' )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Confirmation] MAC address\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start]\n' ) )
    institutions = yarrdb.institution.find()
    instIds = []
    for inst in institutions:
        instIds.append(str(inst['_id']))
    for instId in instIds:
        inst_query = { '_id': ObjectId(instId) }
        thisInstitution = yarrdb.institution.find_one( inst_query )
        if thisInstitution['institution'] == 'null':
            query = { 'address': thisInstitution['address'] }
            run_entries = yarrdb.testRun.find( query )
            print( ' ' )
            print( '----- test list -----' )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            cnt=0
            for run in run_entries:
                query = { '_id': ObjectId(run['user_id']) }
                thisUser = yarrdb.user.find_one( query )
                query = { 'testRun': str(run['_id']) }
                thisCtr = yarrdb.componentTestRun.find_one( query )
                query = { '_id': ObjectId(thisCtr['component']) }
                thisComponent = yarrdb.component.find_one( query )
                print( '{0:^15} ({1:^15}) tested by {2:^20} in {3:^20}'.format(thisComponent['serialNumber'], run['stage'], thisUser['userName'], set_time(run['startTime'])) )
            print( '{:^46}'.format( '---------------------------------------------' ) )
            print( ' ' )

            institutionName = thisInstitution['address']
            userName = thisInstitution['name']
            answer = ''
            while not answer == 'y' and not answer == 'n':
                answer = input_v( '# Is these runs tested on the machine you are using? (y/n) > ' )
            if answer == 'y' : 
                query = { 'address': file_address }
                if yarrdb.institution.find_one( query ):
                    yarrdb.institution.remove( inst_query )
                else:
                    answer = ''
                    print( ' ' )
                    while not answer == 'y' and not answer == 'n':
                        answer = input_v( '# Is the name of the institution the same as where you are using this machine: {}? (y/n) > '.format(institutionName) )
                    if not answer == 'y':
                        answer = ''
                        print( ' ' )
                        while answer == '' :
                            answer = input_v( '# Input the name of the institution > ' )
                        instName = answer
                    else:
                        instName = thisInstitution['address']
                    answer = ''
                    print( ' ' )
                    while answer == '' :
                        answer = input_v( '# Input the name of this machine > ' )
                    name = answer
                    print( ' ' )
                    print( '{:^46}'.format( '###### Confirmation before the convert ######' ) )
                    print( '{:^46}'.format( '---------------------------------------------' ) )
                    print( 'insitution name: {}'.format(instName) )
                    print( 'machine name:    {}'.format(name) )
                    print( 'MAC address:     {}'.format(file_address) ) 
                    print( '{:^46}'.format( '---------------------------------------------' ) )
                    print( ' ' )
                    answer = ''
                    while not answer == 'y' and not answer == 'n':
                        answer = input_v( '# Do you continue to convert their names for changing DB scheme? (y/n) > ' )
                    if answer == 'y' : 
                        print( '# Start the convert...' )
                        # Converting
                        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Convert]\n' ) )
                        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Start]\n' ) )
                        yarrdb.institution.update( inst_query,
                                                   { '$set': { 'institution': instName,
                                                               'name': name,
                                                               'address': file_address }}) #UPDATE
                        update_mod( 'institution', inst_query ) #UPDATE
                        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] {0} -> {1} in institution document'.format(institutionName, file_address) ) )
                        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Finish]\n' ) )

                query = { 'address': institutionName }
                yarrdb.component.update( query,
                                         { '$set': { 'address': file_address }},
                                         multi=True )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] {0} -> {1} in component collection'.format(institutionName, file_address) ) )
                yarrdb.testRun.update( query,
                                       { '$set': { 'address': file_address }},
                                       multi=True )
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] {0} -> {1} in testRun collection'.format(institutionName, file_address) ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish]\n' ) )

    #####################
    ### check broken data
    if not os.path.isdir( './broken_files' ):
        os.mkdir( './broken_files' )
    print( '# Checking broken data ...' )
    query = { 'dbVersion': { '$ne': dbv } }
    run_entries = yarrdb.componentTestRun.find( query )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Confirmation] broken files\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start]\n' ) )
    for run in run_entries:
        runNumber = run['runNumber']
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Start] ComponentTestRun: {}\n'.format(runNumber) ) )
        broken_data = run.get( 'broken', [] )
        broken_num = len(broken_data)
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tNumber Of Broken Data: {}\n'.format(broken_num) ) )
        num = 0
        for data in broken_data:
            bin_data = fs.get( ObjectId( data['code'] )).read()
            query = { '_id': ObjectId( data['code'] ) }
            thisFile = yarrdb.fs.files.find_one( query )
            if not bin_data:
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Not found/Delete] chunks data {0}_{1}: '.format(runNumber, thisFile['filename']) ) + str(data['code']) + '\n' )
                fs.delete( ObjectId(data['code']) )
                query = { '_id': run['_id'] }
                yarrdb.componentTestRun.update( query, { '$pull': { 'broken': { 'code': data['code'] }}} )
                num = num + 1
            else:
                if is_png( bin_data ):
                    print( '\n[PNG] chunks data {0}: {1}\n'.format(thisFile['filename'], runNumber) )
                    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Found/Delete] chunks data (png) {0}: {1}'.format(thisFile['filename'], runNumber) ) + str(data['code']) + '\n' )
                    fin = open('./broken_files/{0}_{1}_{2}.png'.format(runNumber, data['key'], num), 'wb')
                    fin.write(bin_data)
                    fin.close()
                elif is_pdf( bin_data ):
                    print( '\n[PDF] chunks data {0}: {1}\n'.format(thisFile['filename'], runNumber) )
                    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Found/Delete] chunks data (pdf) {0}: {1}'.format(thisFile['filename'], runNumber) ) + str(data['code']) + '\n' )
                    fin = open('./broken_files/{0}_{1}_{2}.pdf'.format(runNumber, data['key'], num), 'wb')
                    fin.write(bin_data)
                    fin.close()
                else:
                    print( '\n[JSON/DAT] chunks data {0}: {1}\n'.format(thisFile['filename'], runNumber) )
                    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Found/Delete] chunks data (json/dat) {0}: {1}'.format(thisFile['filename'], runNumber) ) + str(data['code']) + '\n' )
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
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Update] componentTestRun doc: ' + str(run['_id']) + '\n' ) )
        else:
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[WARNING][Unupdate] componentTestRun doc: ' + str(run['_id']) + '\n' ) )
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tNumber Of Delete Data: {}\n'.format(num) ) )
        log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Finish]\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish]\n' ) )
    
    # check fs.files
    print( '# Checking fs.files ...' )
    query = { 'dbVersion': { '$ne': dbv } }
    file_entries = yarrdb.fs.files.find( query )
    file_num = file_entries.count()
    num = 0
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Confirmation] unupdated fs.files\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start]\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Number Of Unupdated Data: {}\n'.format(file_num) ) )
    for thisFile in file_entries:
        bin_data = fs.get( thisFile['_id'] ).read()
        if bin_data:
            if is_png( bin_data ): 
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Found/Delete] files data (png) {}'.format(thisFile['filename']) ) + str(thisFile['_id']) + '\n')
                fin = open('./broken_files/files_{}.png '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            elif is_pdf( bin_data ): 
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Found/Delete] files data (pdf) {}'.format(thisFile['filename']) ) + str(thisFile['_id']) + '\n' )
                fin = open('./broken_files/files_{}.pdf '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            else:
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Found/Delete] files data (json/dat) {}'.format(thisFile['filename']) ) + str(thisFile['_id']) + '\n' )
                fin = open('./broken_files/files_{}.dat '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            num = num + 1
            fs.delete( ObjectId(thisFile['_id']) )
        else:
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Not found/Delete] chunks data {}'.format(thisFile['filename']) ) + str(thisFile['_id']) + '\n' )
            fs.delete( thisFile['_id'] )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish]\n' ) )

    # check fs.chunks
    print( '# Checking fs.chunks ...' )
    query = { 'dbVersion': { '$ne': dbv } }
    chunk_entries = yarrdb.fs.chunks.find( query )
    chunk_num = chunk_entries.count()
    num = 0
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Confirmation] unupdated fs.chunks\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start]\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Number Of Unupdated Data: {}\n'.format(chunk_num) ) )
    for chunks in chunk_entries:
        query = { '_id': chunks['files_id'] }
        thisFile = yarrdb.fs.files.find_one( query )
        bin_data = chunks['data']
        if thisFile:
            if is_png( bin_data ): 
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Found/Delete] chunks data (png) {0}'.format(thisFile['filename']) ) + str(chunks['files_id']) + '\n' )
                fin = open('./broken_files/chunk_{}.png '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            elif is_pdf( bin_data ): 
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Found/Delete chunks data (pdf) {0}'.format(thisFile['filename']) ) + str(chunks['files_id']) + '\n' )
                fin = open('./broken_files/chunk_{}.pdf '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            else:
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Found/Delete] chunks data (json/dat) {0}'.format(thisFile['filename']) ) + str(chunks['files_id']) + '\n' )
                fin = open('./broken_files/chunk_{}.dat '.format(num) , 'wb')
                fin.write(bin_data)
                fin.close()
            num = num + 1
            fs.delete( ObjectId(chunks['files_id']) )
        else:
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Not found/Delete] files data' + str(chunks['files_id']) + '\n' ) )
            query = { '_id': chunks['_id'] }
            yarrdb.fs.chunks.remove( query )
    
    # check component
    print( '# Checking component ...' )
    query = { 'dbVersion': { '$ne': dbv }}
    component_entries = yarrdb.component.find( query )
    component_num = component_entries.count()
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Confirmation] unupdated component\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start]\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Number Of Unupdated Data: {}\n'.format(component_num) ) )
    for component in component_entries:
        query = { 'component': str(component['_id']), 'dbVersion': { '$ne': dbv } }
        run_counts = yarrdb.testRun.find( query ).count()
        if not run_counts == 0: continue
      
        query = { 'component': str(component['_id']) }
        run_counts = yarrdb.testRun.find( query ).count()
        query = [{ 'parent': str(component['_id']) }, { 'child': str(component['_id']) }]
        cpr_counts = yarrdb.childParentRelation.find({'$or': query}).count()
        if run_counts == 0 and cpr_counts == 0:
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Not found/Delete] relational documents (run/cpr): {}'.format( component['serialNumber'] ) ) + str(component['_id']) + '\n' )
            query = { '_id': component['_id'] }
            yarrdb.component.remove( query )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish]\n' ) )
    
    # check every collection
    confirmation = True
    print( '# Checking every collection ...' )
    cols = yarrdb.collection_names()
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Confirmation] unupdated documentt\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Start]\n' ) )
    # component
    col = 'component'
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Collection: {}\n'.format(col) ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tUnupdated documents: {0}\n'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) ) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), copydb[col].find().count()==yarrdb[col].find().count() ))) 
    query = { 'componentType': 'Module' }
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Module', copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), copydb[col].find( query ).count()==yarrdb[col].find( query ).count() ))) 
    query = { 'componentType': { '$ne': 'Module' } }
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Chip', copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), copydb[col].find( query ).count()==yarrdb[col].find( query ).count() ))) 
    old_query = { 'componentType': 'FE-I4B' }
    new_query = { 'chipType': 'FE-I4B', 'componentType': { '$ne': 'Module' } }
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'FE-I4B', copydb[col].find( old_query ).count(), yarrdb[col].find( new_query ).count(), copydb[col].find(old_query).count()==yarrdb[col].find(new_query).count() ))) 
    old_query = { 'componentType': 'RD53A' }
    new_query = { 'chipType': 'RD53A', 'componentType': { '$ne': 'Module' } }
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'RD53A', copydb[col].find( old_query ).count(), yarrdb[col].find( new_query ).count(), copydb[col].find(old_query).count()==yarrdb[col].find(new_query).count() ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ----------------------------------------------------------------\n' ) )

    # childParentRelation
    col = 'childParentRelation'
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Collection: {}\n'.format(col) ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tUnupdated documents: {0}\n'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) ) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), copydb[col].find().count()==yarrdb[col].find().count() ))) 
    query = { 'status': 'active' }
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Active', copydb[col].find().count(), yarrdb[col].find( query ).count(), copydb[col].find().count()==yarrdb[col].find( query ).count() ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ----------------------------------------------------------------\n' ) )

    # componentTestRun
    col = 'componentTestRun'
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Collection: {}\n'.format(col) ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tUnupdated documents: {0}\n'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) ) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<35}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<35}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), '---' ))) 
    component_entries = yarrdb.component.find()
    componentIds = []
    for component in component_entries:
        componentIds.append( str(component['_id']) )
    for componentId in componentIds:
        query = { '_id': ObjectId(componentId) }
        thisComponent = yarrdb.component.find_one( query )
        query = { 'component': componentId }
        if thisComponent['componentType'] == 'Module':
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tscan entries ({0:^20}): {1:^10} ---> {2:^10} {3:^6}\n'.format( thisComponent['serialNumber'], copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), '---' ))) 
        else:
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tscan entries ({0:^20}): {1:^10} ---> {2:^10} {3:^6}\n'.format( thisComponent['serialNumber'], copydb[col].find( query ).count(), yarrdb[col].find( query ).count(), copydb[col].find( query ).count()==yarrdb[col].find( query ).count() ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ----------------------------------------------------------------\n' ) )
 
    # testRun
    col = 'testRun'
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Collection: {}\n'.format(col) ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tUnupdated documents: {0}\n'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) ) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), '---' ))) 
    run_entries = copydb.testRun.find()
    runIds = []
    testRuns = []
    display = 0
    for run in run_entries:
        runIds.append( str(run['_id']) )
    for runId in runIds:
        query = { '_id': ObjectId(runId) }
        thisRun = copydb.testRun.find_one( query )
        doc = { 'runNumber': thisRun['runNumber'], 'institution': thisRun.get('institution','null'), 'userIdentity': thisRun.get('userIdentity','null') }
        if not doc in testRuns: 
            testRuns.append( doc )
            if thisRun.get('display', False): display += 1
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'testRuns', len(testRuns), yarrdb[col].find().count(), len(testRuns)==yarrdb[col].find().count() ))) 
    query = { 'display': True }
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'display', display, yarrdb[col].find( query ).count(), len(testRuns)==yarrdb[col].find().count() ))) 
    query = { 'environment': { '$exists': True } }
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'environment', yarrdb[col].find( query ).count(), yarrdb.environment.find().count(), yarrdb[col].find( query ).count()==yarrdb.environment.find().count() ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ----------------------------------------------------------------\n' ) )

    # fs.files
    col = 'fs.files'
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Collection: {}\n'.format(col) ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tUnupdated documents: {0}\n'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) ) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), '---' ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ----------------------------------------------------------------\n' ) )

    # fs.chunks
    col = 'fs.chunks'
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Collection: {}\n'.format(col) ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\tUnupdated documents: {0}\n'.format(yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count()) ) )
    if not yarrdb[col].find({ 'dbVersion': { '$ne': dbv } }).count() == 0: confirmation = False
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Keyword', 'old (copy)', 'new (orig)', 'status' ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t{0:<15}: {1:^10} ---> {2:^10} {3:^6}\n'.format( 'Document', copydb[col].find().count(), yarrdb[col].find().count(), '---' ))) 
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ----------------------------------------------------------------\n' ) )

    # emulate basic function
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S Emulation\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Start]\n' ) )
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
            log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[WARNING] Not match the number of children: {}\n'.format(thisModule['serialNumber']) ) )
            confirmation = False
        query = { 'component': moduleId }
        run_entries = yarrdb.componentTestRun.find( query )
        for child in child_entries:
            query = { '_id': ObjectId(child['child']) }
            thisChip = yarrdb.component.find_one( query )
            if not thisChip:
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[WARNING] Not found chip: {0} - {1}\n'.format(thisModule['serialNumber'], child['chipId']) ) )
                confirmation = False
            query = { 'component': child['child'] }
            if not yarrdb.componentTestRun.find( query ).count() == run_entries.count():
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[WARNING] Not match the number of testRun: {0} and {1}\n'.format(thisModule['serialNumber'], child['chipId']) ) )
                confirmation = False
        for run in run_entries:
            query = { '_id': ObjectId(run['testRun']) }
            thisRun = yarrdb.testRun.find_one( query )
            if not thisRun:
                log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[WARNING] Not found testRun: {0} - {1}\n'.format(thisModule['serialNumber'], run['runNumber']) ) )
                confirmation = False
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S \t\t[Finish]\n' ) )
    if confirmation:
        print( '# Confirmed no problems with the conversion of DB scheme.' )
        print( '# The replica of DB can be deleted by python copyDB.py.' )
        print( ' ' )
    else:
        print( '# Confirmed some problems with the conversion of DB scheme.' )
        print( '# Please check the log file for detail.' )
        print( ' ' )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S [Finish]\n' ) )
    log_file.write( datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S ================================================================\n' ) )

finish_time = datetime.datetime.now() 
log_file.write( '\n====        Operation Time        ====\n' )
total_time = datetime.timedelta(seconds=(finish_time-start_time).total_seconds())
log_file.write( 'Total time:  ' + str(total_time) + ' [s]\n' )
log_file.write( start_time.strftime(  '\tStart: %M:%S:%f' ) + '\n' )
log_file.write( finish_time.strftime( '\tFinish: %M:%S:%f' ) + '\n' )
log_file.write( '======================================' )
log_file.close()

print( '# The path to log file: {}'.format(log_filename) )
print( ' ' )
print( '# Exit ...' )
sys.exit()     
