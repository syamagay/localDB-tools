import os, pwd, glob, sys, json, re, shutil
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append( APP_DIR )
SCRIPT_DIR = APP_DIR + "/scripts"

try    : 
    import root
    DOROOT = True
except : 
    DOROOT = False 

from flask import url_for, session  # use Flask scheme
from pymongo import MongoClient, DESCENDING  # use mongodb scheme
from bson.objectid import ObjectId  # handle bson format

# image related module
import base64 # Base64 encoding scheme
import gridfs # gridfs system 
from PIL import Image
import io

# other function
import func, listset
from arguments import *   # Pass command line arguments into app.py

##################
# path/to/save/dir 
TMP_DIR   = '/tmp/{}'.format( pwd.getpwuid( os.geteuid() ).pw_name ) 
PIC_DIR   = '{}/upload'.format( TMP_DIR )
THUM_DIR  = '{}/thumbnail'.format( TMP_DIR )
STAT_DIR  = '{}/static'.format( TMP_DIR )
JSON_DIR  = '{}/json'.format( TMP_DIR )

#############
# set dbs
args = getArgs()         
if args.username is None : url = "mongodb://"                                             + args.host + ":" + str(args.port) 
else :                     url = "mongodb://" + args.username + ":" + args.password + "@" + args.host + ":" + str(args.port) 
client  = MongoClient( url )
yarrdb  = client[args.db]
localdb = client[args.userdb]
fs = gridfs.GridFS( yarrdb )

######################################################################

def clean_dir( dir_name ) :
    if os.path.isdir( dir_name ) : shutil.rmtree( dir_name )
    os.mkdir( dir_name )

def fill_env( thisComponentTestRun ) :
    env_list = thisComponentTestRun.get('environments',[])
    env_dict = { "list" : env_list,
                 "num"  : len(env_list) }
    return env_dict

######################################################################

def fill_photoDisplay( thisComponent ) :
    photoDisplay = []
    if "attachments" in thisComponent : 
        data_entries = thisComponent['attachments']
        for data in data_entries :
            if ( data.get( 'imageType' ) == "image" ) and ( data.get( 'display' ) == True ) :
                filePath = "{0}/{1}_{2}".format( STAT_DIR, data['photoNumber'], data['filename'] )
                f = open( filePath, 'wb' )
                f.write( fs.get(ObjectId(data['code'])).read() )
                f.close()
                url = url_for( 'upload.static', filename='{0}_{1}'.format( data['photoNumber'], data['filename'] ))
                photoDisplay.append({ "url"         : url,
                                      "code"        : data['code'],
                                      "photoNumber" : data['photoNumber'],
                                      "stage"       : data['stage'],
                                      "filename"    : data['filename'] })
    return photoDisplay

def fill_photoIndex( thisComponent ) :
    photoIndex = []
    if "attachments" in thisComponent : 
        data_entries = thisComponent['attachments']
        for data in data_entries :
            if data.get( 'imageType' ) == "image" :
                photoIndex.append({ "code"        : data['code'],
                                    "photoNumber" : data['photoNumber'],
                                    "datetime"    : func.setTime(data['dateTime']),
                                    "stage"       : data['stage'] })
    return photoIndex

def fill_photos( thisComponent, code ) :
    photos = {}
    if not code == "" :
        data_entries = thisComponent['attachments']
        for data in data_entries :
            if code == data.get( 'code' ) :
                filePath = "{0}/{1}".format( STAT_DIR, data['filename'] )
                f = open( filePath, 'wb' )
                f.write( fs.get(ObjectId(code)).read() )
                f.close()

                url = url_for( 'upload.static', filename='{}'.format( data['filename'] ))
                photos = { "url"         : url,
                           "code"        : data['code'],
                           "photoNumber" : data['photoNumber'],
                           "stage"       : data['stage'],
                           "display"     : data.get( 'display', "False" ),
                           "filename"    : data['filename'] }
    return photos

######################################################################

