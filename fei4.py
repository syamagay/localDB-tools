try    : import root
except : pass 

import os, pwd, glob, hashlib, datetime, shutil
#os.environ['LIBPATH']=path/to/root/lib
#os.environ['LD_LIBRARY_PATH']=path/to/root/lib
#os.environ['PYTHONPATH']=path/to/root/lib

# use Flask scheme
from flask import Flask, request, redirect, url_for, render_template, session, abort
from flask_httpauth import HTTPDigestAuth

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

##################
# path/to/save/dir 
USER = pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
PIC_DIR = '{}/upload'.format( USER_DIR )
DAT_DIR = '{}/dat'.format( USER_DIR )
PLOT_DIR = '{}/result'.format( USER_DIR )
STAT_DIR = '{0}/static/{1}-upload'.format( os.path.dirname(os.path.abspath(__file__)), USER )

scanList = { "selftrigger"   : [( "OccupancyMap-0", "#Hit" ),],
             "noisescan"     : [( "NoiseOccupancy","NoiseOccupancy" ), ( "NoiseMask", "NoiseMask" )],
             "totscan"       : [( "MeanTotMap", "Mean[ToT]" ),         ( "SigmaTotMap", "Sigma[ToT]" )],
             "thresholdscan" : [( "ThresholdMap", "Threshold[e]" ),    ( "NoiseMap", "Noise[e]" )],
             "digitalscan"   : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )],
             "analogscan"    : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )]}

#############
# set dbs
client = MongoClient( host='localhost', port=28000 )
yarrdb = client['yarrdb']
localdb = client['yarrlocal']
fs = gridfs.GridFS( yarrdb )

def clean_dir( path ) :
    r = glob.glob( path + "/*" )
    for i in r:
        os.remove(i)

def fill_env( thisRun ) :
    env_dict = { "hv"    : thisRun.get( 'environment', { "key" : "value" } ).get( 'hv', "" ),
                 "cool"  : thisRun.get( 'environment', { "key" : "value" } ).get( 'cool', "" ),
                 "stage" : thisRun.get( 'environment', { "key" : "value" } ).get( 'stage', "" ) }
    return env_dict

def fill_photoDisplay( thisComponent ) :
    photoDisplay = []
    if "attachments" in thisComponent : 
        data_entries = thisComponent['attachments']
        for data in data_entries :
            if ( data.get( 'imageType' ) == "image" ) and ( data.get( 'display' ) == "True" ) :
                filePath = "{0}/{1}_{2}".format( STAT_DIR, data['photoNumber'], data['filename'] )
                f = open( filePath, 'wb' )
                f.write( fs.get(ObjectId(data['code'])).read() )
                f.close()
                url = url_for( 'static', filename='{0}-upload/{1}_{2}'.format( USER, data['photoNumber'], data['filename'] ))
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

                url = url_for( 'static', filename='{0}-upload/{1}'.format( USER, data['filename'] ))
                photos = { "url"         : url,
                           "code"        : data['code'],
                           "photoNumber" : data['photoNumber'],
                           "stage"       : data['stage'],
                           "display"     : data.get( 'display', "False" ),
                           "filename"    : data['filename'] }
    return photos

def fill_resultDisplay( thisComponent ) :
    resultDisplay = []
    if session['component'] == "module" :
        if "attachments" in thisComponent : 
            data_entries = thisComponent['attachments']
            for scan in scanList :
                displayList = []
                for data in data_entries :
                    if data.get( 'imageType' ) == "result" :
                        if scan == data.get( 'filename', "" ).rsplit( '_', 3 )[1] :
                            binary = base64.b64encode( fs.get(ObjectId(data['code'])).read() ).decode()
                            url = img.bin_to_image( data['contentType'], binary )
                            runNumber = data['filename'].rsplit( '_', 3 )[0]
                            mapType   = data['filename'].rsplit( '_', 3 )[2].rsplit( '.', 1 )[0].rsplit( '-', 1 )[0]
                            env_dict = fill_env( data ) 

                            displayList.append({ "url"         : url,
                                                 "runNumber"   : runNumber,
                                                 "runId"       : "",
                                                 "collection"  : "component",
                                                 "environment" : env_dict,
                                                 "description" : data['description'],
                                                 "code"        : data['code'],
                                                 "htmlurl"     : "remove_attachment",
                                                 "filename"    : mapType })
                if not displayList == [] :
                    resultDisplay.append({ "testType" : scan,
                                           "display"  : displayList })

    if session['component'] == "chip" :
        for scan in scanList :
            query = { "component" : str(thisComponent['_id']), "testType" : scan }
            run_entries = yarrdb.componentTestRun.find( query )
            displayList = []
            for run in run_entries :
                query = { "_id" : ObjectId(run['testRun']) }
                thisRun = yarrdb.testRun.find_one( query )
                env_dict = fill_env( thisRun )
    
                display_entries = thisRun['attachments']
                for data in display_entries :
                    if data.get( 'display' ) == 'True' :
                        binary = base64.b64encode( fs.get( ObjectId(data['code']) ).read() ).decode()
                        url = img.bin_to_image( data['contentType'], binary )
    
                        displayList.append({ "runNumber"   : thisRun['runNumber'],
                                             "runId"       : thisRun['_id'],
                                             "code"        : data['code'],
                                             "htmlurl"     : "tag_result",
                                             "environment" : env_dict,
                                             "description" : data['description'],
                                             "collection"  : "testRun",
                                             "filename"    : data['filename'].rsplit("_",1)[1],
                                             "url"         : url })
    
            if not displayList == [] :
                resultDisplay.append({ "testType" : scan,
                                       "display"  : displayList })

    return resultDisplay

