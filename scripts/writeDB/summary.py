"""
script for add summary plots
"""
##### import #####
import os, sys, pwd, glob, datetime, shutil, json, hashlib
import gridfs # gridfs system 
from   pymongo       import MongoClient, ASCENDING # use mongodb scheme
from   bson.objectid import ObjectId               # handle bson format
from   getpass       import getpass

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)) )
sys.path.append( SCRIPT_DIR )
sys.path.append( SCRIPT_DIR + "/src" )

# exit if not enable to use ROOT SW
try : 
    import root
except : 
    print( "[EXIT] Can not use ROOT software." )
    sys.exit()     

import listset
from   arguments import *   # Pass command line arguments into app.py

##### setting about dbs #####
args = getArgs()         
if args.username : url = "mongodb://" + args.username + ":" + args.password + "@" + args.host + ":" + str(args.port) 
else :             url = "mongodb://"                                             + args.host + ":" + str(args.port) 
client  = MongoClient( url )
yarrdb  = client[args.db]
userdb = client[args.userdb]
fs = gridfs.GridFS( yarrdb )

##### directories ##### 
TMP_DIR   = '/tmp/{}'.format( pwd.getpwuid( os.geteuid() ).pw_name ) 
THUM_DIR  = '{}/thumbnail'.format( TMP_DIR )
STAT_DIR  = '{}/static'.format( TMP_DIR )
JSON_DIR  = '{}/json'.format( TMP_DIR )

##### function #####
def make_dir() :
    if not os.path.isdir( TMP_DIR ) :
        os.mkdir( TMP_DIR )
    user_dir = TMP_DIR + "/localuser" 
    if not os.path.isdir( user_dir ) :
        os.mkdir( user_dir )

def clean_dir( dir_name ) :
    if os.path.isdir( dir_name ) : shutil.rmtree( dir_name )
    os.mkdir( dir_name )

def update_mod( collection, query ) :
    yarrdb[collection].update( query, 
                               { '$set' : { 'sys.rev' : int( yarrdb[collection].find_one( query )['sys']['rev'] + 1 ), 
                                            'sys.mts' : datetime.datetime.utcnow() }}, 
                                 multi=True )
def input_v( message ) :
    answer = ""
    if args.fpython == 2 : answer = raw_input( message ) 
    if args.fpython == 3 : answer =     input( message )
    return answer
def max_run( id_list ) :
    max_entry = {}  
    for entry in id_list :
        if entry['runNumber'] > max_entry.get('runNumber',0) : max_entry = entry
    return max_entry
def number2entry( runNumber, id_list ) :
    entry = {}
    for query in id_list :
        if runNumber == query['runNumber'] : entry = query
    return entry
#################################################################
### password required
print( "%%% This function can be used by people with administrator authority %%%" )
print( " " )
username = input_v( "# Username of administrator account >> " ) 
password = getpass( "# Password of administrator account >> " )
password = hashlib.md5(password.encode("utf-8")).hexdigest()
print( " " )

query = { "userName" : username }
user = userdb.user.find_one( query )
if not user :
    print(" ")
    print("[EXIT] Not found the user.")
    sys.exit()     
if not user['authority'] == 7 :
    print(" ")
    print("[EXIT] Not user with administrator authority.")
    sys.exit()     
if not user['passWord'] == password :
    print(" ")
    print("[EXIT] Not match password.")
    sys.exit()     

### setup for add summary plot
make_dir()

plot_dir = TMP_DIR + "/localuser/plot"
clean_dir( plot_dir )
 
jsonFile = JSON_DIR + "/localuser_parameter.json"
if not os.path.isfile( jsonFile ) :
    jsonFile_default = SCRIPT_DIR + "/json/parameter_default.json"
    with open( jsonFile_default, 'r' ) as f : jsonData_default = json.load( f )
    with open( jsonFile,         'w' ) as f : json.dump( jsonData_default, f, indent=4 )

answer = ""
while answer == "" :
    answer = input_v( "# Type 'y' if conitinue to add summary plot >> " )
if not answer == 'y' :
    print(" ")
    print("[EXIT]")
    sys.exit()     