# summary plot for each stage in component page
def fill_summary( stages ) :

    query = { "_id" : ObjectId(session['this']) } 
    thisComponent = yarrdb.component.find_one( query )

    summaryIndex = []

    # pick runs with "display : True" for each stage
    entries = {}
    for stage in stages :
        entries.update({ stage : {} })

        for scan in listset.scan :
            entries[stage].update({ scan : None })
            query = { "component" : str(thisComponent['_id']), "stage" : stage, "testType" : scan }
            run_entries = yarrdb.componentTestRun.find( query )
            for run in run_entries :
                query = { "_id" : ObjectId(run['testRun']) }
                thisRun = yarrdb.testRun.find_one( query )

                if thisRun.get( 'display' ) : 
                    entries[stage].update({ scan : thisRun['_id'] })

    for stage in entries :
        scandict = {}

        for scan in entries[stage] :
            mapList = []
            total = False
            scandict.update({ scan : {} })
            if entries[stage][scan] :
                query = { "_id" : entries[stage][scan] }
                thisRun = yarrdb.testRun.find_one( query )
                query = { "testRun" : str(entries[stage][scan]) }
                thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
                env_dict = fill_env( thisComponentTestRun )

                for mapType in listset.scan[scan] :
                    mapDict = {}
                    mapDict.update({ "mapType" : mapType[0] })

                    data_entries = thisRun['attachments']
                    for data in data_entries :

                        datadict = { "1" : "_Dist", "2" : "" }
                        for i in datadict :
                            if data['filename'] == "{0}_{1}{2}".format( thisComponent['serialNumber'], mapType[0], datadict[i] ) :
                                if data['contentType'] == "png" :
                                    filePath = "{0}/{1}_{2}_{3}.png".format( THUM_DIR, stage, scan, data['filename'] )
                                    mapDict.update({ "code{}D".format(i) : data['code'] })
                                    if not os.path.isfile(filePath) :
                                        binary = fs.get(ObjectId(data['code'])).read()
                                        image_bin = io.BytesIO( binary )
                                        image = Image.open( image_bin )
                                        image.thumbnail((int(image.width/4),int(image.height/4)))
                                        image.save( filePath )

                                    url = url_for( 'thumbnail.static', filename='{0}_{1}_{2}.png'.format( stage, scan, data['filename'] ))
                                    mapDict.update({ "url{}Dthum".format(i) : url })

                    mapList.append( mapDict )

                scandict[scan].update({ "runNumber"    : thisRun['runNumber'],
                                        "environment"  : env_dict,
                                        "institution"  : thisRun['institution'],
                                        "userIdentity" : thisRun['userIdentity'] })

            scandict[scan].update({ "map" : mapList,
                                    "num" : len(mapList) })

            if mapList : total = True

        if not scandict == {} :
            summaryIndex.append({ "stage" : stage,
                                  "scan"  : scandict,
                                  "total" : total })

    return summaryIndex

