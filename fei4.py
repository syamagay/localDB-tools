try    : 
    import root
    DOROOT = True
except : 
    DOROOT = False 
#DOROOT=False

import os, pwd, glob, hashlib, datetime, shutil

# usersetting
import userset

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
from PIL import Image
import io

# other function
import func, userfunc, listset

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
client = MongoClient( host='localhost', port=userset.PORT )
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
    resultIndex = []
    for scan in listset.scan :
        runIndex = []
        numberids = []
        keys = [ "runNumber", "institution", "userIdentity" ]
        for i in [ 1, 2 ] :
            if i == 1 :
                query = { "component" : item.get( 'this' ), "testType" : scan }
            elif session['component'] == "module" :
                query = { '$or' : item.get( 'chips' ), "testType" : scan }
            else :
                continue
            run_entries = yarrdb.componentTestRun.find( query )
            for run in run_entries :
                if numberids == [] :
                    query = { "_id" : ObjectId(run['testRun']) }
                else :
                    query = { "_id" : ObjectId(run['testRun']), '$and' : numberids }
                thisRun = yarrdb.testRun.find_one( query )
                if thisRun :
                    numberid = []
                    for key in keys :
                        numberid.append({ key : { '$ne' : thisRun[key] }})
                    numberids.append({ '$or' : numberid })
                    result = ( 'png' or 'pdf' ) in [ data.get('contentType') for data in thisRun['attachments'] ]
                    stage = run['stage']
                    runIndex.append({ "_id"          : str(thisRun['_id']),
                                      "runNumber"    : thisRun['runNumber'],
                                      "datetime"     : func.setTime(thisRun['date']),
                                      "result"       : result,
                                      "stage"        : stage,
                                      "summary"      : thisRun.get('display') })
        if not runIndex == [] :
            runIndex = sorted(runIndex, key=lambda x:x['datetime'])
            resultIndex.append({ "testType" : scan,
                                 "run"      : runIndex })
    return resultIndex

def fill_results( item, runId ) :
    results = []
    if not runId == None :
        query = { "component" : item.get( 'this' ), "testRun" : runId }
        thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
        query = { "_id" : ObjectId(runId) }
        thisRun = yarrdb.testRun.find_one( query )
        if thisComponentTestRun :
            env_dict = fill_env( thisComponentTestRun ) 
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
                                     "comments"    : list(thisRun['comments']),
                                     "filename"    : data['filename'].split("_",1)[1],
                                     "stage"       : thisComponentTestRun['stage'],
                                     "institution" : thisRun['institution'],
                                     "userIdentity": thisRun['userIdentity'],
                                     "environment" : env_dict,
                                     "display"     : data.get('display',False) })
        else :
            query = { "testRun" : runId }
            thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
            query = { "_id" : ObjectId(runId) }
            thisRun = yarrdb.testRun.find_one( query )
            env_dict = fill_env( thisComponentTestRun ) 
            results.append({ "testType"    : thisRun['testType'],
                             "runNumber"   : thisRun['runNumber'],
                             "runId"       : thisRun['_id'],
                             "comments"    : list(thisRun['comments']),
                             "stage"       : thisComponentTestRun['stage'],
                             "institution" : thisRun['institution'],
                             "userIdentity": thisRun['userIdentity'],
                             "environment" : env_dict,
                             "display"     : False })

    return results

def fill_roots( item, runId, doroot ) :
    roots = {}
    if not runId == None :
        roots.update({ "runId" : True })
        if doroot :
            roots.update({ "doroot" : True })
            if DOROOT :
                results = []
                query = { "_id" : ObjectId(runId) }
                thisRun = yarrdb.testRun.find_one( query )
                thisComponentTestRun = yarrdb.componentTestRun.find_one({ "testRun" : str(thisRun['_id']) })
                env_dict = fill_env( thisComponentTestRun ) 
                reanalysis = session.get('reanalysis')
                if not reanalysis :
                    clean_dir( DAT_DIR )
                query = { '$or' : item.get( 'chips' ), "runNumber" : thisRun['runNumber'], "testType" : thisRun['testType'] }
                run_entries = yarrdb.componentTestRun.find( query )
                runIds = []
                for run in run_entries :
                    runIds.append({ "_id" : ObjectId(run['testRun']) })
                query = { '$or' : runIds, "institution" : thisRun['institution'], "userIdentity" : thisRun['userIdentity'] }
                run_entries = yarrdb.testRun.find( query )
                for chiprun in run_entries :
                    if not reanalysis :
                        data_entries = chiprun['attachments']
                        for data in data_entries :
                            if data['contentType'] == "dat" :
                                f = open( '{0}/{1}_{2}_{3}.dat'.format( DAT_DIR, thisRun['runNumber'], data['filename'].rsplit("_",2)[1], data['filename'].rsplit("_",2)[2] ), "wb" )
                                f.write( fs.get(ObjectId(data['code']) ).read())
                                f.close()
                mapList = {}
                for mapType in listset.scan[thisRun['testType']] :
                    if reanalysis and not mapType[0] == session.get( 'mapType' ) :
                        mapList.update({ mapType[0] : False })
                    else :
                        mapList.update({ mapType[0] : True })

                root.drawScan( thisRun['testType'], str(thisRun['runNumber']), bool(session.get( 'log' )), int( session.get( 'max' )), mapList )

                for mapType in listset.scan[thisRun['testType']] :
                    for i in [ "1", "2" ] :
                        max_value = func.readJson( "{}/parameter.json".format( os.path.dirname(os.path.abspath(__file__)) )) 
                        filename = PLOT_DIR + "/" + thisRun['testType'] + "/" + str(thisRun['runNumber']) + "_" + mapType[0] + "_{}.png".format(i)
                        url = "" 
                        query = { "testRun" : str(thisRun['_id']) }
                        stage = yarrdb.componentTestRun.find_one( query )['stage']
                        if os.path.isfile( filename ) :
                            binary_image = open( filename, 'rb' )
                            code_base64 = base64.b64encode(binary_image.read()).decode()
                            binary_image.close()
                            url = img.bin_to_image( 'png', code_base64 ) 
                        results.append({ "testType"    : thisRun['testType'], 
                                         "mapType"     : mapType[0], 
                                         "filename"    : mapType[0], 
                                         "runNumber"   : thisRun['runNumber'], 
                                         "runId"       : runId,
                                         "comments"    : list(thisRun['comments']),
                                         "path"        : filename, 
                                         "stage"       : stage,
                                         "institution" : thisRun['institution'],
                                         "userIdentity": thisRun['userIdentity'],
                                         "url"         : url, 
                                         "environment" : env_dict,
                                         "setLog"      : max_value[thisRun['testType']][mapType[0]][1], 
                                         "maxValue"    : max_value[thisRun['testType']][mapType[0]][0] })
                roots.update({ "rootsw"  : True,
                               "results" : results })
            else :
                roots.update({ "rootsw" : False })
        else :
            roots.update({ "doroot" : False })
    else :
        roots.update({ "runId" : False })

    return roots
