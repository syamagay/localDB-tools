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
fs = gridfs.GridFS( yarrdb )

##### function #####
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

#################################################################
print( '# Confirm new database scheme' )
now = datetime.datetime.now() 
log_filename = now.strftime("logCo_%m%d_%H%M.txt")
log_file = open( log_filename, 'w' )

start_time = datetime.datetime.now() 

if not os.path.isdir( './broken_files' ):
    os.mkdir( './broken_files' )

# check broken data
print( '# Checking broken data ...' )
query = { 'dbVersion': { '$ne': 2 } }
run_entries = yarrdb.componentTestRun.find( query )
log_file.write( '========================================\n' )
log_file.write( '=== Broken files in componentTestRun ===\n' )
log_file.write( '========================================\n' )
for run in run_entries:
    runNumber = run['runNumber']
    log_file.write( '\nComponentTestRun: {}\n'.format(runNumber) )
    broken_data = run.get( 'broken' )
    broken_num = len(broken_data)
    log_file.write( '\tNumber Of Broken Data: {}\n'.format(broken_num) )
    num = 0
    for data in broken_data:
        bin_data = fs.get( ObjectId( data['code'] )).read()
        query = { '_id': ObjectId( data['code'] ) }
        thisFile = yarrdb.fs.files.find_one( query )
        if not bin_data:
            log_file.write( '\t[NOT FOUND] chunks data {0}: {1}\n'.format(thisFile['filename'], runNumber) )
            log_file.write( '\t            -> delete: ' + str(data['code']) + '\n' )
            fs.delete( ObjectId(data['code']) )
            query = { '_id': run['_id'] }
            yarrdb.componentTestRun.update( query, { '$pull': { 'broken': { 'code': data['code'] }}} )
            num = num + 1
        else:
            if is_png( bin_data ):
                print( '\n[PNG] chunks data {0}: {1}\n'.format(thisFile['filename'], runNumber) )
                log_file.write( '\t[FOUND] chunks data (png) {0}: {1}\n'.format(thisFile['filename'], runNumber) )
                fin = open('./broken_files/{0}_{1}_{2}.png'.format(runNumber, data['key'], num), 'wb')
                fin.write(bin_data)
                fin.close()
            elif is_pdf( bin_data ):
                print( '\n[PDF] chunks data {0}: {1}\n'.format(thisFile['filename'], runNumber) )
                log_file.write( '\t[FOUND] chunks data (pdf) {0}: {1}\n'.format(thisFile['filename'], runNumber) )
                fin = open('./broken_files/{0}_{1}_{2}.pdf'.format(runNumber, data['key'], num), 'wb')
                fin.write(bin_data)
                fin.close()
            else:
                print( '\n[JSON/DAT] chunks data {0}: {1}\n'.format(thisFile['filename'], runNumber) )
                log_file.write( '\t[FOUND] chunks data (json/dat) {0}: {1}\n'.format(thisFile['filename'], runNumber) )
                fin = open('./broken_files/{0}_{1}_{2}.dat'.format(runNumber, data['key'], num), 'wb')
                fin.write(bin_data)
                fin.close()
            answer = ''
            while answer == '' :
                answer = input_v( '# Do you delete this file? (y/n) > ' )
            if answer == 'y':
                fs.delete( ObjectId(data['code']) )
                log_file.write( '\t        -> delete: ' + str(data['code']) + '\n' )
                query = { '_id': run['_id'] }
                yarrdb.componentTestRun.update( query, { '$pull': { 'broken': { 'code': data['code'] }}} )
                num = num + 1

    if broken_num == num:
        query = { '_id': run['_id'] }
        yarrdb.componentTestRun.update( query,
                                        { '$unset': { 'broken' : '' }} )
        yarrdb.componentTestRun.update( query,
                                        { '$set': { 'dbVersion' : 2 }} )
        log_file.write( '[UPDATE] componentTestRun doc: ' + str(run['_id']) + '\n' )
    else:
        log_file.write( '[UNUPDATE] componentTestRun doc: ' + str(run['_id']) + '\n' )
    log_file.write( '\tNumber Of Delete Data: {}\n'.format(num) )

# check fs.files
print( '# Checking fs.files ...' )
query = { 'dbVersion': { '$ne': 2 } }
file_entries = yarrdb.fs.files.find( query )
file_num = file_entries.count()
num = 0
log_file.write( '\n==========================\n' )
log_file.write( '=== Unupdated fs.files ===\n' )
log_file.write( '==========================\n' )
log_file.write( '\tNumber Of Unupdated Data: {}\n'.format(file_num) )
for thisFile in file_entries:
    bin_data = fs.get( thisFile['_id'] ).read()
    if bin_data:
        if is_png( bin_data ): 
            log_file.write( '\t[FOUND] files data (png) {}\n'.format(thisFile['filename']) )
            fin = open('./broken_files/files_{}.png '.format(num) , 'wb')
            fin.write(bin_data)
            fin.close()
        elif is_pdf( bin_data ): 
            log_file.write( '\t[FOUND] files data (pdf) {}\n'.format(thisFile['filename']) )
            fin = open('./broken_files/files_{}.pdf '.format(num) , 'wb')
            fin.write(bin_data)
            fin.close()
        else:
            log_file.write( '\t[FOUND] files data (json/dat) {}\n'.format(thisFile['filename']) )
            fin = open('./broken_files/files_{}.dat '.format(num) , 'wb')
            fin.write(bin_data)
            fin.close()
        num = num + 1
        answer = ''
        while answer == '' :
            answer = input_v( '# Do you delete this file? (y/n) > ' )
        if answer == 'y':
            fs.delete( ObjectId(thisFile['_id']) )
            log_file.write( '\t        -> delete: ' + str(thisFile['_id']) + '\n' )
    else:
        log_file.write( '\t[NOT FOUND] chunks data {}\n'.format(thisFile['filename']) )
        fs.delete( thisFile['_id'] )
        log_file.write( '\t            -> delete: ' + str(thisFile['_id']) + '\n' )

