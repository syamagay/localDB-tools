import os, sys
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)) )
sys.path.append( SCRIPT_DIR )
sys.path.append( SCRIPT_DIR + "/src" )

from arguments import *   # Pass command line arguments into app.py
try    : 
    import root
    DOROOT = True
except : 
    DOROOT = False 

import pwd, glob, datetime, shutil, json

# use mongodb scheme
import pymongo
from flask_pymongo import PyMongo
from pymongo import MongoClient

# handle bson format
from bson.objectid import ObjectId 

# image related module
import gridfs # gridfs system 

# other function
import listset, func

#############
# set dbs
args = getArgs()            # Get command line arguments
client = MongoClient( host=args.host, port=args.port )
yarrdb = client[args.db]
fs = gridfs.GridFS( yarrdb )

##################
# path/to/save/dir 
USER = pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
DAT_DIR = '{}/dat'.format( USER_DIR )
PLOT_DIR = '{}/result'.format( USER_DIR )
THUM_DIR = '{}/result/thum'.format( USER_DIR )

if os.path.isdir( PLOT_DIR ) :
    shutil.rmtree( PLOT_DIR )
    os.mkdir( PLOT_DIR )
    os.mkdir( THUM_DIR )

dataPath = "{0}/{1}/identity.json".format( SCRIPT_DIR, "json" )
parameterPath = "{0}/{1}/parameter_default.json".format( SCRIPT_DIR, "json")
if os.path.isfile( dataPath ) :
    with open( dataPath, 'r' ) as f :
        dataJson = json.load( f )
if os.path.isfile( parameterPath ) :
    with open( parameterPath, 'r' ) as f :
        parameterJson = json.load( f )

##########
# function
def clean_dir( path ) :
    r = glob.glob( path + "/*" )
    for i in r:
        os.remove(i)

def update_mod( collection, query ) :
    yarrdb[collection].update( query, 
                               { '$set' : { 'sys.rev' : int( yarrdb[collection].find_one( query )['sys']['rev'] + 1 ), 
                                            'sys.mts' : datetime.datetime.utcnow() }}, 
                                 multi=True )

#################################################################
# check python version
if not args.fpython in [ 2, 3 ] :
    print( "# Set python version by setting.sh" )
print( "# Use python : version " + str(args.fpython) + "\n")

# exit if not enable to use ROOT SW
if not DOROOT :
    print( "# Can not use ROOT software, exit ..." )
    sys.exit()     
i=0
print("--- stage list ---")
for stage in listset.stage :
    print( str(i) + " : " + stage )
    i+=1
print( " " )

# enter stage number
num = ""
while num == "" :
    if args.fpython == 2 :
        num = raw_input( "# Type stage number >> " ) #python2
    elif args.fpython == 3 :
        num = str(input( "# Type stage number >> " )) #python3
if not num.isdigit() :
    print( "# Enter STAGE NUMBER, exist ... ")
    sys.exit()
if not int(num) < len(listset.stage) :
    print( "# Enter STAGE NUMBER, exist ... ")
    sys.exit()
dataJson.update({ "stage" : listset.stage[int(num)]}) 
print("# ok.\n")

# serial number
serialNumber = ""
while serialNumber == "" :
    if args.fpython == 2 :
        serialNumber = raw_input( "# Type serial number of module >> " ) #python2
    elif args.fpython == 3 :
        serialNumber = str(input( "# Type serial number of module >> " )) #python3
dataJson.update({ "serialNumber" : serialNumber }) 
query = { "serialNumber" : dataJson['serialNumber'] }
if not yarrdb.component.find( query ).count() == 1 :
    print( "# Not found module " + dataJson['serialNumber'] + ", exit ... " )
    sys.exit()     
thisComponent = yarrdb.component.find_one( query )
print("# found.\n")

# Check the informations of the summary result 
print( "# Start to add summary plots " )    
print( " " )
print( "      < General information >       " )
print( " ---------------------------------- " )
print( "  serialNumber : " + str(dataJson['serialNumber']) )
print( "  stage        : " + str(dataJson['stage']) )
print( "  institution  : " + str(dataJson['institution']) )
print( "  userIdentity : " + str(dataJson['userIdentity']) )
print( " ---------------------------------- " )
print( " " )
answer = ""
while answer == "" :
    if args.fpython == 2 :
        answer = raw_input( "# Continue to check results of this module? Type 'y' if continue >> " ) #python2
    elif args.fpython == 3 :
        answer = str(input( "# Continue to check results of this module? Type 'y' if continue >> " )) #python3
if not answer == "y" : 
    print( "# exit ... " )
    sys.exit()
print( " " )

# Check chip entries
query = { "parent" : str(thisComponent['_id']) }
child_entries = yarrdb.childParentRelation.find( query )
chips = []
chips.append({ "component" : str(thisComponent['_id']) })
for child in child_entries :
    chips.append({ "component" : child['child'] })

# Check last run for each scan
i=0
scannum = {}
runNumbers = {}
scanList = [ "digitalscan", "analogscan", "thresholdscan", "totscan", "noisescan", "selftrigger" ] 

