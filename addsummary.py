try    : 
    import root
    DOROOT = True
except : 
    DOROOT = False 

import os, sys, pwd, glob, hashlib, datetime, shutil

# usersetting
import userset

# use mongodb scheme
import pymongo
from flask_pymongo import PyMongo
from pymongo import MongoClient

# handle bson format
from bson.objectid import ObjectId 
from bson.binary import BINARY_SUBTYPE

# image related module
import base64 # Base64 encoding scheme
import gridfs # gridfs system 
from werkzeug import secure_filename # for upload system
import img # binary to dataURI

# other function
import func, userfunc

#############
# set dbs
client = MongoClient( host='localhost', port=userset.PORT )
yarrdb = client['yarrdb']
localdb = client['yarrlocal']
fs = gridfs.GridFS( yarrdb )

##################
# path/to/save/dir 
USER = pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
PIC_DIR = '{}/upload'.format( USER_DIR )
DAT_DIR = '{}/dat'.format( USER_DIR )
PLOT_DIR = '{}/result'.format( USER_DIR )
STAT_DIR = '{}/static'.format( USER_DIR )

if os.path.isdir( PLOT_DIR ) :
    shutil.rmtree( PLOT_DIR )
    os.mkdir( PLOT_DIR )


scanList = { "selftrigger"   : [( "OccupancyMap-0", "#Hit" ),],
             "noisescan"     : [( "NoiseOccupancy","NoiseOccupancy" ), ( "NoiseMask", "NoiseMask" )],
             "totscan"       : [( "MeanTotMap", "Mean[ToT]" ),         ( "SigmaTotMap", "Sigma[ToT]" )],
             "thresholdscan" : [( "ThresholdMap", "Threshold[e]" ),    ( "NoiseMap", "Noise[e]" )],
             "digitalscan"   : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )],
             "analogscan"    : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )]}
stageList = [ "wirebond", "encapsulation" ]

dataJson = func.readJson("{}/module_runnumber.json".format( os.path.dirname(os.path.abspath(__file__)) )) 
parameterJson = func.readJson("{}/parameter_default.json".format( os.path.dirname(os.path.abspath(__file__)) )) 

def clean_dir( path ) :
    r = glob.glob( path + "/*" )
    for i in r:
        os.remove(i)

def fill_env( thisRun ) :
    env_dict = { "hv"    : thisRun.get( 'environment', { "key" : "value" } ).get( 'hv', "" ),
                 "cool"  : thisRun.get( 'environment', { "key" : "value" } ).get( 'cool', "" )}
    return env_dict
def update_mod( collection, query ) :
    yarrdb[collection].update( query, 
                               { '$set' : { 'sys.rev' : int( yarrdb[collection].find_one( query )['sys']['rev'] + 1 ), 
                                            'sys.mts' : datetime.datetime.utcnow() }}, 
                                 multi=True )

#################################################################

if not DOROOT :
    print( "# Can not use ROOT software, exit ..." )
    sys.exit()     

i=0
print("--- stage list ---")
for stage in stageList :
    print( str(i) + " : " + stage )
    i+=1
print( " " )
try :
    dataJson.update({ "stage" : stageList[int(raw_input( "# Type stage number >> " ))]}) #python2
    dataJson.update({ "stage" : stageList[int(input( "# Type stage number >> " ))]}) #python3
    print("# ok.")
    print( " " )
except :
    print( "# Enter STAGE NUMBER, exist ... ")
    sys.exit()     
dataJson.update({ "serialNumber" : raw_input( "# Type serial number of module >> " )}) #python2 
dataJson.update({ "serialNumber" : input( "# Type serial number of module >> " )}) #python3 
query = { "serialNumber" : dataJson['serialNumber'] }
if not yarrdb.component.find( query ).count() == 1 :
    print( "# Not found module " + dataJson['serialNumber'] + ", exit ... " )
    sys.exit()     
print("# found.")
print( " " )

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

if not raw_input( "# Are there any mistakes? Type 'y' if continue >> " ) == "y" : #python2
if not input( "# Are there any mistakes? Type 'y' if continue >> " ) == "y" : #python3
    print( "# exit ... " )
    sys.exit()     

