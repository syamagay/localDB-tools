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
    print( "# Can not use ROOT software, exit ..." )
    sys.exit()     

import listset, func
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
print( "# Use python : version " + str(args.fpython) )
print( " " )
print( "%%% This function can be used by people with administrator authority %%%" )
print( " " )
username = input_v( "# Username of administrator account >> " ) 
password = getpass( "# Password of administrator account >> " )
password = hashlib.md5(password.encode("utf-8")).hexdigest()

query = { "userName" : username }
user = userdb.user.find_one( query )
if not user :
    print(" ")
    print("# Not found the user, exit ...")
    sys.exit()     
if not user['authority'] == 7 :
    print(" ")
    print("# Not user with administrator authority, exit ...")
    sys.exit()     
if not user['passWord'] == password :
    print(" ")
    print("# Not match password, exit ...")
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
 
print( " " )
print( "# Add summary plot ..." )
print( " " )

answer = ""
while answer == "" :
    answer = input_v( "# Type 'y' if conitinue to add summary plot >> " )
if not answer == 'y' :
    print(" ")
    print("# Exit ...")
    sys.exit()     

### serial number
print(" ")
serialNumber = ""
while serialNumber == "" :
    serialNumber = input_v( "# Enter serial number of module >> " ) 
query = { "serialNumber" : serialNumber }
if not yarrdb.component.find( query ).count() == 1 :
    print( "# Not found module " + serialNumber + ", exit ... " )
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

i=0
stageDict = {}
print(" ")
print("----- stage list -----")
for stage in stages :
    print( " {0:<3}".format(i) + " : " + stage )
    stageDict.update({ i : stage })
    i+=1
print( " " )
stage_num = ""
while stage_num == "" :
    num = ""
    while num == "" :
        num = input_v( "# Enter stage number >> " ) 
    print(" ")
    if not num.isdigit() : 
        print( "# Input item is not number, enter agein. ")
        print(" ")
    elif not int(num) < len(stages) : 
        print( "# Input number is not included in the stage list, enter agein. ")
        print(" ")
    else :
        stage_num = int(num)

stage = stageDict[stage_num]
    
### Check the informations of the summary result 
print( "# Start to add summary plots " )    
print( "----------------------------------" )
print( " serialNumber : {}".format(serialNumber) )
print( " stage        : {}".format(stage) )
print( "----------------------------------" )
print( " " )

answer = ""
while answer == "" :
    answer = input_v( "# Type 'y' if continue >> " ) 
if not answer == "y" : 
    print( "# Exit ... " )
    sys.exit()

### Check current summary plot
i=0
runNumbers = {}
summaryList = { "before" : {}, "after" : {} }
scanList = [ "digitalscan", "analogscan", "thresholdscan", "totscan", "noisescan", "selftrigger" ] 
keys = [ "runNumber", "institution", "userIdentity" ]
current = False
scanDict = {}
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
    scanDict.update({ i : scan })
    i+=1

if not current :
    print( " " )
    print( "%%% Current summary plot is not registered, then latest test will be added for summary %%%" )    
    for i in scanDict :
        scan = scanDict[i]
        thisRun = max_run( runNumbers[scan] )
        if thisRun : summaryList['after'].update({ scan : thisRun })