for scan in scanList :
    runNumbers.update({ scan : {} })
    scannum.update({ i : scan })
    i+=1
    runNumber = 0
    query = { '$or' : chips, "stage" : dataJson['stage'], "testType" : scan }
    run_entries = yarrdb.componentTestRun.find( query ).sort( "runNumber", pymongo.ASCENDING )
    for run in run_entries :
        query = { "_id" : ObjectId(run['testRun']), "institution" : dataJson['institution'], "userIdentity" : dataJson['userIdentity'] }
        thisRun = yarrdb.testRun.find_one( query )
        if thisRun :
            dateTime = func.setTime( thisRun['date'] )
            runNumbers[scan].update({ thisRun['runNumber'] : [ thisRun['_id'], dateTime ] })
            if thisRun['runNumber'] > runNumber :
                runNumber = thisRun['runNumber']
                dataJson.update({ scan : { "runNumber" : runNumber,
                                           "datetime"  : dateTime }})
answer = "first"
while not answer == "y" :
    if answer == "first" :
        pass
    elif not answer.isdigit() :
        print( "# Type NUMBER.\n" )
    elif not int(answer) in scannum :
        print( "# Type THE NUMBER BEFORE SCAN NAME.\n" )
    else :
        print( "  testType        : " + scannum[int(answer)] )
        print( "  Run number list : " )
        for n in sorted(runNumbers[scannum[int(answer)]].keys()) :
            print( "                    " + str(n) + " : " + runNumbers[scannum[int(answer)]][n][1] )
        print( " " )
        number = ""
        while number == "" :
            if args.fpython == 2 :
                number = raw_input( '# Enter run number from this list for summary plot. If you want not to select, type "N". >> ' ) #python2
            elif args.fpython == 3 :
                number = str(input( '# Enter run number from this list for summary plot. If you want not to select, type "N". >> ' )) #python3
            if number == "N" :
                number = None
            elif not number.isdigit() :
                print("# Enter NUMBER.")
                number = ""
            elif not int(number) in runNumbers[scannum[int(answer)]] :
                print( "# Enter RUN NUMBER from this LIST." )
                number = ""
            else : 
                number = int(number)
        print( " " )
        if number :
            query = { "_id" : runNumbers[scannum[int(answer)]][number][0] }
            thisRun = yarrdb.testRun.find_one( query )
            if thisRun :
                dateTime = func.setTime( thisRun['date'] )
                runNumber = thisRun['runNumber']
                dataJson.update({ scannum[int(answer)] : { "runNumber" : runNumber,
                                                           "datetime"  : dateTime }})
        else :
                dataJson.pop( scannum[int(answer)] )

    print( "      < Confirm information >       " )
    print( " ---------------------------------- " )
    for i in [ 0, 1, 2, 3, 4, 5 ] :
        print( "  " + str(i) + ", " + scannum[i] ) 
        if dataJson.get(scannum[i]) :
            print( "  runNumber   : " + str(dataJson[scannum[i]].get( 'runNumber', "None" )))
            print( "  datetime    : " + str(dataJson[scannum[i]].get( 'datetime', "None" )))
        else :
            print( "  data        : None" )
            dataJson.update({ scannum[i] : { "runNumber" : None } }) 
        print( " ---------------------------------- \n" )
    answer = "" 
    while answer == "" :
        if args.fpython == 2 :
            answer = raw_input( "# Type 'y' if continue to make plots, or type the number before scan name if change run number >> " ) #python2
        elif args.fpython == 3 :
            answer = str(input( "# Type 'y' if continue to make plots, or type the number before scan name if change run number >> " )) #python3
    print( " " )

runIds = {}
for scan in listset.scan :
    runIds.update({ scan : [] })
    if dataJson[scan].get('runNumber',None) :
        query = { '$or' : chips, "stage" : dataJson['stage'], "testType" : scan, "runNumber" : dataJson[scan]['runNumber'] }
        run_entries = yarrdb.componentTestRun.find( query )
        for run in run_entries :
            query = { "_id" : ObjectId(run['testRun']), "institution" : dataJson['institution'], "userIdentity" : dataJson['userIdentity'] }
            thisRun = yarrdb.testRun.find_one( query )
            if thisRun : 
                runIds[scan].append({ "_id" : thisRun['_id'] })

# make histogram
print( "# Start to make histograms.\n" )
for scan in listset.scan :
    print( "--- Start : " + scan + " ---" )
    clean_dir( DAT_DIR )
    if not runIds[scan] == [] :
        query = { '$or' : runIds[scan] }
        run_entries = yarrdb.testRun.find( query )
        for thisRun in run_entries :
            data_entries = thisRun['attachments']
            for data in data_entries :
                if data['contentType'] == "dat" :
                    f = open( '{0}/{1}_{2}_{3}.dat'.format( DAT_DIR, thisRun['runNumber'], data['filename'].rsplit("_",2)[1], data['filename'].rsplit("_",2)[2] ), "wb" )
                    f.write( fs.get(ObjectId(data['code']) ).read())
                    f.close()
        mapList = {}
        for mapType in listset.scan[thisRun['testType']] :
            mapList.update({ mapType[0] : True })
        root.drawScan( thisRun['testType'], str(thisRun['runNumber']), False, 0, mapList )
        print( "done. " )
    else :
        print( "failure. " )
    print( "--- Finish : " + scan + " ---\n" )