# summary plot in add summary function page
def fill_summary_test() :

    summaryIndex = {}
    scanList = [ "digitalscan", "analogscan", "thresholdscan", "totscan", "noisescan", "selftrigger" ] 
    
    if not session.get( 'stage' ) : return summaryIndex 

    stage = session['stage']
    query = { "_id" : ObjectId(session.get( 'this' )) }
    thisComponent = yarrdb.component.find_one( query )

    # first step in add summary function : make current summary plots as thumbnail
    if not session['summaryList']['before'] :

        after_dir  = "{0}/{1}/after".format( TMP_DIR, session.get('uuid') )
        clean_dir( after_dir )

        before_dir = "{0}/{1}/before".format( TMP_DIR, session.get('uuid') )
        clean_dir( before_dir )
     
        for scan in scanList :
            session['summaryList']['before'].update({ scan : { "runId" : None } })
            session['summaryList']['after' ].update({ scan : { "runId" : None } })

            query = { "component" : session.get( 'this' ), "stage" : stage, "testType" : scan }
            run_entries = yarrdb.componentTestRun.find( query )
            for componentTestRun in run_entries :
                query = { "_id" : ObjectId(componentTestRun['testRun']) }
                thisRun = yarrdb.testRun.find_one( query )
                if thisRun.get( 'display' ) : 
                    session['summaryList']['before'][scan].update({ "runId" : str(thisRun['_id']) })
                    session['summaryList']['after' ][scan].update({ "runId" : str(thisRun['_id']) })

                    make_plot( str(thisRun['_id']) )

                    for mapType in session.get('plotList') :
                        if session['plotList'][mapType]['HistoType'] == 1 : continue
                        url = {} 
                        path = {}
                        datadict = { "1" : "_Dist", "2" : "" }
                        for i in datadict :
                            filepath = "{0}/{1}/plot/{2}_{3}_{4}.png".format(TMP_DIR, str(session.get('uuid')), str(thisRun['testType']), str(mapType), i)
                            if os.path.isfile( filepath ) :
                                binary_file = open( filepath, 'rb' )
                                binary = binary_file.read()
                                binary_file.close()

                                image_bin = io.BytesIO( binary )
                                image = Image.open( image_bin )
                                image.thumbnail((int(image.width/4),int(image.height/4)))
                                filename_before = "{0}/{1}_{2}_{3}_{4}{5}.png".format( before_dir, stage, scan, thisComponent['serialNumber'], mapType, datadict[i] )
                                image.save( filename_before )
                                filename_after  = "{0}/{1}_{2}_{3}_{4}{5}.png".format( after_dir,  stage, scan, thisComponent['serialNumber'], mapType, datadict[i] )
                                image.save( filename_after )

    # remove/replace summary plot : make replaced summary plots as thumbnail
    elif session['step'] == 1 :
        after_dir  = "{0}/{1}/after".format( TMP_DIR, session.get('uuid') )

        for scan in scanList :
            if not session.get('testType') == scan : continue

            for r in glob.glob( '{0}/{1}_{2}*'.format( after_dir, stage, scan ) ) :
                os.remove(r)
            
            if session['summaryList']['after'][scan]['runId'] :
                query = { "_id" : ObjectId(session['summaryList']['after'][scan]['runId']) }
                thisRun = yarrdb.testRun.find_one( query )

                make_plot( str(thisRun['_id']) )

                for mapType in session.get('plotList') :
                    if session['plotList'][mapType]['HistoType'] == 1 : continue
                    url = {} 
                    path = {}
                    datadict = { "1" : "_Dist", "2" : "" }
                    for i in datadict :
                        filepath = "{0}/{1}/plot/{2}_{3}_{4}.png".format(TMP_DIR, str(session.get('uuid')), str(thisRun['testType']), str(mapType), i)
                        if os.path.isfile( filepath ) :
                            binary_file = open( filepath, 'rb' )
                            binary = binary_file.read()
                            binary_file.close()

                            image_bin = io.BytesIO( binary )
                            image = Image.open( image_bin )
                            image.thumbnail((int(image.width/4),int(image.height/4)))
                            filename_after = "{0}/{1}_{2}_{3}_{4}{5}.png".format( after_dir, stage, scan, thisComponent['serialNumber'], mapType, datadict[i] )
                            image.save( filename_after )

    # check path to thumbnails 
    scandict = { "before" : {},
                 "after"  : {} }
    total = 0
    submit = True
    for scan in scanList :

        abType = { 'before' : "{0}/{1}/before".format(TMP_DIR,session.get('uuid')), 'after' : "{0}/{1}/after".format(TMP_DIR,session.get('uuid')) }

        for ab in abType :

            scandict[ab].update({ scan : {} })
            mapList = []

            for mapType in listset.scan[scan] :

                mapDict = { "mapType" : mapType[0] }

                total += 1

                if session['summaryList'][ab][scan]['runId'] :

                    query = { "_id" : ObjectId(session['summaryList'][ab][scan]['runId']) }
                    thisRun = yarrdb.testRun.find_one( query )
                    query = { "testRun" : session['summaryList'][ab][scan]['runId'] }
                    thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
                    env_dict = fill_env( thisComponentTestRun )

                    datadict = { "1" : "_Dist", "2" : "" }
                    for i in datadict :

                        filename = "{0}/{1}_{2}_{3}_{4}{5}.png".format( abType[ab], stage, scan, thisComponent['serialNumber'], mapType[0], datadict[i] )
                        if os.path.isfile( filename ) :
                            binary_image = open( filename, 'rb' )
                            code_base64 = base64.b64encode(binary_image.read()).decode()
                            binary_image.close()
                            url = func.bin_to_image( 'png', code_base64 ) 
                            mapDict.update({ "url{}Dthum".format(i) : url })

                    scandict[ab][scan].update({ "runNumber"    : thisRun['runNumber'],
                                                "runId"        : str(thisRun['_id']),
                                                "institution"  : thisRun['institution'],
                                                "userIdentity" : thisRun['userIdentity'],
                                                "environment"  : env_dict })
                mapList.append( mapDict )

            # put suitable comment for each run
            comment = "..."
            if session['summaryList']["before"][scan]['runId'] == session['summaryList']["after"][scan]['runId'] : comment = None
            elif session['summaryList']["after"][scan].get('comment') in listset.summary_comment :                 comment = session['summaryList']["after"][scan]['comment']
            elif not session['summaryList']["before"][scan]['runId'] :                                             comment = "add"
            else :                                                                                                 submit =  False

            scandict[ab][scan].update({ "map"     : mapList,
                                        "num"     : len(mapList),
                                        "comment" : comment })

    if not scandict == {} :
        summaryIndex.update({ "stage"  : stage,
                              "scan"   : scandict,
                              "total"  : total,
                              "submit" : submit })

    return summaryIndex