query = { "serialNumber" : dataJson['serialNumber'] }
thisComponent = yarrdb.component.find_one( query )

query = { "parent" : str(thisComponent['_id']) }
child_entries = yarrdb.childParentRelation.find( query )
chips = []
chips.append({ "component" : str(thisComponent['_id']) })
for child in child_entries :
    chips.append({ "component" : child['child'] })

for scan in scanList :
    runNumber = 0
    runNumbers = {}
    query = { '$or' : chips, "stage" : dataJson['stage'], "testType" : scan }
    run_entries = yarrdb.componentTestRun.find( query )
    for run in run_entries :
        query = { "_id" : ObjectId(run['testRun']), "institution" : dataJson['institution'], "userIdentity" : dataJson['userIdentity'] }
        thisRun = yarrdb.testRun.find_one( query )
        dateTime = func.setTime( thisRun['date'] )
        runNumbers.update({ thisRun['runNumber'] : [ thisRun['_id'], dateTime ] })
        if thisRun['runNumber'] > runNumber :
            runNumber = thisRun['runNumber']
            dataJson.update({ scan : { "runNumber" : runNumber,
                                       "datetime"  : dateTime }})
    print( " " )
    print( "      < " + scan + " >       " )
    print( " ---------------------------------- " )
    if dataJson.get(scan) :
        print( "  runNumber   : " + str(dataJson[scan].get( 'runNumber', "None" )) + " (last run)")
        print( "  datetime    : " + str(dataJson[scan].get( 'datetime', "None" )))
    else :
        print( "  data        : None" )
    print( " ---------------------------------- " )
    print( " " )
    answer = raw_input( "# Type 'y' if continue, or type 'c' if change number >> " ) #python2
    answer = input( "# Type 'y' if continue, or type 'c' if change number >> " ) #python3
    if answer == "c" :
        print( " " )
        print( "--- Run number list ---" )
        for n in runNumbers :
            print( str(n) + " : " + runNumbers[n][1] )
        print( " " )
        number = int(raw_input( "# Enter run number from this list for summary plot >> " )) #python2
        number = int(input( "# Enter run number from this list for summary plot >> " )) #python3 
        if not number in runNumbers :
            print( "# Enter RUN NUMBER from this LIST, exit ... " )
            sys.exit()     
 
        dataJson[scan]['runNumber'] = number
        query = { "_id" : runNumbers[number][0] }
        thisRun = yarrdb.testRun.find_one( query )
        dateTime = func.setTime( thisRun['date'] )
        runNumber = thisRun['runNumber']
        dataJson.update({ scan : { "runNumber" : runNumber,
                                   "datetime"  : dateTime }})
        print( " " )
        print( "      < " + scan + " >       " )
        print( " ---------------------------------- " )
        if dataJson.get(scan) :
            print( "  runNumber   : " + str(dataJson[scan].get( 'runNumber', "None" )))
            print( "  datetime    : " + str(dataJson[scan].get( 'datetime', "None" )))
        print( " ---------------------------------- " )
        print( " " )
        if not raw_input( "# Type 'y' if continue >> " ) == "y" : #python2
        if not input( "# Type 'y' if continue >> " ) == "y" : #python3
            print( "# exit ... " )
            sys.exit()     
    elif not answer == "y" :
        print( "# exit ... " )
        sys.exit()     
        
print( " " )
print( "      < Confirm information >       " )
print( " ---------------------------------- " )
for scan in scanList :
    print( "  testType    : " + scan ) 
    if dataJson.get(scan) :
        print( "  runNumber   : " + str(dataJson[scan].get( 'runNumber', "None" )))
        print( "  datetime    : " + str(dataJson[scan].get( 'datetime', "None" )))
    else :
        print( "  data        : None" )
    print( " ---------------------------------- " )
print( " " )

if not raw_input( "# Are there any mistakes? Type 'y' if continue >> " ) == "y" : #python2
if not input( "# Are there any mistakes? Type 'y' if continue >> " ) == "y" : #python3
    print( "# exit ... " )
    sys.exit()     