print( "# Finish to make histograms of all scans.\n" )
if args.fpython == 2 :
    if not raw_input( "# Continue to insert plots into Database? Type 'y' if continue >> " ) == "y" : #python2
        print( "# exit ... " )
        sys.exit()     
elif args.fpython == 3 :
    if not str(input( "# Continue to insert plots into Database? Type 'y' if continue >> " )) == "y" : #python3
        print( "# exit ... " )
        sys.exit()     

# insert testRun and componentTestRun
for scan in listset.scan :
    testRuns = []
    if not runIds[scan] == [] :
        for runId in runIds[scan] :
            testRuns.append({ "testRun" : str(runId['_id']) })
        query = { "component" : str(thisComponent['_id']), '$or' : testRuns }
        if yarrdb.componentTestRun.find( query ).count() == 1 :
            RunId = yarrdb.componentTestRun.find_one( query )['testRun']
        elif yarrdb.componentTestRun.find( query ).count() == 0 :
            query = { '$or' : runIds[scan] }
            moduleTestRun = yarrdb.testRun.find_one( query )
            runid = moduleTestRun.pop( '_id', None )
            query = { "testRun" : str(runid) }
            moduleComponentTestRun = yarrdb.componentTestRun.find_one( query )
            moduleComponentTestRun.pop( '_id', None )
            moduleTestRun.update({ "attachments" : [] })
            moduleTestRun.update({ "sys" : { "rev" : 0,
                                             "cts" : datetime.datetime.utcnow(),
                                             "mts" : datetime.datetime.utcnow() }})
            RunId = str(yarrdb.testRun.insert( moduleTestRun ))
            moduleComponentTestRun.update({ "component" : str(thisComponent['_id']),
                                            "testRun"   : RunId,
                                            "sys"         : { "rev" : 0,
                                                              "cts" : datetime.datetime.utcnow(),
                                                              "mts" : datetime.datetime.utcnow() }})
            moduleComponentRunId = yarrdb.componentTestRun.insert( moduleComponentTestRun )
        else : 
            print("# something wrong, exit ... ")
            sys.exit()

        # add attachments into module TestRun
        query = { "component" : str(thisComponent['_id']), "testRun" : RunId }
        thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
        query = { "_id" : ObjectId(RunId) }
        thisRun = yarrdb.testRun.find_one( query )
        for mapType in listset.scan[thisRun['testType']] :
            for i in [ "1", "2" ] :
                if i == "1" :
                    filename = "{0}_{1}_Dist".format( dataJson['serialNumber'], mapType[0] )
                if i == "2" :
                    filename = "{0}_{1}".format( dataJson['serialNumber'], mapType[0] )
                for attachment in yarrdb.testRun.find_one( query )['attachments'] :
                    if filename == attachment.get('filename') :
                        fs.delete( ObjectId(attachment.get('code')) )
                        yarrdb.testRun.update( query, { '$pull' : { "attachments" : { "code" : attachment.get('code') }}}) 
                filepath = PLOT_DIR + "/" + thisRun['testType'] + "/" + str(thisRun['runNumber']) + "_" + mapType[0] + "_{}.png".format(i)
                binary_image = open( filepath, 'rb' )
                image = fs.put( binary_image.read(), filename=filename )
                binary_image.close()
                yarrdb.testRun.update( query, { '$push' : { "attachments" : { "code" : str(image),
                                                                              "dateTime" : datetime.datetime.utcnow(),
                                                                              "title" : "title",
                                                                              "description" : "describe",
                                                                              "contentType" : "png",
                                                                              "filename" : filename }}}) 

        # change display bool
        components = [{ "component" : str(thisComponent['_id']) }]
        query = { "parent" : str(thisComponent['_id']) }
        for child in yarrdb.childParentRelation.find( query ) :
            components.append({ "component" : child['child'] })
        query = { '$or' : components, "testType" : thisComponentTestRun['testType'], "stage" : thisComponentTestRun['stage'] }
        runids = []
        for run in yarrdb.componentTestRun.find( query ) :
            runids.append({ "_id" : ObjectId(run['testRun']) })
        query = { '$or' : runids, "display" : True }
        if not yarrdb.testRun.find( query ).count() == 0 :
            update_mod( "testRun", query ) 
            yarrdb.testRun.update( query, { '$set' : { "display" : False }}, multi=True )
        query.pop("display",None)
        query.update({ "runNumber" : thisRun['runNumber'], "institution" : thisRun['institution'], "userIdentity" : thisRun['userIdentity'] })
        update_mod( "testRun", query ) 
        yarrdb.testRun.update( query, { '$set' : { "display" : True }}, multi=True )

print( "Finish." )