######################################################################

# run number list
def fill_resultIndex() :

    resultIndex = {}

    keys = [ "runNumber", "institution", "userIdentity" ]
    runs = []

    chips = []
    query = [{ "parent" : session[ 'this' ] },{ "child" : session[ 'this' ] }]
    child_entries = yarrdb.childParentRelation.find({ '$or' : query })
    for child in child_entries :
        chips.append({ "component" : child[ 'child' ] })

    if session.get( 'stage' ) : query = { '$or' : chips + [{ "component" : session.get( 'this' ) }], "stage" : session.get( 'stage' ) }
    else :                      query = { '$or' : chips + [{ "component" : session.get( 'this' ) }] }

    # list run number and information of the run for each test type
    run_entries = yarrdb.componentTestRun.find( query ).sort( "component", DESCENDING )
    for run in run_entries :
        query = { "_id" : ObjectId(run[ 'testRun' ]) }
        thisRun = yarrdb.testRun.find_one( query )
        query_id = dict( [ (key, thisRun[key]) for key in keys ] )

        if query_id in runs : continue

        runs.append( query_id ) 
        result = ( 'png' or 'pdf' ) in [ data.get( 'contentType' ) for data in thisRun.get( 'attachments' ) ]
        stage = run[ 'stage' ]

        idRun_entries = yarrdb.testRun.find( query_id )
        for idRun in idRun_entries :        
            query = { "component" : session[ 'this' ], "testRun" : str(idRun[ '_id' ]) }
            if yarrdb.componentTestRun.find_one( query ) : thisRun =idRun 
            if not result : result = ( 'png' or 'pdf' ) in [ data.get( 'contentType' ) for data in idRun.get( 'attachments' ) ]
        if not run.get( 'testType' ) in resultIndex : resultIndex.update({ run.get( 'testType' ) : { "run" : [] }})

        resultIndex[ run.get( 'testType' ) ][ 'run' ].append({ "_id"          : str(thisRun[ '_id' ]),
                                                               "runNumber"    : thisRun[ 'runNumber' ],
                                                               "datetime"     : func.setTime(thisRun[ 'date' ]),
                                                               "result"       : result,
                                                               "stage"        : stage,
                                                               "summary"      : thisRun.get( 'display' ) })
    for scan in resultIndex :
        runInd = sorted( resultIndex[ scan ][ 'run' ], key=lambda x:x['datetime'], reverse=True)
        resultIndex.update({ scan : { "num" : len( runInd ),
                                      "run" : runInd }})
    return resultIndex

