"""
script for copy databaase scheme
replicated DB ---> <dbName>_copy
"""

##### import #####
import os, sys, datetime, json, re, time, hashlib
import gridfs # gridfs system 
from   pymongo       import MongoClient # use mongodb scheme
from   bson.objectid import ObjectId    # handle bson format

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)) )
sys.path.append( SCRIPT_DIR )
sys.path.append( SCRIPT_DIR + '/src' )

from   arguments import *   # Pass command line arguments into app.py

##### setting about dbs #####
args = getArgs()         
if args.username : url = 'mongodb://' + args.username + ':' + args.password + '@' + args.host + ':' + str(args.port) 
else :             url = 'mongodb://'                                             + args.host + ':' + str(args.port) 
client = MongoClient( url )
localdb = client[args.db]
fs = gridfs.GridFS( localdb )
dbv = args.version

##### function #####
def input_v( message ) :
    answer = ''
    if args.fpython == 2 : answer = raw_input( message ) 
    if args.fpython == 3 : answer =     input( message )
    return answer
#################################################################
# Main function
# convert database scheme
print( '# Conversion flow' )
print( '\t1. Replicate : python copyDB.py    : {0}      ---> {1}_copy'.format( args.db, args.db ) )
print( '\t2. Convert   : python convertDB.py : {0}(old) ---> {1}(new)'.format( args.db, args.db ) )
print( '\t3. Confirm   : python confirmDB.py : {0}(new) ---> {1}(confirmed)'.format( args.db, args.db ) )
print( ' ' )
print( '# This is the stage of step1. Replicate' )
print( ' ' )
print( '--- function list ---' )
print( ' 0. replicate: {0}      ---> {1}_copy (overwritten)'.format( args.db, args.db ) )
print( ' 1. restore:   {0}_copy ---> {1}      (overwritten)'.format( args.db, args.db ) )
print( ' 2. remove:    {0}_copy ---> drop'.format( args.db ) )
print( ' 3. exit' )
print( ' ' )
func_num = ''
while func_num == '':
    num = ''
    while num == '':
        num = input_v( '# Enter function number >> ' ) 
    if not num.isdigit() : 
        print( '[WARNING] Input item is not number, enter agein. ')
    elif not int(num) < 4 : 
        print( '[WARNING] Input number is not included in the function list, enter agein. ')
    else :
        func_num = int(num)
print( ' ' )
copy_db='{}_copy'.format(args.db)
if func_num == 0:
    dbs = client.list_database_names()
    if copy_db in dbs:
        print( '[WARNING] {} is already exist.'.format(copy_db) )
        print( ' ' )
        answer = ''
        while not answer == 'y' and not answer =='n':
            answer = input_v( '# Do you overwrite current DB to the copy of the original DB: {0} ---> {1}? (y/n) > '.format( args.db, copy_db ) )
        print( ' ' )
        if answer == 'y':
            print( '# Removing database "{}" ...'.format(copy_db) )
            print( datetime.datetime.now().strftime( '\t[Start]  %Y-%m-%dT%H:%M:%S' ) )
            client.drop_database( copy_db )
            print( datetime.datetime.now().strftime( '\t[Finish] %Y-%m-%dT%H:%M:%S' ) )
            print( '# Succeeded in removing.' )
            print( ' ' )
            print( '# Replicating database to "{}" for replica ... '.format(copy_db) )
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
            client.admin.command( 'copydb',
                                  fromdb=args.db,
                                  todb=copy_db ) 
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]' ) )
            print( '# Succeeded in replicating.' )
            print( ' ' )
    else:
        answer = ''
        while not answer == 'y' and not answer =='n':
            answer = input_v( '# Do you replicate DB: {0} ---> {1}? (y/n) > '.format( args.db, copy_db ) )
        print( ' ' )
        if answer == 'y':
            # copy database for buckup
            print( '# Replicating database to "{}" for replica ... '.format(copy_db) )
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Start]' ) )
            client.admin.command( 'copydb',
                                  fromdb=args.db,
                                  todb=copy_db ) 
            print( datetime.datetime.now().strftime( '\t%Y-%m-%dT%H:%M:%S [Finish]' ) )
            print( '# Succeeded in replicating.' )
            print( ' ' )
elif func_num == 1:
    dbs = client.list_database_names()
    if not copy_db in dbs:
        print( '[WARNING] {} is not exist.'.format(copy_db) )
        print( ' ' )
    else:
        print( '# {} is found.'.format(copy_db) )
        print( ' ' )
        answer = ''
        while not answer == 'y' and not answer == 'n':
            answer = input_v( '# Do you make it back to the original DB: {0} ---> {1}? (y/n) > '.format(copy_db, args.db) )
        print( ' ' )
        if answer == 'y' :
            print( '# Restoring ...' )
            print( datetime.datetime.now().strftime( '\t[Start]  %Y-%m-%dT%H:%M:%S' ) )
            client.drop_database( args.db )
            client.admin.command( 'copydb',
                                  fromdb=copy_db,
                                  todb=args.db )#COPY 
            print( datetime.datetime.now().strftime( '\t[Finish] %Y-%m-%dT%H:%M:%S' ) )
            print( '# Succeeded in Restoring.' )
            print( ' ' )
elif func_num == 2:
    dbs = client.list_database_names()
    if not copy_db in dbs:
        print( '# {} is not exist.'.format(copy_db) )
        print( ' ' )
    else:
        print( '# {} is found.'.format(copy_db) )
        print( ' ' )
        answer = ''
        while not answer == 'y' and not answer == 'n':
            answer = input_v( '# Do you remove {0}? (y/n) > '.format(copy_db) )
        print( ' ' )
        if answer == 'y' :
            print( '# Removing database "{}" ...'.format(copy_db) )
            print( datetime.datetime.now().strftime( '\t[Start]  %Y-%m-%dT%H:%M:%S' ) )
            client.drop_database( copy_db )
            print( datetime.datetime.now().strftime( '\t[Finish] %Y-%m-%dT%H:%M:%S' ) )
            print( '# Succeeded in removing.' )
            print( ' ' )
elif func_num == 3:
    print( '# Exit ...' )
    sys.exit()     
print( '# Exit ...' )
sys.exit()     