runIds = {}
for scan in scanList :
    runIds.update({ scan : [] })
    query = { '$or' : chips, "stage" : dataJson['stage'], "testType" : scan, "runNumber" : dataJson[scan]['runNumber'] }
    run_entries = yarrdb.componentTestRun.find( query )
    for run in run_entries :
        query = { "_id" : ObjectId(run['testRun']), "institution" : dataJson['institution'], "userIdentity" : dataJson['userIdentity'] }
        thisRun = yarrdb.testRun.find_one( query )
        if thisRun : 
            runIds[scan].append({ "_id" : thisRun['_id'] })

# make histogram
print( "# Start to make histograms." )
print( " " )
for scan in scanList :
    print( "--- Start : " + scan + " ---" )
    clean_dir( DAT_DIR )
    if not runIds[scan] == [] :
        query = { '$or' : runIds[scan] }
        run_entries = yarrdb.testRun.find( query )
        for thisRun in run_entries :
            env_dict = fill_env( thisRun ) 
            data_entries = thisRun['attachments']
            for data in data_entries :
                if data['contentType'] == "dat" :
                    f = open( '{0}/{1}_{2}_{3}.dat'.format( DAT_DIR, thisRun['runNumber'], data['filename'].rsplit("_",2)[1], data['filename'].rsplit("_",2)[2] ), "wb" )
                    f.write( fs.get(ObjectId(data['code']) ).read())
                    f.close()
        mapList = {}
        for mapType in scanList[thisRun['testType']] :
            mapList.update({ mapType[0] : True })
        root.drawScan( thisRun['testType'], str(thisRun['runNumber']), False, 0, mapList )
        print( "done. " )
    else :
        print( "# Not make. " )
    print( "--- Finish : " + scan + " ---" )
    print( " " )

print( "# Finish to make histograms of all scans." )
if not raw_input( "# Continue to insert plots into Database? Type 'y' if continue >> " ) == "y" : #python2
if not input( "# Continue to insert plots into Database? Type 'y' if continue >> " ) == "y" : #python3
    print( "# exit ... " )
    sys.exit()     

# insert testRun and componentTestRun
for scan in scanList :
    testRuns = []
    if not runIds[scan] == [] :
        for runId in runIds[scan] :
            testRuns.append({ "testRun" : str(runId['_id']) })
        query = { "component" : str(thisComponent['_id']), '$or' : testRuns }
        if yarrdb.componentTestRun.find( query ).count() == 1 :
            RunId = yarrdb.componentTestRun.find_one( query )['testRun']
        elif yarrdb.componentTestRun.find( query ).count() == 0 :
            query = { '$or' : runIds[scan] }
            docs = { "_id"         : 0,
                     "sys"         : 0 }
            moduleTestRun = yarrdb.testRun.find_one( query, docs )
            moduleTestRun.update({ "attachments" : [] })
            moduleTestRun.update({ "sys" : { "rev" : 0,
                                             "cts" : datetime.datetime.utcnow(),
                                             "mts" : datetime.datetime.utcnow() }})
            RunId = str(yarrdb.testRun.insert( moduleTestRun ))
            moduleComponentTestRun = { "component"   : str(thisComponent['_id']),
                                       "testType"    : moduleTestRun['testType'],
                                       "testRun"     : RunId,
                                       "stage"       : dataJson['stage'],
                                       "runNumber"   : moduleTestRun['runNumber'],
                                       "sys"         : { "rev" : 0,
                                                         "cts" : datetime.datetime.utcnow(),
                                                         "mts" : datetime.datetime.utcnow() }} 
            moduleComponentRunId = yarrdb.componentTestRun.insert( moduleComponentTestRun )
        else : 
            print("# something wrong, exit ... ")
            sys.exit()

        # add attachments into module TestRun
        query = { "component" : str(thisComponent['_id']), "testRun" : RunId }
        thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
        query = { "_id" : ObjectId(RunId) }
        thisRun = yarrdb.testRun.find_one( query )
        for mapType in scanList[thisRun['testType']] :
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