print( " " )
answer = ""
while answer == "" :
    print( "# Change summary plot as below " )    
    print( "-----------------------------------------------------" )
    print( " {0:^3} {1:^20} : {2:^10} -> {3:^10} ".format( "num", "test type", "current", "change" ))
    for i in scanDict :
        scan = scanDict[i]
        if summaryList['before'][scan] == summaryList['after'][scan] :
            print( " {0:<3} {1:<20} : {2:^10} -> {3:^10} ".format( str(i)+",", scanDict[i], summaryList['before'][scan].get('runNumber',"None"), "No change" ))
        else :
            print( " {0:<3} {1:<20} : {2:^10} -> {3:^10} ".format( str(i)+",", scanDict[i], summaryList['before'][scan].get('runNumber',"None"), summaryList['after'][scan].get('runNumber',"None") ))
    print( "-----------------------------------------------------" )
    print( " " )

    number = ""
    while number == "" :
        answer_num = ""
        while answer_num == "" :
            answer_num = input_v( "# Type 'y' if continue, or type the number before scan name if change summary run  >> " )
        print( " " )
        if answer_num == 'y' : 
            number = "y"
        elif not answer_num.isdigit() :
            print( "# Input item is not number, enter agein. ")
            print( " " )
        elif not int(answer_num) < len(scanList) : 
            print( "# Input number is not before scan name, enter agein. ")
            print( " " )
        else :
            number = int(answer_num)

    if number == 'y' : 
        answer = "y"
        continue

    scan = scanDict[number]
    print( "# testType : {}".format(scan) )
    print( " " )
    print( "------------------------------------ run number list ------------------------------------" )
    for entry in runNumbers[scan] :
        print( " runNumber : {0:^5} userIdentity : {1:^20} institution : {2:^20} ".format( str(entry['runNumber'])+",", entry['userIdentity']+",", entry['institution']+"," ))
    print( " " )
    run_num = ""
    while run_num == "" :
        answer_num = ""
        while answer_num == "" :
            answer_num = input_v( "# Enter summary run number, or type 'N' if not to select >> " )
        print( " " )
        if answer_num == 'N' :
            summaryList['after'].update({ scan : {} })
            run_num = "N"
        elif not answer_num.isdigit() :
            print( "# Input item is not number, enter agein. ")
            print( " " )
        elif not number2entry( int(answer_num), runNumbers[scan] )  in runNumbers[scan]  : 
            print( "# Input number is not included in run number list, enter agein. ")
            print( " " )
        else :
            run_num = int(answer_num)
            summaryList['after'].update({ scan : number2entry(run_num, runNumbers[scan]) })

### Add comment
comments = {}
for scan in scanList :
    if summaryList['before'][scan] == summaryList['after'][scan] : continue
    if not summaryList['before'][scan] : continue
    
    print( "%%%%%%%%%%%%%%%%%%%%%%%%%%%%" )
    print( "    {0:^20}    ".format(scan) )
    print( " " )
    print( " {0:^10} -> {1:^10} ".format( summaryList['before'][scan].get('runNumber',"None"), summaryList['after'][scan].get('runNumber',"None") ))
    print( "%%%%%%%%%%%%%%%%%%%%%%%%%%%%" )
    print( " " )
    print( "%%%            There are already set summary plot in this scan           %%%" )
    print( "%%% You must leave a comment about the reason to remove/replace the plot %%%" )
    print( " " )
    print("----- comment list -----")
    i=0
    commentDict = {}
    for comment in listset.summary_comment :
        print( " {0:<3}".format(i) + " : " + comment )
        commentDict.update({ i : comment })
        i+=1
    print( " " )
    comment_num = ""
    while comment_num == "" :
        num = ""
        while num == "" :
            num = input_v( "# Enter comment number >> " ) 
        print(" ")
        if not num.isdigit() : 
            print( "# Input item is not number, enter agein. ")
            print(" ")
        elif not int(num) < len(stages) : 
            print( "# Input number is not included in the comment list, enter agein. ")
            print(" ")
        else :
            comment_num = int(num)
    comments.update({ scan : commentDict[comment_num] })

### Confirmation

print( "# Confirmation " )    
print( "-----------------------------------------------------------------------------" )
print( " {0:^3} {1:^20} : {2:^10} -> {3:^10} : {4:^20} ".format( "num", "test type", "current", "change", "comment" ))
for i in scanDict :
    scan = scanDict[i]
    if summaryList['before'][scan] == summaryList['after'][scan] :
        print( " {0:<3} {1:<20} : {2:^10} -> {3:^10} ".format( str(i)+",", scanDict[i], summaryList['before'][scan].get('runNumber',"None"), "No change" ))
    elif not summaryList['before'][scan] :
        print( " {0:<3} {1:<20} : {2:^10} -> {3:^10} : {4:^20} ".format( str(i)+",", scanDict[i], summaryList['before'][scan].get('runNumber',"None"), summaryList['after'][scan].get('runNumber',"None"), "-----" ))
    else :
        print( " {0:<3} {1:<20} : {2:^10} -> {3:^10} : {4:^20} ".format( str(i)+",", scanDict[i], summaryList['before'][scan].get('runNumber',"None"), summaryList['after'][scan].get('runNumber',"None"), comments[scan] ))