def fill_runIndex( thisRun, runIndex=[] ) :
    env_dict = fill_env( thisRun )
    if not thisRun['runNumber'] in [ runItem.get( 'runNumber', "" ) for runItem in runIndex ] :
        if ( 'png' or 'pdf' ) in [ data.get('contentType') for data in thisRun['attachments'] ] :
            result = "True"
        else :
            result = "False"
        runIndex.append({ "_id"         : thisRun['_id'],
                          "runNumber"   : thisRun['runNumber'],
                          "datetime"    : func.setTime(thisRun['date']),
                          "institution" : thisRun['institution'],
                          "result"      : result,
                          "environment" : env_dict })
    return env_dict

def fill_resultIndex( item ) :
    resultIndex = []
    for scan in scanList :
        query = { '$or' : item, "testType" : scan }
        run_entries = yarrdb.componentTestRun.find( query )
        runIndex = []
        for run in run_entries :
            query = { "_id" : ObjectId(run['testRun']) }
            thisRun = yarrdb.testRun.find_one( query )
            env_dict = fill_runIndex( thisRun, runIndex )
        
        if not runIndex == [] :
            resultIndex.append({ "testType" : scan,
                                 "run"      : runIndex })
    return resultIndex

def fill_results( item, runNumber ) :
    results = []
    if not runNumber == 0 :
        if session['component'] == "module" :
            reanalysis = request.form.get( 'reanalysis', "False" )
            if not reanalysis == "True" :
                clean_dir( DAT_DIR )

            query = { '$or' : item , "runNumber" : runNumber }
            run_entries = yarrdb.componentTestRun.find( query )
            for run in run_entries :
                query = { "_id" : ObjectId(run['testRun']) }
                thisRun = yarrdb.testRun.find_one( query )
                env_dict = fill_env( thisRun )
                comments = list(thisRun['comments'])
                testType = thisRun['testType']
                if not reanalysis == "True" :
                    data_entries = thisRun['attachments']
                    for data in data_entries :
                        if data['contentType'] == "dat" :
                            f = open( '{0}/{1}_{2}_{3}.dat'.format( DAT_DIR, runNumber, data['filename'].rsplit("_",2)[1], data['filename'].rsplit("_",2)[2] ), "wb" )
                            f.write( fs.get(ObjectId(data['code']) ).read())
                            f.close()
            mapList = {}
            for mapType in scanList[testType] :
                if reanalysis == "True" and not mapType[0] == request.form.get( 'mapType' ) :
                    mapList.update({ mapType[0] : False })
                else :
                    mapList.update({ mapType[0] : True })

            try    : root.drawScan( testType, str(runNumber), bool(request.form.get( 'log', False )), int( request.form.get( 'max' ) or 0 ), mapList )
            except : print( "undo root process" )

            for mapType in scanList[testType] :
                for i in [ "1", "2" ] :
                    max_value = func.readJson( "{}/parameter.json".format( os.path.dirname(os.path.abspath(__file__)) )) 
                    filename = PLOT_DIR + "/" + testType + "/" + str(runNumber) + "_" + mapType[0] + "_{}.png".format(i)
                    url = "" 
                    if os.path.isfile( filename ) :
                        binary_image = open( filename, 'rb' )
                        code_base64 = base64.b64encode(binary_image.read()).decode()
                        binary_image.close()
                        url = img.bin_to_image( 'png', code_base64 ) 
                    results.append({ "testType"  : testType, 
                                     "mapType"   : mapType[0], 
                                     "runNumber" : runNumber, 
                                     "comments"  : comments,
                                     "comment"   : "No Root Software",
                                     "path"      : filename, 
                                     "url"       : url, 
                                     "environment" : env_dict,
                                     "setLog"    : max_value[testType][mapType[0]][1], 
                                     "maxValue"  : max_value[testType][mapType[0]][0] })

        if session['component'] == "chip" :
            query = { '$or' : item , "runNumber" : runNumber }
            run = yarrdb.componentTestRun.find_one( query )
            query = { "_id" : ObjectId(run['testRun']) }
            thisRun = yarrdb.testRun.find_one( query )
            comments = list(thisRun['comments'])
            env_dict = fill_env( thisRun )
            data_entries = thisRun['attachments']
            for data in data_entries :
                if data['contentType'] == 'pdf' or data['contentType'] == 'png' :
                    binary = base64.b64encode( fs.get( ObjectId(data['code']) ).read() ).decode()
                    url = img.bin_to_image( data['contentType'], binary )
                    results.append({ "testType"    : thisRun['testType'],
                                     "runNumber"   : thisRun['runNumber'],
                                     "runId"       : thisRun['_id'],
                                     "code"        : data['code'],
                                     "url"         : url,
                                     "comments"   : comments,
                                     "filename"    : data['filename'].rsplit("_",1)[1],
                                     "environment" : env_dict,
                                     "display"     : data.get('display',"False") })

    return results

