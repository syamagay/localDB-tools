import os, pwd, glob, sys, json
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(APP_DIR)
sys.path.append( APP_DIR )
JSON_DIR = APP_DIR + "/scripts/json"

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
USER = pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
PIC_DIR = '{}/upload'.format( USER_DIR )
DAT_DIR = '{}/dat'.format( USER_DIR )
PLOT_DIR = '{}/result'.format( USER_DIR )
STAT_DIR = '{}/static'.format( USER_DIR )

#############
# set dbs
args = getArgs()         
if args.username is None:
    url = "mongodb://" + args.host + ":" + str(args.port) 
else:
    url = "mongodb://" + args.username + ":" + args.password + "@" + args.host + ":" + str(args.port) 
client = MongoClient( url )
yarrdb = client['yarrdb']
localdb = client['yarrlocal']
fs = gridfs.GridFS( yarrdb )

def clean_dir( path ) :
    r = glob.glob( path + "/*" )
    for i in r:
        os.remove(i)

def fill_env( thisComponentTestRun ) :
    env_list = thisComponentTestRun.get('environments',[])
    env_dict = { "list" : env_list,
                 "num"  : len(env_list) }
    return env_dict

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

def fill_summary( thisComponent ) :
    summaryIndex = []
    for stage in listset.stage :
        query = { "component" : str(thisComponent['_id']), "stage" : stage }
        componentTestRun_entries = yarrdb.componentTestRun.find( query )
        runIds = []
        for componentTestRun in componentTestRun_entries :
            runIds.append({ "_id" : ObjectId(componentTestRun['testRun']) })
        if not runIds == [] :
            query = { '$or' : runIds, "display" : True }
            run_entries = yarrdb.testRun.find( query )
            if not run_entries.count() == 0 :
                scandict = {}
                for scan in listset.scan :
                    query = { '$or' : runIds, "testType" : scan, "display" : True }
                    thisRun = yarrdb.testRun.find_one( query )
                    mapList = []
                    if thisRun :
                        for mapType in listset.scan[scan] :
                            values = {}
                            thisComponentTestRun = yarrdb.componentTestRun.find_one({ "testRun" : str(thisRun['_id']) })
                            env_dict = fill_env( thisComponentTestRun )
                            values.update({ "env" : env_dict })
                            data_entries = thisRun['attachments']
                            for data in data_entries :
                                if data['filename'] == "{0}_{1}".format( thisComponent['serialNumber'], mapType[0] ) :
                                    if data['contentType'] == "png" :
                                        filePath = "{0}/thum/{1}_{2}_{3}.png".format( PLOT_DIR, stage, scan, data['filename'] )
                                        values.update({ "2Dcode" : data['code'] })
                                        if not os.path.isfile(filePath) :
                                            binary = fs.get(ObjectId(data['code'])).read()
                                            image_bin = io.BytesIO( binary )
                                            image = Image.open( image_bin )
                                            image.thumbnail((int(image.width/4),int(image.height/4)))
                                            image.save( filePath )
                                        url = url_for( 'result.static', filename='thum/{0}_{1}_{2}.png'.format( stage, scan, data['filename'] ))
                                        values.update({ "2Dthum" : url })
                                elif data['filename'] == "{0}_{1}_Dist".format( thisComponent['serialNumber'], mapType[0] ) :
                                    if data['contentType'] == "png" :
                                        filePath = "{0}/thum/{1}_{2}_{3}.png".format( PLOT_DIR, stage, scan, data['filename'] )
                                        values.update({ "1Dcode" : data['code'] })
                                        if not os.path.isfile(filePath) :
                                            binary = fs.get(ObjectId(data['code'])).read()
                                            image_bin = io.BytesIO( binary )
                                            image = Image.open( image_bin )
                                            image.thumbnail((int(image.width/4),int(image.height/4)))
                                            image.save( filePath )
                                        url = url_for( 'result.static', filename='thum/{0}_{1}_{2}.png'.format( stage, scan, data['filename'] ))
                                        values.update({ "1Dthum" : url })
                            mapList.append({ "url1Dthum" : values.get('1Dthum'),
                                             "url2Dthum" : values.get('2Dthum'),
                                             "code1D" : values.get('1Dcode'),
                                             "code2D" : values.get('2Dcode'),
                                             "mapType" : mapType[0],
                                             "environment" : values.get('env') })
                    scandict.update({ scan : { "map" : mapList,
                                               "num" : len(mapList) }})

                if not scandict == {} :
                    summaryIndex.append({ "stage"    : stage,
                                          "scan"     : scandict })
    return summaryIndex