# make result plot in component page for the run
def fill_results() :

    results = {}

    if session.get('runId') :
        query = { "component" : session[ 'this' ], "testRun" : session[ 'runId' ] }
        thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
        query = { "_id" : ObjectId(session['runId']) }
        thisRun = yarrdb.testRun.find_one( query )

        plots = []
        config = []
        if thisComponentTestRun :
            data_entries = thisRun['attachments']
            for data in data_entries :
                if data['contentType'] == 'pdf' or data['contentType'] == 'png' :
                    binary = base64.b64encode( fs.get( ObjectId(data['code']) ).read() ).decode()
                    url = func.bin_to_image( data['contentType'], binary )
                    plots.append({ "code"        : data['code'],
                                   "url"         : url,
                                   "filename"    : data['filename'].split("_",1)[1] })
                #elif data['contentType'] == 'after' :
                #    filename = TMP_DIR + "/test.json"
                #    #func.writeJson( filename, fs.get( ObjectId(data['code']) ).read().decode() )
                #    with open( filename, 'bw' ) as f :
                #        f.write( fs.get( ObjectId(data['code']) ).read() )
        else :
            query = { "testRun" : session['runId'] }
            thisComponentTestRun = yarrdb.componentTestRun.find_one( query )

        env_dict = fill_env( thisComponentTestRun ) 

        results.update({ "testType"     : thisRun['testType'],
                         "runNumber"    : thisRun['runNumber'],
                         "runId"        : str(thisRun['_id']),
                         "comments"     : list(thisRun['comments']),
                         "stage"        : thisComponentTestRun['stage'],
                         "institution"  : thisRun['institution'],
                         "userIdentity" : thisRun['userIdentity'],
                         "environment"  : env_dict,
                         "plots"        : plots,
                         "config"       : config }) 

    return results

# create dat file from dat data in attachments of run
def write_dat( runId ) :

    query = { "_id" : ObjectId(runId) }
    thisRun = yarrdb.testRun.find_one( query )
    thisComponentTestRun = yarrdb.componentTestRun.find_one({ "testRun" : str(thisRun['_id']) })

    chipIds = {}

    chips = []
    query = [{ "parent" : session['this'] },{ "child" : session['this'] }]
    child_entries = yarrdb.childParentRelation.find({ '$or' : query })
    for child in child_entries :
        chips.append({ "component" : child['child'] })

    components = sorted( chips, key=lambda x:x['component'] )
    i=1
    for component in components :
        if not component['component'] in chipIds :
            chipIds.update({ component['component'] : i })
            i+=1
    query = { '$or' : components, "runNumber" : thisRun['runNumber'], "testType" : thisRun['testType'], "stage" : thisComponentTestRun['stage'] }
    run_entries = yarrdb.componentTestRun.find( query )

    for run in run_entries :
        query = { "_id" : ObjectId(run['testRun']), "institution" : thisRun['institution'], "userIdentity" : thisRun['userIdentity'] }
        chiprun = yarrdb.testRun.find_one( query )

        if chiprun :

            data_entries = chiprun['attachments']
            for data in data_entries :
                if data['contentType'] == "dat" :
                    f = open( '{0}/{1}/dat/{2}_{3}.dat'.format( TMP_DIR, session.get('uuid'), 'chipId{}'.format(chipIds[run['component']]), data['filename'].rsplit("_",1)[1] ), 'wb' )
                    f.write( fs.get(ObjectId(data['code']) ).read())
                    f.close()
                    mapType = data['filename'].rsplit("_",1)[1]
                    session['plotList'].update({ mapType : { "draw" : True, "chips" : len(chipIds) } })