print( "-----------------------------------------------------------------------------" )
print( " " )

### Make histogram
print( "# Start to make histograms.\n" )
plotList = {}
for scan in scanList :
    print( "--- Start : " + "{0:^20}".format(scan) + " ---" )
    
    dat_dir = TMP_DIR + "/localuser/dat"
    clean_dir( dat_dir )
 
    plotList.update({ scan : {} })
    if not summaryList['after'][scan] : continue

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

print( "# Finish to make histograms of all scans.\n" )

if not input_v( "# Continue to insert plots into Database? Type 'y' if continue >> " ) == "y" : #python2
    print( "# exit ... " )
    sys.exit()     

### Insert testRun and componentTestRun
for scan in scanList :

    if not summaryList['after'][scan] : continue

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
        moduleComponentTestRun.update({ "component" : componentId,
                                        "testRun"   : runId,
                                        "sys"       : { "rev" : 0,
                                                        "cts" : thistime,
                                                        "mts" : thistime }})
        yarrdb.componentTestRun.insert( moduleComponentTestRun )

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
    ### remove "display : True" in current summary run
    if summaryList['before'][scan] :
        query_id = summaryList['before'][scan] 
        yarrdb.testRun.update( query_id, { '$set' : { "display" : False }}, multi=True )

###########
#        yarrdb.testRun.update( query_id, { '$push' : { 'comments' : [{ "user"        : session['userIdentity'],
#                                                                       "userid"      : session['uuid'],
#                                                                       "comment"     : session['summaryList']['after'][scan]['comment'], 
#                                                                       "after"       : session['summaryList']['after'][scan]['runId'],
#                                                                       "datetime"    : datetime.datetime.utcnow(), 
#                                                                       "institution" : session['institution'],
#                                                                       "description" : "add_summary" }] }}, multi=True )
#        update_mod( "testRun", query_id ) 
#
#    query = { "component" : componentId, "stage" : session['stage'], "testType" : scan }
#    entries = mongo.db.componentTestRun.find( query )
#    for entry in entries :
#        query = { "_id" : ObjectId( entry['testRun'] )}
#        thisRun = mongo.db.testRun.find_one( query )
#        keys = [ "runNumber", "institution", "userIdentity", "testType" ]
#        query_id = dict( [ (key, thisRun[key]) for key in keys ] )
#        run_entries = mongo.db.testRun.find( query_id )
#        for run in run_entries :
#            if run.get( 'display' ) :
#                query = { "_id" : run['_id'] }
#                mongo.db.testRun.update( query, { '$set' : { "display" : False }} )
#                update_mod( "testRun", query )
#
#
#        # change display bool
#        components = [{ "component" : str(thisComponent['_id']) }]
#        query = { "parent" : str(thisComponent['_id']) }
#        for child in yarrdb.childParentRelation.find( query ) :
#            components.append({ "component" : child['child'] })
#        query = { '$or' : components, "testType" : thisComponentTestRun['testType'], "stage" : thisComponentTestRun['stage'] }
#        runids = []
#        for run in yarrdb.componentTestRun.find( query ) :
#            runids.append({ "_id" : ObjectId(run['testRun']) })
#        query = { '$or' : runids, "display" : True }
#        if not yarrdb.testRun.find( query ).count() == 0 :
#            update_mod( "testRun", query ) 
#            yarrdb.testRun.update( query, { '$set' : { "display" : False }}, multi=True )
#        query.pop("display",None)
#        query.update({ "runNumber" : thisRun['runNumber'], "institution" : thisRun['institution'], "userIdentity" : thisRun['userIdentity'] })
#        update_mod( "testRun", query ) 
#        yarrdb.testRun.update( query, { '$set' : { "display" : True }}, multi=True )
#
#print( "Finish." )