def fill_resultIndex( item ) :
    resultIndex = {}
    keys = [ "runNumber", "institution", "userIdentity" ]
    runs = []

    query = { '$or' : item.get( 'chips' ) + [{"component" : item.get( 'this' )}] }
    run_entries = yarrdb.componentTestRun.find( query ).sort( "component", DESCENDING )
    for run in run_entries :
        query = { "_id" : ObjectId(run['testRun']) }
        thisRun = yarrdb.testRun.find_one( query )
        query_id = dict( [ (key, thisRun[key]) for key in keys ] )
        if query_id in runs :
            continue
        runs.append( query_id ) 
        result = ( 'png' or 'pdf' ) in [ data.get('contentType') for data in thisRun.get('attachments') ]
        stage = run['stage']
        thisRun_entries = yarrdb.testRun.find( query_id )
        for thisRun_entry in thisRun_entries :        
            query = { "component" : item.get( 'this' ), "testRun" : str(thisRun_entry['_id']) }
            if yarrdb.componentTestRun.find_one( query ) :
                thisRun = thisRun_entry
            if not result :
                result = ( 'png' or 'pdf' ) in [ data.get('contentType') for data in thisRun_entry.get('attachments') ]
        if not run.get( 'testType' ) in resultIndex :
            resultIndex.update({ run.get( 'testType' ) : { "run" : [] }})
        resultIndex[ run.get( 'testType' ) ][ 'run' ].append({ "_id"          : str(thisRun['_id']),
                                                               "runNumber"    : thisRun['runNumber'],
                                                               "datetime"     : func.setTime(thisRun['date']),
                                                               "result"       : result,
                                                               "stage"        : stage,
                                                               "summary"      : thisRun.get('display') })
    for scan in resultIndex :
        runInd = sorted( resultIndex[ scan ][ 'run' ], key=lambda x:x['datetime'], reverse=True)
        resultIndex.update({ scan : { "num" : len(runInd),
                                      "run" : runInd }})
    return resultIndex

def fill_results( item, runId ) :
    results = {}
    if not runId == None :
        query = { "component" : item.get( 'this' ), "testRun" : runId }
        thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
        query = { "_id" : ObjectId(runId) }
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
                #    filename = USER_DIR + "/test.json"
                #    #func.writeJson( filename, fs.get( ObjectId(data['code']) ).read().decode() )
                #    with open( filename, 'bw' ) as f :
                #        f.write( fs.get( ObjectId(data['code']) ).read() )
        else :
            query = { "testRun" : runId }
            thisComponentTestRun = yarrdb.componentTestRun.find_one( query )

            data_entries = thisRun['attachments']
            for data in data_entries :
                if data['contentType'] == 'pdf' or data['contentType'] == 'png' :
                    plots.append({ "filename"    : data['filename'].split("_",1)[1] })

        env_dict = fill_env( thisComponentTestRun ) 

        results.update({ "testType"  : thisRun['testType'],
                         "runNumber" : thisRun['runNumber'],
                         "runId"     : str(thisRun['_id']),
                         "comments"  : list(thisRun['comments']),
                         "stage"     : thisComponentTestRun['stage'],
                         "institution" : thisRun['institution'],
                         "userIdentity" : thisRun['userIdentity'],
                         "environment" : env_dict,
                         "plots"        : plots,
                         "config"       : config }) 

    return results

def fill_roots( item, runId ) :
    roots = {}
    if not runId == None :
        roots.update({ "runId" : True })
        query = { "_id" : ObjectId(runId) }
        thisRun = yarrdb.testRun.find_one( query )
        if DOROOT :
            results = []
            thisComponentTestRun = yarrdb.componentTestRun.find_one({ "testRun" : str(thisRun['_id']) })
            env_dict = fill_env( thisComponentTestRun ) 
            reanalysis = session.get('reanalysis')
            mapList = {}
            if not reanalysis :
                session['plot_list'] = {}
                chipIds = {}
                components = sorted( item.get( 'chips' ), key=lambda x:x['component'] )
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
                                f = open( '{0}/{1}_{2}_{3}_{4}.dat'.format( DAT_DIR, session.get('uuid'), thisRun['runNumber'], 'chipId{}'.format(chipIds[run['component']]), data['filename'].rsplit("_",1)[1] ), 'wb' )
                                f.write( fs.get(ObjectId(data['code']) ).read())
                                f.close()
                                mapList.update({ data['filename'].rsplit("_",1)[1] : len(chipIds) })
            else :
                chipIds = {}
                components = sorted( item.get( 'chips' ), key=lambda x:x['component'] )
                i=1
                for component in components :
                    if not component['component'] in chipIds :
                        chipIds.update({ component['component'] : i })
                        i+=1
                mapList.update({ session.get( 'mapType' ) : len(chipIds) })
            root.drawScan( thisRun['testType'], str(thisRun['runNumber']), bool(session.get( 'log', False )), int( session.get( 'max', 0 )), mapList )

            for mapType in session.get('plot_list') :
                for i in [ "1", "2" ] :
                    filename = PLOT_DIR + "/" + str(session.get('uuid')) + "/" + str(thisRun['runNumber']) + "_" + str(mapType) + "_{}.png".format(i)
                    url = "" 
                    stage = thisComponentTestRun['stage']
                    if os.path.isfile( filename ) :
                        binary_image = open( filename, 'rb' )
                        code_base64 = base64.b64encode(binary_image.read()).decode()
                        binary_image.close()
                        url = func.bin_to_image( 'png', code_base64 ) 
                    results.append({ "testType"    : thisRun['testType'], 
                                     "mapType"     : mapType, 
                                     "filename"    : mapType, 
                                     "runNumber"   : thisRun['runNumber'], 
                                     "runId"       : runId,
                                     "comments"    : list(thisRun['comments']),
                                     "path"        : filename, 
                                     "stage"       : stage,
                                     "institution" : thisRun['institution'],
                                     "userIdentity": thisRun['userIdentity'],
                                     "url"         : url, 
                                     "environment" : env_dict,
                                     "setLog"      : session['plot_list'][mapType]["log"], 
                                     "maxValue"    : session['plot_list'][mapType]["max"] })
            roots.update({ "rootsw"  : True,
                           "results" : results })
        else :
            roots.update({ "rootsw" : False })
    else :
        roots.update({ "runId" : False })

    return roots