# check fs.chunks
print( '# Checking fs.chunks ...' )
query = { 'dbVersion': { '$ne': 2 } }
chunk_entries = yarrdb.fs.chunks.find( query )
chunk_num = chunk_entries.count()
num = 0
log_file.write( '\n===========================\n' )
log_file.write( '=== Unupdated fs.chunks ===\n' )
log_file.write( '===========================\n' )
log_file.write( '\tNumber Of Unupdated Data: {}\n'.format(chunk_num) )
for chunks in chunk_entries:
    query = { '_id': chunks['files_id'] }
    thisFile = yarrdb.fs.files.find_one( query )
    bin_data = chunks['data']
    if thisFile:
        if is_png( bin_data ): 
            log_file.write( '\t[FOUND] chunks data (png) {0}\n'.format(thisFile['filename']) )
            fin = open('./broken_files/chunk_{}.png '.format(num) , 'wb')
            fin.write(bin_data)
            fin.close()
        elif is_pdf( bin_data ): 
            log_file.write( '\t[FOUND] chunks data (pdf) {0}\n'.format(thisFile['filename']) )
            fin = open('./broken_files/chunk_{}.pdf '.format(num) , 'wb')
            fin.write(bin_data)
            fin.close()
        else:
            log_file.write( '\t[FOUND] chunks data (json/dat) {0}\n'.format(thisFile['filename']) )
            fin = open('./broken_files/chunk_{}.dat '.format(num) , 'wb')
            fin.write(bin_data)
            fin.close()
        num = num + 1
        answer = ''
        while answer == '' :
            answer = input_v( '# Do you delete this file? (y/n) > ' )
        if answer == 'y':
            fs.delete( ObjectId(chunks['files_id']) )
            log_file.write( '\t        -> delete: ' + str(chunks['files_id']) + '\n' )
    else:
        log_file.write( '\t[NOT FOUND] files data\n' )
        query = { '_id': chunks['_id'] }
        yarrdb.fs.chunks.remove( query )
        log_file.write( '\t          -> delete: ' + str(chunks['_id']) + '\n' )

# check component
print( '# Checking component ...' )
query = { 'dbVersion': { '$ne': 2 }}
component_entries = yarrdb.component.find( query )
component_num = component_entries.count()
log_file.write( '\n===========================\n' )
log_file.write( '=== Unupdated component ===\n' )
log_file.write( '===========================\n' )
log_file.write( '\tNumber Of Unupdated Data: {}\n'.format(component_num) )
for component in component_entries:
    query = { 'component': str(component['_id']), 'dbVersion': { '$ne': 2 } }
    run_counts = yarrdb.testRun.find( query ).count()
    if not run_counts == 0: continue
  
    query = { 'component': str(component['_id']) }
    run_counts = yarrdb.testRun.find( query ).count()
    query = [{ 'parent': str(component['_id']) }, { 'child': str(component['_id']) }]
    cpr_counts = yarrdb.childParentRelation.find({'$or': query}).count()
    if run_counts == 0 and cpr_counts == 0:
        log_file.write( '\t[NOT FOUND] relational documents (run/cpr): {}\n'.format( component['serialNumber'] ) )
        query = { '_id': component['_id'] }
        yarrdb.component.remove( query )
        log_file.write( '\t          -> delete: ' + str(component['_id']) + '\n' )

# check every collection
print( '# Checking every collection ...' )
cols = yarrdb.collection_names()
log_file.write( '\n===========================\n' )
log_file.write( '=== Unupdated documents ===\n' )
log_file.write( '===========================\n' )
for col in cols:
    log_file.write( 'Collection: {0:25}---> Unupdated documents: {1}\n'.format(col, yarrdb[col].find({ 'dbVersion': { '$ne': 2 } }).count()) )

finish_time = datetime.datetime.now() 
log_file.write( '\n==== Operation Time ====\n' )
log_file.write( start_time.strftime(  'start:  %M:%S:%f' ) + '\n' )
log_file.write( finish_time.strftime( 'finish: %M:%S:%f' ) + '\n' )
total_time = datetime.timedelta(seconds=(finish_time-start_time).total_seconds())
log_file.write( 'Total:  ' + str(total_time) + ' [s]\n' )
log_file.write( '========================' )

log_file.close()

print( '# Log file: {}.'.format(log_filename) )