### serial number
if yarrdb.component.find({ "serialNumber" : str(args.serial) }).count() == 1 :
    serialNumber = str(args.serial)
else :
    if args.serial : print( "\n[WARNING] {} is not found. ".format( args.serial ) )
    print(" ")
    serialNumber = ""
    while serialNumber == "" :
        serialNumber = input_v( "# Enter serial number of module >> " ) 

query = { "serialNumber" : serialNumber }
if not yarrdb.component.find( query ).count() == 1 :
    print( "[EXIT] Not found module " + serialNumber )
    sys.exit()     

thisComponent = yarrdb.component.find_one( query )
chips = []
componentId = str(thisComponent['_id'])
query = { "parent" : componentId }
child_entries = yarrdb.childParentRelation.find( query )
for child in child_entries :
    chips.append({ "component" : child['child'] })

### select stage
query = { '$or' : chips }
run_entries = yarrdb.componentTestRun.find( query )
stages = []
for run in run_entries :
    stages.append( run.get('stage') )
stages = list(set(stages))

if str(args.stage) in stages :
    stage = str(args.stage)
else :
    if args.stage : print( "\n[WARNING] {} is not found, select stage from the list.".format( args.stage ) )

    print(" ")
    print("----- stage list -----")
    for stage in stages :
        print( " {0:<3}".format(stages.index(stage)) + " : " + stage )
    print(" ")
    stage_num = ""
    while stage_num == "" :
        num = ""
        while num == "" :
            num = input_v( "# Enter stage number >> " ) 
        if not num.isdigit() : 
            print( "[WARNING] Input item is not number, enter agein. ")
        elif not int(num) < len(stages) : 
            print( "[WARNING] Input number is not included in the stage list, enter agein. ")
        else :
            stage_num = int(num)
    
    stage = stages[stage_num]
    
### Check the informations of the summary result 
print( " " )
print( "%%% Start to add summary plots %%%" )    
print( "----------------------------------" )
print( " serialNumber : {}".format(serialNumber) )
print( " stage        : {}".format(stage) )
print( "----------------------------------" )
print( " " )

answer = ""
while answer == "" :
    answer = input_v( "# Type 'y' if continue >> " ) 
if not answer == "y" : 
    print( "[EXIT]" )
    sys.exit()

### Check current summary plot
runNumbers = {}
summaryList = { "before" : {}, "after" : {} }
scanList = [ "digitalscan", "analogscan", "thresholdscan", "totscan", "noisescan", "selftrigger" ] 
keys = [ "runNumber", "institution", "userIdentity", "testType" ]
current = False
for scan in scanList :
    runNumbers.update({ scan : [] })
    summaryList['before'].update({ scan : {} })
    summaryList['after' ].update({ scan : {} })
    query = { '$or' : chips + [{ "component" : componentId }], "stage" : stage, "testType" : scan }
    run_entries = yarrdb.componentTestRun.find( query )
    for run in run_entries :
        query = { "_id" : ObjectId(run['testRun']) }
        thisRun = yarrdb.testRun.find_one( query )
        query_id = dict( [ (key, thisRun[key]) for key in keys ] )
        if query_id in runNumbers[scan] : continue
        runNumbers[scan].append( query_id ) 
        if thisRun.get( 'display' ) : 
            summaryList['before'].update({ scan : query_id })
            summaryList['after' ].update({ scan : query_id })
            current = True

if not current :
    print( " " )
    print( "%%% Current summary plot is not registered, then latest test will be added for summary %%%" )    
    for scan in scanList :
        thisRun = max_run( runNumbers[scan] )
        if thisRun : summaryList['after'].update({ scan : thisRun })