# make plot using PyROOT
def make_plot( runId ) :

    query = { "_id" : ObjectId(runId) }
    thisRun = yarrdb.testRun.find_one( query )

    if session.get('rootType') :

        mapType = session['mapType']

        if session['rootType'] == 'set' : 
            root.setParameter( thisRun['testType'], mapType )
            for mapType in session['plotList'] : session['plotList'][mapType].update({ "draw" : True, "parameter" : {} })

        elif session['rootType'] == 'make' :
            session['plotList'][mapType].update({ "draw" : True, "parameter" : session['parameter'] })

    else :

        session['plotList'] = {}
    
        plot_dir = TMP_DIR + "/" + str(session.get('uuid')) + "/plot"
        dat_dir  = TMP_DIR  + "/" + str(session.get('uuid')) + "/dat"
        clean_dir( plot_dir )
        clean_dir( dat_dir )
    
        jsonFile = JSON_DIR + "/{}_parameter.json".format(session.get('uuid'))
        if not os.path.isfile( jsonFile ) :
            jsonFile_default = SCRIPT_DIR + "/json/parameter_default.json"
            with open( jsonFile_default, 'r' ) as f : jsonData_default = json.load( f )
            with open( jsonFile,         'w' ) as f : json.dump( jsonData_default, f, indent=4 )
    
        write_dat( runId )

    root.drawScan( thisRun['testType'] )

    session.pop( 'rootType',  None )
    session.pop( 'mapType',   None )
    session.pop( 'parameter', None )
 
# list plot created by "make_plot" using PyROOT
def fill_roots() :

    roots = {}

    if not session.get( 'runId' ) : return roots

    if not DOROOT :
        roots.update({ "rootsw" : False })
        return roots

    make_plot(session['runId'])

    query = { "_id" : ObjectId(session['runId']) }
    thisRun = yarrdb.testRun.find_one( query )

    results = []
    thisComponentTestRun = yarrdb.componentTestRun.find_one({ "testRun" : str(thisRun['_id']) })
    env_dict = fill_env( thisComponentTestRun ) 

    for mapType in session.get('plotList') :
        if session['plotList'][mapType]['HistoType'] == 1 : continue
        url = {} 
        path = {}
        for i in [ "1", "2" ] :
            filename = TMP_DIR + "/" + str(session.get('uuid')) + "/plot/" + str(thisRun['testType']) + "_" + str(mapType) + "_{}.png".format(i)
            stage = thisComponentTestRun['stage']
            if os.path.isfile( filename ) :
                binary_image = open( filename, 'rb' )
                code_base64 = base64.b64encode(binary_image.read()).decode()
                binary_image.close()
                url.update({ i : func.bin_to_image( 'png', code_base64 ) }) 
                path.update({ i : filename }) 

        results.append({ "testType"    : thisRun['testType'], 
                         "mapType"     : mapType, 
                         "sortkey"     : "{}0".format(mapType), 
                         "runNumber"   : thisRun['runNumber'], 
                         "runId"       : session['runId'],
                         "comments"    : list(thisRun['comments']),
                         "path_Dist"   : path.get("1"), 
                         "path"        : path.get("2"), 
                         "stage"       : stage,
                         "institution" : thisRun['institution'],
                         "userIdentity": thisRun['userIdentity'],
                         "urlDist"     : url.get("1"), 
                         "urlMap"      : url.get("2"), 
                         "environment" : env_dict,
                         "setLog"      : session['plotList'][mapType]['parameter']["log"], 
                         "minValue"    : session['plotList'][mapType]['parameter']["min"],
                         "maxValue"    : session['plotList'][mapType]['parameter']["max"],
                         "binValue"    : session['plotList'][mapType]['parameter']["bin"] })

    results = sorted( results, key=lambda x:int((re.search(r"[0-9]+",x['sortkey'])).group(0)), reverse=True)

    roots.update({ "rootsw"  : True,
                   "results" : results })

    return roots