print( " " )
answer = ""
while answer == "" :
    print( "%%%         Change summary plot as below          %%%" )    
    print( "-----------------------------------------------------" )
    print( " {0:^3} {1:^20} : {2:^10} -> {3:^10} ".format( "num", "test type", "current", "change" ))
    for scan in scanList :
        if summaryList['before'][scan] == summaryList['after'][scan] :
            print( " {0:<3} {1:<20} : {2:^10} -> {3:^10} ".format( str(scanList.index(scan))+",", scan, summaryList['before'][scan].get('runNumber',"None"), "No change" ))
        else :
            print( " {0:<3} {1:<20} : {2:^10} -> {3:^10} ".format( str(scanList.index(scan))+",", scan, summaryList['before'][scan].get('runNumber',"None"), summaryList['after'][scan].get('runNumber',"None") ))
    print( "-----------------------------------------------------" )
    print( " " )

    number = ""
    while number == "" :
        answer_num = ""
        while answer_num == "" :
            answer_num = input_v( "# Type 'y' if continue, or type the number before scan name if change summary run  >> " )
        if answer_num == 'y' : 
            number = "y"
        elif not answer_num.isdigit() :
            print( "[WARNING] Input item is not number, enter agein. ")
        elif not int(answer_num) < len(scanList) : 
            print( "[WARNING] Input number is not before scan name, enter agein. ")
        else :
            number = int(answer_num)

    if number == 'y' : 
        answer = "y"
        continue

    scan = scanList[number]
    print( " " )
    print( "--------------------------- run number list ({0:^19}) ---------------------------".format( scan ) )
    for entry in runNumbers[scan] :
        print( " {0:<3} runNumber : {1:^5} userIdentity : {2:^20} institution : {3:^20} ".format( str(runNumbers[scan].index( entry ))+",", str(entry['runNumber'])+",", entry['userIdentity']+",", entry['institution']+"," ))
    print( " " )
    run_num = ""
    while run_num == "" :
        answer_num = ""
        while answer_num == "" :
            answer_num = input_v( "# Enter the number before run number for summary, or type 'N' if not to select >> " )
        if answer_num == 'N' :
            summaryList['after'].update({ scan : {} })
            run_num = "N"
        elif not answer_num.isdigit() :
            print( "[WARNING] Input item is not number, enter agein. ")
        elif not int(answer_num) < len(runNumbers[scan]) : 
            print( "[WARNING] Input number is not before run number, enter agein. ")
        else :
            run_num = int(answer_num)
            summaryList['after'].update({ scan : runNumbers[scan][run_num] })

### Add comment
comments = {}
for scan in scanList :
    if summaryList['before'][scan] == summaryList['after'][scan] : continue
    if not summaryList['before'][scan] : continue
    
    print( " " )
    print( "%%%%%%%%%%%%%%%%%%%%%%%%%%%%" )
    print( "    {0:^20}    ".format(scan) )
    print( " {0:^10} -> {1:^10} ".format( summaryList['before'][scan].get('runNumber',"None"), summaryList['after'][scan].get('runNumber',"None") ))
    print( "%%%%%%%%%%%%%%%%%%%%%%%%%%%%" )
    print( " " )
    print( "%%%            There are already set summary plot in this scan           %%%" )
    print( "%%% You must leave a comment about the reason to remove/replace the plot %%%" )
    print( " " )
    print("----- comment list -----")
    for comment in listset.summary_comment :
        print( " {0:<3}".format(listset.summary_comment.index(comment)) + " : " + comment )
    print( " " )
    comment_num = ""
    while comment_num == "" :
        num = ""
        while num == "" :
            num = input_v( "# Enter comment number >> " ) 
        if not num.isdigit() : 
            print( "[WARNING] Input item is not number, enter agein. ")
        elif not int(num) < len(listset.summary_comment) : 
            print( "[WARNING] Input number is not included in the comment list, enter agein. ")
        else :
            comment_num = int(num)
    comments.update({ scan : listset.summary_comment[comment_num] })

### Confirmation

print( " " )
print( "%%%                           Confirmation                            %%%" )    
print( "-------------------------------------------------------------------------" )
print( " {0:^20} : {1:^10} -> {2:^10} : {3:^20} ".format( "test type", "current", "change", "comment" ))
for scan in scanList :
    if summaryList['before'][scan] == summaryList['after'][scan] :
        print( " {0:<20} : {1:^10} -> {2:^10} ".format( scan, summaryList['before'][scan].get('runNumber',"None"), "No change" ))
    elif not summaryList['before'][scan] :
        print( " {0:<20} : {1:^10} -> {2:^10} : {3:^20} ".format( scan, summaryList['before'][scan].get('runNumber',"None"), summaryList['after'][scan].get('runNumber',"None"), "-----" ))
    else :
        print( " {0:<20} : {1:^10} -> {2:^10} : {3:^20} ".format( scan, summaryList['before'][scan].get('runNumber',"None"), summaryList['after'][scan].get('runNumber',"None"), comments[scan] ))
print( "-------------------------------------------------------------------------" )
print( " " )

answer = ""
while answer == "" :
    answer = input_v( "# Type 'y' if conitinue to add summary plot >> " )
if not answer == 'y' :
    print(" ")
    print("[EXIT]")
    sys.exit()     

### Make histogram
print( "%%% Start to make histograms %%%" )
print( " " )
plotList = {}
for scan in scanList :

    if summaryList['before'][scan] == summaryList['after'][scan] : continue

    print( "--- Start : " + "{0:^20}".format(scan) + " ---" )
    
    dat_dir = TMP_DIR + "/localuser/dat"
    clean_dir( dat_dir )
 
    plotList.update({ scan : {} })
    if not summaryList['after'][scan] : 
        print( "--------------- done ---------------" )
        continue

    thisRun = summaryList['after'][scan]
    components = sorted( chips, key=lambda x:x['component'] )
    components = sorted( chips, key=lambda x:x['component'] )
    i=1
    chipIds = {}
    for component in components :
        if not component['component'] in chipIds :
            chipIds.update({ component['component'] : i })
            i+=1
    query = { '$or' : components, "runNumber" : thisRun['runNumber'], "testType" : scan, "stage" : stage }
    run_entries = yarrdb.componentTestRun.find( query )
    for run in run_entries :
        query = { "_id" : ObjectId( run['testRun'] )}
        query.update( summaryList['after'][scan] )
        chiprun = yarrdb.testRun.find_one( query )
        if chiprun :
            data_entries = chiprun['attachments']
            for data in data_entries :
                if data['contentType'] == "dat" :
                    f = open( '{0}/localuser/dat/{1}_{2}.dat'.format( TMP_DIR, 'chipId{}'.format(chipIds[run['component']]), data['filename'].rsplit("_",1)[1] ), 'wb' )
                    f.write( fs.get(ObjectId(data['code']) ).read())
                    f.close()
                    mapType = data['filename'].rsplit("_",1)[1]
                    plotList[scan].update({ mapType : { "draw" : True, "chips" : len(chipIds) } })

    root.localDrawScan( scan, plotList[scan] )
    print( "--------------- done ---------------" )

print( "%%% Finish to make histograms of all scans %%%" )
print( " " )

if not input_v( "# Continue to insert plots into Database? Type 'y' if continue >> " ) == "y" : #python2
    print( "[EXIT]" )
    sys.exit()     

### Insert data into Database
print( "%%% Start to insert data into database %%%" )
print( " " )
for scan in scanList :
    print( "--- Start : " + "{0:^20}".format(scan) + " ---" )

    if summaryList['before'][scan] == summaryList['after'][scan] : continue

    ### Insert testRun and componentTestRun
    runId = None
    if summaryList['after'][scan] : 

        query = summaryList['after'][scan]
        run_entries = yarrdb.testRun.find( query )
        runIds = []
        for run in run_entries :
            runIds.append({ "testRun" : str( run['_id'] ) })
        query = { '$or' : runIds, "component" : componentId }
        thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
        if thisComponentTestRun : 
            runId = thisComponentTestRun['testRun']
        else :
            query = runIds[0] 
            moduleComponentTestRun = yarrdb.componentTestRun.find_one( query )
            query = { "_id" : ObjectId(runIds[0]['testRun']) }
            moduleTestRun = yarrdb.testRun.find_one( query )
            moduleComponentTestRun.pop( '_id', None )
            moduleTestRun.pop( '_id', None )

            thistime = datetime.datetime.utcnow()
            moduleTestRun.update({ "attachments" : [] })
            moduleTestRun.update({ "sys" : { "rev" : 0,
                                             "cts" : thistime,
                                             "mts" : thistime }})
            runId = str(yarrdb.testRun.insert( moduleTestRun ))
            print( "Info in <testRun>: id {} has been inserted".format( runId ) )
            moduleComponentTestRun.update({ "component" : componentId,
                                            "testRun"   : runId,
                                            "sys"       : { "rev" : 0,
                                                            "cts" : thistime,
                                                            "mts" : thistime }})
            componentRunId = str(yarrdb.componentTestRun.insert( moduleComponentTestRun ) )
            print( "Info in <componentTestRun>: id {} has been inserted".format( componentRunId ) )

        ### add attachments into module TestRun
        query = { "component" : componentId, "testRun" : runId }
        thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
        query = { "_id" : ObjectId(runId) }
        thisRun = yarrdb.testRun.find_one( query )

        for mapType in plotList[scan] :
            if plotList[scan][mapType]['HistoType'] == 1 : continue
            url = {} 
            path = {}
            datadict = { "1" : "_Dist", "2" : "" }
            for i in datadict :
                filename = "{0}_{1}{2}".format( thisComponent['serialNumber'], mapType, datadict[i] )
                for attachment in thisRun['attachments'] :
                    if filename == attachment.get('filename') :
                        fs.delete( ObjectId(attachment.get('code')) )
                        yarrdb.testRun.update( query, { '$pull' : { "attachments" : { "code" : attachment.get('code') }}}) 
                        print( "Info in <testRun>: code {} has been pulled".format( str(attachment.get('code')) ) )

                filepath = "{0}/localuser/plot/{1}_{2}_{3}.png".format(TMP_DIR, str(thisRun['testType']), str(mapType), i)
                if os.path.isfile( filepath ) :
                    binary_image = open( filepath, 'rb' )
                    image = fs.put( binary_image.read(), filename="{}.png".format(filename) )
                    binary_image.close()
                    yarrdb.testRun.update( query, { '$push' : { "attachments" : { "code"        : str(image),
                                                                                  "dateTime"    : datetime.datetime.utcnow(),
                                                                                  "title"       : "title",
                                                                                  "description" : "describe",
                                                                                  "contentType" : "png",
                                                                                  "filename"    : filename }}}) 
                    print( "Info in <testRun>: code {} has been pushed".format( str(image) ) )

    ### remove "display : True" in current summary run
    if summaryList['before'][scan] :
        query_id = summaryList['before'][scan] 
        yarrdb.testRun.update( query_id, { '$set'  : { "display" : False }}, multi=True )
        print( "Info in <testRun>: run number {} has been set to false".format( query_id['runNumber'] ) )
        yarrdb.testRun.update( query_id, { '$push' : { 'comments' : { "userIdentity" : user['userIdentity'],
                                                                      "userid"       : str(user['_id']),
                                                                      "comment"      : comments[scan], 
                                                                      "after"        : runId,
                                                                      "datetime"     : datetime.datetime.utcnow(), 
                                                                      "institution"  : user['institution'],
                                                                      "description"  : "add_summary" }}}, multi=True )
        print( "Info in <testRun>: run number {} has been set comment".format( query_id['runNumber'] ) )
        update_mod( "testRun", query_id ) 

    query = { '$or' : chips + [{ "component" : componentId }], "stage" : stage, "testType" : scan }
    entries = yarrdb.componentTestRun.find( query )
    for entry in entries :
        query = { "_id" : ObjectId( entry['testRun'] )}
        thisRun = yarrdb.testRun.find_one( query )
        if thisRun.get( 'display' ) :
            query = { "_id" : thisRun['_id'] }
            yarrdb.testRun.update( query, { '$set' : { "display" : False }} )
            print( "Info in <testRun>: run number {} has been set to false".format( thisRun['runNumber'] ) )
            update_mod( "testRun", query )

    # add "display : True" in selected run
    if summaryList['after'][scan] :
        query_id = summaryList['after'][scan]
        yarrdb.testRun.update( query_id, { '$set' : { "display" : True }}, multi=True )
        print( "Info in <testRun>: run number {} has been set to true".format( query_id['runNumber'] ) )
        update_mod( "testRun", query_id ) 
    print( "--------------- done ---------------" )

print( "%%% Finish %%%" )
