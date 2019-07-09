# modules
import os
import pwd
import glob
import json
import re
import shutil
import base64  # Base64 encoding scheme
from datetime import datetime, timezone, timedelta
import pytz
import hashlib
import gridfs # gridfs system 
import io
import zipfile

from flask         import url_for, session  # use Flask scheme
from pymongo       import MongoClient, DESCENDING  # use mongodb scheme
from bson.objectid import ObjectId  # handle bson format
from binascii      import a2b_base64  # convert a block of base64 data back to binary
from pdf2image     import convert_from_path  # convert pdf to image
from PIL           import Image
from scripts.src.arguments import *  # Pass command line arguments into app.py
from scripts.src import listset

# PyROOT
try: 
    from scripts.src import root
    DOROOT = True
except: 
    DOROOT = False 

# dcsPlot
try:
    from scripts.src import dcs_plot
    import time
    DODCS=True
except:
    DODCS= False

# directories 
"""
 /
 `-- tmp
      |-- [username who execute app.py]
               |-- [reader1's userid] ... reader's directory (created and reset in app.py) 
               |      :
               |-- [reader#'s userid]
               |        |-- dat    ... dat files  (reset in writeDat())
               |        |-- plot   ... plot files (reset in makePlot()) 
               |        |-- before ... previous summary plots in add_summary function (reset in first time setsummary_test())
               |        `-- after  ... modified summary plots in add_summary function (reset in first time setsummary_test())
               | 
               |-- thumbnail ... summary plots (reset after add_summary function)
               |        `-- [reader's userid] ... summary plots for user (created and reset in show_summary())
               `-- json ... json file ; <reader's userid>_parameter.json (created in makePlot())
"""

TMP_DIR       = '/tmp/{}'.format(pwd.getpwuid(os.geteuid()).pw_name) 
UPLOAD_DIR    = '{}/upload'.format(TMP_DIR)
THUMBNAIL_DIR = '{}/thumbnail'.format(TMP_DIR)
STATIC_DIR    = '{}/static'.format(TMP_DIR)
JSON_DIR      = '{}/json'.format(TMP_DIR)
_DIRS = [UPLOAD_DIR, STATIC_DIR, THUMBNAIL_DIR, JSON_DIR] 

# MongoDB setting
args = getArgs()
_MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
client = MongoClient(_MONGO_URL)
localdb = client[args.db]
if args.username:
    localdb.authenticate(args.username, args.password)
fs = gridfs.GridFS(localdb)

#####
_EXTENSIONS = ['png', 'jpeg', 'jpg', 'JPEG', 'jpe', 'jfif', 'pjpeg', 'pjp', 'gif']

def bin2image( typ, binary ):
    if typ in _EXTENSIONS:
        data = 'data:image/png;base64,' + binary
    if typ == 'pdf':
        filePdf = open( '{}/image.pdf'.format( TMP_DIR ), 'wb' )
        binData = a2b_base64( binary )
        filePdf.write( binData )
        filePdf.close()
        path = '{}/image.pdf'.format( TMP_DIR )
        image = convert_from_path( path )
        image[0].save( '{}/image.png'.format( TMP_DIR ), 'png' )
        binaryPng = open( '{}/image.png'.format( TMP_DIR ), 'rb' )
        byte = base64.b64encode( binaryPng.read() ).decode()
        binaryPng.close()
        data = 'data:image/png;base64,' + byte
    return data

#####
# user funtion
def addRequest(userinfo):
    password = hashlib.md5(userinfo[5].encode('utf-8')).hexdigest()
    localdb.request.insert({ 'userName'   : userinfo[0],
                             'firstName'  : userinfo[1],
                             'lastName'   : userinfo[2],
                             'email'      : userinfo[3],
                             'institution': userinfo[4],
                             'type'       : 'user', 
                             'password'   : password })
def addUser(userinfo):
    localdb.user.insert({ 'userName'   : userinfo['userName'],
                          'firstName'  : userinfo['firstName'],
                          'lastName'   : userinfo['lastName'],
                          'authority'  : int(userinfo['authority']),
                          'institution': userinfo['institution'],
                          'type'       : userinfo['type'], 
                          'email'      : userinfo['email'],
                          'passWord'   : userinfo['password'] })
   
def removeRequest(userid):
    localdb.request.remove({ '_id': ObjectId(userid) })

def removeUser(userid):
    localdb.user.remove({ '_id': ObjectId(userid) })

def makeDir():
    if not os.path.isdir(TMP_DIR): 
        os.mkdir(TMP_DIR)
    user_dir = TMP_DIR + '/' + str(session.get('uuid','localuser'))
    if not os.path.isdir(user_dir): 
        os.mkdir(user_dir)
    for dir_ in _DIRS:
        if not os.path.isdir(dir_): 
            os.mkdir(dir_)

def cleanDir(dir_name):
    if os.path.isdir(dir_name): 
        shutil.rmtree(dir_name)
    os.mkdir(dir_name)

def updateData(collection, query):
    localdb[collection].update(
        query, 
        {'$set': {'sys.rev': int(localdb[collection].find_one(query)['sys']['rev']+1), 
                  'sys.mts': datetime.utcnow()}}, 
        multi=True
    )

def countPhotoNum():
    if localdb.counter.find({'type': 'photoNumber'}).count() == 0:
        localdb.counter.insert({'type': 'photoNumber', 'num': 1})
    else:
        localdb.counter.update({'type': 'photoNumber'}, {'$set': {'num': int(localdb.counter.find_one({'type': 'photoNumber'})['num']+1)}})
    return int(localdb.counter.find_one({'type': 'photoNumber'})['num'])

def setTime(date):
    zone = session.get('timezone','UTC')
    converted_time = date.replace(tzinfo=timezone.utc).astimezone(pytz.timezone(zone))
    time = converted_time.strftime('%Y/%m/%d %H:%M:%S')
    return time

def setTimezone():
    # timezone
    timezones = []
    for tz in pytz.all_timezones:
        timezones.append(tz)
    if not 'timezone' in session:
        session['timezone'] = 'UTC'

    return timezones 

def setEnv(thisTestRun):
    env_list = thisTestRun.get('environments',[])
    env_dict = { 'list': env_list,
                 'num' : len(env_list) }
    return env_dict

######################################################################
# component function
def setPhotoDisplay(this_cmp):
    photo_display = []
    if 'attachments' in this_cmp: 
        data_entries = this_cmp['attachments']
        for data in data_entries:
            if (data.get('imageType') == 'image') and (data.get('display') == True):
                file_path = '{0}/{1}_{2}'.format(STATIC_DIR, data['photoNumber'], data['filename'])
                f = open(file_path, 'wb')
                f.write(fs.get(ObjectId(data['code'])).read())
                f.close()
                url = url_for('upload.static', filename='{0}_{1}'.format(data['photoNumber'], data['filename']))
                photo_display.append({'url':         url,
                                      'code':        data['code'],
                                      'photoNumber': data['photoNumber'],
                                      'stage':       data['stage'],
                                      'filename':    data['filename']})
    return photo_display

def setPhotoIndex(this_cmp):
    photo_index = []
    if 'attachments' in this_cmp: 
        data_entries = this_cmp['attachments']
        for data in data_entries:
            if data.get('imageType') == 'image':
                photo_index.append({'code':        data['code'],
                                    'photoNumber': data['photoNumber'],
                                    'datetime':    setTime(data['dateTime']),
                                    'stage':       data['stage']})
    return photo_index

def setPhotos(this_cmp, code):
    photos = {}
    if not code == '':
        data_entries = this_cmp['attachments']
        for data in data_entries:
            if code == data.get('code'):
                file_path = '{0}/{1}'.format(STATIC_DIR, data['filename'])
                f = open(file_path, 'wb')
                f.write(fs.get(ObjectId(code)).read())
                f.close()

                url = url_for('upload.static', filename='{}'.format( data['filename']))
                photos = {'url':         url,
                          'code':        data['code'],
                          'photoNumber': data['photoNumber'],
                          'stage':       data['stage'],
                          'display':     data.get('display', 'False'),
                          'filename':    data['filename']}
    return photos

# summary plot for each stage in component page
def setSummary():

    query = { '_id': ObjectId(session['this']) } 
    this_cmp = localdb.component.find_one(query)
    chip_type = this_cmp['chipType']
    serial_number = this_cmp['serialNumber']

    summary_index = []

    entries = {}
    # pick runs with 'summary: True' for each stage
    query = { 'component': session['this'] }
    ctr_entries = localdb.componentTestRun.find(query)
    runoids = []
    for ctr in ctr_entries:
        runoids.append(ctr['testRun'])
    for runoid in runoids:
        query = { '_id': ObjectId(runoid) }
        this_run = localdb.testRun.find_one( query )
        if 'stage' in this_run:
            stage = this_run['stage']
            if not stage in entries:
                entries.update({ stage: {} })
                for scan in listset.scan[chip_type]:
                    entries[stage].update({ scan: None })
        if this_run.get('summary'): 
            entries[stage].update({ this_run['testType']: this_run['_id'] })

    for stage in entries:
        scandict = {}
        datadict = { '1': { 'name': '_Dist', 'count': 0 }, '2': { 'name': '', 'count': 0 } }
        for scan in entries[stage]:
            maplist = []
            total = False
            scandict.update({scan: {}})
            if entries[stage][scan]:
                query = { '_id': entries[stage][scan] }
                this_run = localdb.testRun.find_one(query)
                query = { '_id': ObjectId(this_run['user_id']) }
                this_user = localdb.user.find_one( query )
                query = { 
                    'component': session['this'],
                    'testRun':   str(entries[stage][scan]) 
                }
                this_ctr = localdb.componentTestRun.find_one(query)
                for maptype in listset.scan[chip_type][scan]:
                    mapdict = {}
                    mapdict.update({'mapType': maptype[0]})
                    data_entries = this_ctr['attachments']
                    for data in data_entries:
                        for i in datadict:
                            if data['filename'] == '{0}{1}.png'.format(maptype[0], datadict[i]['name']):
                                datadict[i].update({ 'count': int(datadict[i]['count'])+1 })
                                file_path = '{0}/{1}_{2}_{3}_{4}.png'.format(THUMBNAIL_DIR, serial_number, stage, scan, data['title'])
                                mapdict.update({'code{}D'.format(i): data['code']})
                                if not os.path.isfile(file_path):
                                    binary = fs.get(ObjectId(data['code'])).read()
                                    f = open( '{0}/image.png'.format( TMP_DIR ), 'wb' )
                                    f.write(binary)
                                    f.close()
                                    image_bin = io.BytesIO(binary)
                                    image = Image.open(image_bin)
                                    image.thumbnail((int(image.width/4),int(image.height/4)))
                                    image.save(file_path)

                                url = url_for('thumbnail.static', filename='{0}_{1}_{2}_{3}.png'.format(serial_number, stage, scan, data['title']))
                                mapdict.update({'url{}Dthum'.format(i): url})

                    maplist.append(mapdict)

                #query = { 'resultId': str(entries[stage][scan]) }
                #thisRunInLocal = localdb.localdb.find_one( query )
                #if thisRunInLocal:
                #    count = thisRunInLocal['count']
                #else:
                #    writeDat(entries[stage][scan])
                #    count = {}
                #    if DOROOT:
                #        root.uuid = str(session.get('uuid','localuser'))
                #        count = root.countPix( scan, session['plotList'] )
                #    document = { 'resultId': str(entries[stage][scan]),
                #                 'count': count }
                #    localdb.localdb.insert( document )

                count = {}
                scandict[scan].update({
                    'runNumber':   this_run['runNumber'],
                    'institution': this_user['institution'],
                    'userName':    this_user['userName'], 
                    'total':       count.get('module',{}).get('score',None)
                })

            scandict[scan].update({
                'map': maplist,
                'num': len(maplist)
            })

        if not scandict == {}:
            summary_index.append({
                'stage': stage,
                'scan': scandict,
                '2Dnum': datadict['2']['count'],
                '1Dnum': datadict['1']['count']
            })

    return summary_index

## summary plot in add summary function page
#def setSummaryTest():
#
#    summary_index = {}
#    scanList = ['digitalscan', 'analogscan', 'thresholdscan', 'totscan', 'noisescan', 'selftrigger'] 
#    
#    if not session.get('stage'): return summary_index 
#
#    stage = session['stage']
#    query = {'_id': ObjectId(session.get('this'))}
#    this_cmp = localdb.component.find_one(query)
#
#    # first step in add summary function: make current summary plots as thumbnail
#    if not session['summaryList']['before']:
#
#        after_dir  = '{0}/{1}/after'.format(TMP_DIR, session.get('uuid','localuser'))
#        cleanDir(after_dir)
#
#        before_dir = '{0}/{1}/before'.format(TMP_DIR, session.get('uuid','localuser'))
#        cleanDir(before_dir)
#     
#        for scan in scanList:
#            session['summaryList']['before'].update({scan: {'runId': None}})
#            session['summaryList']['after'].update({scan: {'runId': None}})
#
#            query = {'component': session.get('this'), 'stage': stage, 'testType': scan}
#            run_entries = localdb.componentTestRun.find(query)
#            for componentTestRun in run_entries:
#                query = {'_id': ObjectId(componentTestRun['testRun'])}
#                this_run = localdb.testRun.find_one(query)
#                if this_run.get('summary'): 
#                    session['summaryList']['before'][scan].update({'runId': str(this_run['_id'])})
#                    session['summaryList']['after'][scan].update({'runId': str(this_run['_id'])})
#
#                    makePlot(str(this_run['_id']))
#
#                    for maptype in session.get('plotList'):
#                        if not session['plotList'][maptype].get('HistoType') == 2: continue
#                        url = {} 
#                        path = {}
#                        datadict = {'1': '_Dist', '2': ''}
#                        for i in datadict:
#                            filepath = '{0}/{1}/plot/{2}_{3}_{4}.png'.format(TMP_DIR, str(session.get('uuid','localuser')), str(this_run['testType']), str(maptype), i)
#                            if os.path.isfile(filepath):
#                                binary_file = open(filepath, 'rb')
#                                binary = binary_file.read()
#                                binary_file.close()
#
#                                image_bin = io.BytesIO(binary)
#                                image = Image.open(image_bin)
#                                image.thumbnail((int(image.width/4),int(image.height/4)))
#                                filename_before = '{0}/{1}_{2}_{3}_{4}{5}.png'.format(before_dir, stage, scan, this_cmp['serialNumber'], maptype, datadict[i])
#                                image.save(filename_before)
#                                filename_after  = '{0}/{1}_{2}_{3}_{4}{5}.png'.format(after_dir,  stage, scan, this_cmp['serialNumber'], maptype, datadict[i])
#                                image.save(filename_after)
#
#    # remove/replace summary plot: make replaced summary plots as thumbnail
#    elif session['step'] == 1:
#        after_dir  = '{0}/{1}/after'.format(TMP_DIR, session.get('uuid','localuser'))
#
#        for scan in scanList:
#            if not session.get('testType') == scan: continue
#
#            for r in glob.glob('{0}/{1}_{2}*'.format(after_dir, stage, scan)): os.remove(r)
#            
#            if session['summaryList']['after'][scan]['runId']:
#                query = {'_id': ObjectId(session['summaryList']['after'][scan]['runId'])}
#                this_run = localdb.testRun.find_one(query)
#
#                makePlot(str(this_run['_id']))
#
#                for maptype in session.get('plotList'):
#                    if not session['plotList'][maptype].get('HistoType') == 2: continue
#                    url = {} 
#                    path = {}
#                    datadict = {'1': '_Dist', '2': ''}
#                    for i in datadict:
#                        filepath = '{0}/{1}/plot/{2}_{3}_{4}.png'.format(TMP_DIR, str(session.get('uuid','localuser')), str(this_run['testType']), str(maptype), i)
#                        if os.path.isfile( filepath ):
#                            binary_file = open(filepath, 'rb')
#                            binary = binary_file.read()
#                            binary_file.close()
#
#                            image_bin = io.BytesIO(binary)
#                            image = Image.open(image_bin)
#                            image.thumbnail((int(image.width/4),int(image.height/4)))
#                            filename_after = '{0}/{1}_{2}_{3}_{4}{5}.png'.format(after_dir, stage, scan, this_cmp['serialNumber'], maptype, datadict[i])
#                            image.save(filename_after)
#
#    # check path to thumbnails 
#    scandict = {'before': {},
#                'after': {}}
#    total = 0
#    submit = True
#    for scan in scanList:
#
#        abType = {'before': '{0}/{1}/before'.format(TMP_DIR,session.get('uuid','localuser')), 
#                  'after': '{0}/{1}/after'.format(TMP_DIR,session.get('uuid','localuser'))}
#
#        for ab in abType:
#
#            scandict[ab].update({scan: {}})
#            maplist = []
#
#            for maptype in listset.scan[scan]:
#
#                mapdict = {'mapType': maptype[0]}
#
#                total += 1
#
#                if session['summaryList'][ab][scan]['runId']:
#
#                    query = {'_id': ObjectId(session['summaryList'][ab][scan]['runId'])}
#                    this_run = localdb.testRun.find_one(query)
#                    query = {'testRun': session['summaryList'][ab][scan]['runId']}
#                    this_ctr = localdb.componentTestRun.find_one(query)
#                    env_dict = setEnv(this_ctr)
#
#                    datadict = {'1': '_Dist', '2': ''}
#                    for i in datadict:
#
#                        filename = '{0}/{1}_{2}_{3}_{4}{5}.png'.format(abType[ab], stage, scan, this_cmp['serialNumber'], maptype[0], datadict[i])
#                        if os.path.isfile(filename):
#                            binary_image = open(filename, 'rb')
#                            code_base64 = base64.b64encode(binary_image.read()).decode()
#                            binary_image.close()
#                            url = bin2image('png', code_base64) 
#                            mapdict.update({'url{}Dthum'.format(i): url})
#
#                    scandict[ab][scan].update({'runNumber': this_run['runNumber'],
#                                               'runId': str(this_run['_id']),
#                                               'institution': this_run['institution'],
#                                               'userIdentity': this_run['userIdentity'],
#                                               'environment': env_dict})
#                maplist.append(mapdict)
#
#            # put suitable comment for each run
#            comment = '...'
#            if session['summaryList']['before'][scan]['runId'] == session['summaryList']['after'][scan]['runId']: 
#                comment = None
#            elif session['summaryList']['after'][scan].get('comment') in listset.summary_comment: 
#                comment = session['summaryList']['after'][scan]['comment']
#            elif not session['summaryList']['before'][scan]['runId']:
#                comment = 'add'
#            else:
#                submit =  False
#
#            scandict[ab][scan].update({'map': maplist,
#                                       'num': len(maplist),
#                                       'comment': comment})
#
#    if not scandict == {}:
#        summary_index.update({'stage': stage,
#                             'scan': scandict,
#                             'total': total,
#                             'submit': submit})
#
#    return summary_index
#
#def grade_module(moduleId):
#    scoreIndex = { 'stage': None }
#    scoreIndex.update({ 'module': {} })
#
#    query = { '_id': ObjectId(moduleId) }
#    this_module = localdb.component.find_one( query )
#
#    query = { 'parent': moduleId }
#    child_entries = localdb.childParentRelation.find( query )
#    for child in child_entries:
#        query = { '_id': ObjectId(child['child']) }
#        this_chip = localdb.component.find_one( query )
#        if 'chipId' in this_chip['serialNumber']:
#            scoreIndex.update({ str(this_chip['serialNumber'].split('chipId')[1]): {} })
#        else:
#            scoreIndex.update({ '1': {} })
#
#    entries = {}
#    for stage in listset.stage:
#        query = { 'component': moduleId, 'stage': stage }
#        run_entries = localdb.componentTestRun.find( query )
#        if run_entries.count() == 0: continue
#
#        scoreIndex.update({ 'stage': stage })
#
#        for run in run_entries:
#            query = { '_id': ObjectId(run['testRun']), 'summary': True }
#            this_run = localdb.testRun.find_one( query )
#            if this_run:
#                entries.update({ this_run['testType']: str(this_run['_id']) }) 
#        break
#
#    if entries == {}: return scoreIndex
#
#    for scan in listset.scan:
#        count = {}
#        if scan in entries : 
#            session['this'] = moduleId 
#
#            query = { 'resultId': str(entries[scan]) }
#            thisRunInLocal = localdb.localdb.find_one( query )
#            if thisRunInLocal:
#                count = thisRunInLocal['count']
#            else:
#                writeDat( entries[scan] )
#                count = {}
#                if DOROOT:
#                    root.uuid = str(session.get('uuid','localuser'))
#                    count = root.countPix( scan, session['plotList'] )
#                document = { 'resultId': str(entries[scan]),
#                             'count': count }
#                localdb.localdb.insert( document )
#
#        for component in scoreIndex:
#            if component == 'stage': continue
#            scoreIndex[component].update({ scan: count.get(component,0) })
#            scoreIndex[component].update({ 'total': scoreIndex[component].get('total',0) + count.get(component,{}).get('score',0) })
#
#    return scoreIndex
#

######################################################################

# run number list
def setResultIndex():

    result_index = {}

    chips = []
    query = { 'parent': session['this'] }
    child_entries = localdb.childParentRelation.find( query )
    for child in child_entries:
        chips.append({ 'component': child['child'] })

    query = { 'component': session['this'] }
    run_entries = localdb.componentTestRun.find( query )
    runoids = []
    for run in run_entries:
        runoids.append(run['testRun'])

    for runoid in runoids:
        query = { '_id': ObjectId(runoid) }
        this_run = localdb.testRun.find_one(query)
        query = { 
            'component': session['this'],
            'testRun': runoid 
        }
        this_ctr = localdb.componentTestRun.find_one( query )

        if chips == []:
            result = 'attachments' in this_ctr
        else:
            query = { '$or': chips }
            chip_run_entries = localdb.componentTestRun.find( query )
            result = True in [ 'attachments' in chip_run for chip_run in chip_run_entries ]

        stage = this_run.get('stage','null')
        test_type = this_run.get('testType')

        if not test_type in result_index: 
            result_index.update({ test_type: { 'run': [] } })

        count = {}
        #TODO
        #query = { 'resultId': str(this_run['_id']) }
        #thisRunInLocal = localdb.localdb.find_one( query )
        #if thisRunInLocal:
        #    count = thisRunInLocal['count']
        #else:
        #    writeDat(str(this_run['_id'])) 
        #    count = {}
        #    if DOROOT:
        #        root.uuid = str(session.get('uuid','localuser'))
        #        count = root.countPix( run.get('test_type'), session['plotList'] )
        #    document = { 'resultId': str(this_run['_id']),
        #                 'count': count }
        #    localdb.localdb.insert( document )
        #TODO

        result_index[test_type]['run'].append({ 
            '_id'      : str(this_run['_id']),
            'runNumber': this_run['runNumber'],
            'datetime' : setTime(this_run['startTime']),
            'result'   : result,
            'chips'    : len(chips),
            'stage'    : stage,
            'rate'     : count.get('module',{}).get('rate','-'),
            'score'    : count.get('module',{}).get('score',None),
            'values'   : count.get('module',{}).get('parameters',{}),
            'summary'  : this_run.get('summary') 
        })
    test_index = []
    for scan in result_index:
        run_index = sorted(result_index[scan]['run'], key=lambda x:x['datetime'], reverse=True)
        result_index.update({ 
            scan: { 
                'num': len(run_index),
                'run': run_index 
            }
        })
        test_index.append( scan )
    test_index.sort()
    result_index.update({ "index": test_index })

    return result_index

# make result plot in component page for the run
def setResults():

    results = {}

    if not session.get('runId'): return results

    query = { 
        'component': session['this'], 
        'testRun'  : session['runId'] 
    }
    this_ctr = localdb.componentTestRun.find_one(query)
    query = { '_id': ObjectId(session['runId']) }
    this_run = localdb.testRun.find_one(query)

    # get comments for this run
    query = { 'runId': session['runId'] }
    comments_entries = localdb.comments.find(query)
    comments = []
    for comment in comments_entries:
        comments.append(comment)

    # Change scheme
    ctrlconfig = {}
    if not this_run.get('ctrlCfg','...')=='...':
        query = { '_id': ObjectId(this_run['ctrlCfg']) }
        config_data = localdb.config.find_one( query )
        ctrlconfig.update({ 
            "filename" : config_data['filename'],
            "code"     : [config_data['data_id']],
            "configid" : [this_run['ctrlCfg']]
        })
    scanconfig = {}
    if not this_run.get('scanCfg','...')=='...':
        query = { '_id': ObjectId(this_run['scanCfg']) }
        config_data = localdb.config.find_one( query )
        scanconfig.update({ 
            "filename" : config_data['filename'],
            "code"     : [config_data['data_id']],
            "configid" : [this_run['scanCfg']] 
        })

    is_module = False
    if this_run['dummy']:
        if session['this'] == this_run['serialNumber']:
            is_module = True
    else:
        query = { '_id': ObjectId(session['this']) }
        this_cmp = localdb.component.find_one( query )
        if this_cmp['serialNumber'] == this_run['serialNumber']:
            is_module = True

    chipoids = []
    if is_module:
        query = { 'testRun': session['runId'] }
        ctr_entries = localdb.componentTestRun.find( query )
        for ctr in ctr_entries:
            if ctr['component'] != session['this']:
                chipoids.append( ctr['component'] )
    else:
        chipoids.append( session['this'] )

    chipid = []
    after_code = []
    after_configid = []
    before_code = []
    before_configid = []

    for i, chipoid in enumerate(chipoids):
        query = { 'component': chipoid, 'testRun': session['runId'] }
        this_chip_ctr = localdb.componentTestRun.find_one(query)
        chipid.append(i+1)

        afterconfig = {}
        if not this_chip_ctr.get('afterCfg','...')=='...':
            after_configid.append(this_chip_ctr['afterCfg'])   
            query = { '_id': ObjectId(this_chip_ctr['afterCfg']) }
            config_data = localdb.config.find_one(query)
            after_code.append(config_data['data_id'])

            query = { '_id': ObjectId(this_chip_ctr['afterCfg']) }
            afterconfig.update({ 
                "filename" : config_data['filename'],
                "code"     : after_code,
                "chipId"   : chipid, 
                "configid" : after_configid 
            })

        beforeconfig = {}
        if not this_chip_ctr.get('beforeCfg','...')=='...':
            before_configid.append(this_chip_ctr['beforeCfg'])   
            query = { '_id': ObjectId(this_chip_ctr['beforeCfg']) }
            config_data = localdb.config.find_one(query)
            before_code.append(config_data['data_id'])
            beforeconfig.update({ 
                "filename" : config_data['filename'],
                "code"     : before_code,
                "chipId"   : chipid,
                "configid" : before_configid 
            })

    query = { '_id': ObjectId(this_run['user_id']) }
    user = localdb.user.find_one( query )
    query = { '_id': ObjectId(this_run['address']) }
    site = localdb.institution.find_one( query )
    results.update({ 
        'datetime'    : setTime(this_run['startTime']),
        'testType'    : this_run['testType'],
        'runNumber'   : this_run['runNumber'],
        'comments'    : comments,
        'stage'       : this_run.get('stage'),
        'site'        : site['institution'].replace('_', ' '),
        'institution' : user['institution'].replace('_', ' '),
        'userIdentity': user['userName'].replace('_', ' '),
        'config'      : { 
            'ctrlCfg':   ctrlconfig, 
            'scanCfg':   scanconfig, 
            'beforeCfg': beforeconfig, 
            'afterCfg':  afterconfig 
        }
    }) 

    return results


def writeDat(cmpoid, runoid):

    query = { 'testRun': runoid, 'component': cmpoid }
    this_ctr = localdb.componentTestRun.find_one( query )
    if not this_ctr: return

    chipid = this_ctr.get('geomId',1)
    for data in this_ctr.get('attachments', []):
        if data['contentType'] == 'dat':
            query = { '_id': ObjectId(data['code']) }
            file_path = '{0}/{1}/dat/{2}-{3}.dat'.format(TMP_DIR, session.get('uuid','localuser'), chipid, data['title'])
            f = open(file_path, 'wb')
            f.write(fs.get(ObjectId(data['code'])).read())
            f.close()
            if data['title'] in session['plotList']:
                session['plotList'][data['title']]['chipIds'].append( chipid )
    return

def makePlot(cmpoid, runoid):
    query = { '_id': ObjectId(runoid) }
    this_run = localdb.testRun.find_one( query )
    if session.get('rootType'):
        root.uuid = str(session.get('uuid','localuser'))
        maptype = session['mapType']
        if session['rootType'] == 'set':
            root.setParameter( this_run['testType'], maptype, session['plotList'] )
            for maptype in session['plotList']: session['plotList'][maptype].update({'draw': True, 'parameter': {}})
        elif session['rootType'] == 'make':
            session['plotList'][maptype].update({'draw': True, 'parameter': session['parameter']})
    else:
        dat_dir = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/dat'
        cleanDir(dat_dir)

        session['plotList'] = {}
        for maptype in this_run.get('plots',[]):
            session['plotList'].update({maptype: {'draw': True, 'chipIds': []}})
        is_module = False
        if this_run['dummy']:
            if session['this'] == this_run['serialNumber']:
                is_module = True
        else:
            query = { '_id': ObjectId(session['this']) }
            this_cmp = localdb.component.find_one( query )
            if this_cmp['serialNumber'] == this_run['serialNumber']:
                is_module = True

        chipoids = []
        if is_module:
            query = { 'testRun': session['runId'] }
            ctr_entries = localdb.componentTestRun.find( query )
            for ctr in ctr_entries:
                if ctr['component'] != session['this']:
                    chipoids.append( ctr['component'] )
        else:
            chipoids.append( session['this'] )
        for chipoid in chipoids:
            writeDat( chipoid, runoid )

    if DOROOT:
        root.uuid = str(session.get('uuid','localuser'))
        for maptype in this_run.get('plots',[]):
            if not session['plotList'][maptype]['draw']: continue
            session['plotList'][maptype]['filled'] = False
            chipids = session['plotList'][maptype]['chipIds']
            for chipid in chipids:
                session['plotList'] = root.fillHisto(this_run['testType'], maptype, int(chipid), session['plotList'])
            if session['plotList'][maptype]['filled']:
                root.outHisto(this_run['testType'], maptype, session['plotList'])
            session['plotList'][maptype]['draw'] = False

    session.pop('rootType',  None)
    session.pop('mapType',   None)
    session.pop('parameter', None)

    return

# list plot created by 'makePlot' using PyROOT
def setRoots():

    roots = {}

    if not session.get('runId'): return roots

    makePlot( session['this'], session['runId'] )
    query = { '_id': ObjectId(session['runId']) }
    this_run = localdb.testRun.find_one(query)

    results = []
    for maptype in this_run.get('plots',[]):
        result = {
            'mapType' : maptype,
            'sortkey' : '{}0'.format(maptype),
            'runId'   : session['runId'],
            'plot'    : False
        }
        if session['plotList'][maptype].get('HistoType') == 2:
            url = {} 
            for i in ['1', '2']:
                filename = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/plot/' + str(this_run['testType']) + '_' + str(maptype) + '_{}.png'.format(i)
                if os.path.isfile(filename):
                    binary_image = open(filename, 'rb')
                    code_base64 = base64.b64encode(binary_image.read()).decode()
                    binary_image.close()
                    url.update({i: bin2image('png', code_base64)}) 
            result.update({
                'plot'    : True,
                'setLog'  : session['plotList'][maptype]['parameter']['log'], 
                'minValue': session['plotList'][maptype]['parameter']['min'],
                'maxValue': session['plotList'][maptype]['parameter']['max'],
                'binValue': session['plotList'][maptype]['parameter']['bin'],
                'urlDist' : url.get('1'),
                'urlMap'  : url.get('2')
            })
        results.append(result)

    results = sorted(results, key=lambda x:int((re.search(r'[0-9]+',x['sortkey'])).group(0)), reverse=True)

    if DOROOT:
        roots.update({'rootsw': True})
    else:
        roots.update({'rootsw': False})

    roots.update({'results': results})

    return roots

def getData(mo_serial_number,maptype):

    myzip = zipfile.ZipFile('{0}/{1}/dat/{2}_{3}.zip'.format(TMP_DIR, session.get('uuid','localuser'),mo_serial_number,maptype),'a')
    for i in session['plotList'][maptype]['chipIds']:
        myzip.write('{0}/{1}/dat/{2}-{3}.dat'.format(TMP_DIR, session.get('uuid','localuser'), i, maptype),'{0}_chip{1}_{2}.dat'.format(mo_serial_number,i,maptype))
    myzip.close()
    filename = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/dat/' + str(mo_serial_number) + '_' + str(maptype) + '.zip'

    return filename

def writeConfig(mo_serial_number,config_type):
    
    config_dir = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/config'
    cleanDir(config_dir)
    myzip = zipfile.ZipFile('{0}/{1}/config/{2}_{3}.zip'.format(TMP_DIR, session.get('uuid','localuser'),mo_serial_number, config_type),'a')

    if session.get('runId'):
        query = { 'component': session['this'], 
                  'testRun'  : session['runId'] }
        this_ctr = localdb.componentTestRun.find_one(query)
        query = { '_id': ObjectId(session['runId']) }
        this_run = localdb.testRun.find_one(query)


        # Change scheme
        if config_type == 'ctrlCfg' or config_type == 'scanCfg':
            if not this_run.get(config_type,'...')=='...':
                query = { '_id': ObjectId(this_run[config_type]) }
                config_data = localdb.config.find_one( query )
                file_path = '{0}/{1}/config/{2}_{3}.json'.format(TMP_DIR, session.get('uuid','localuser'),mo_serial_number, config_type)
                f = open(file_path, 'wb')
                f.write(fs.get(ObjectId(config_data['data_id'])).read())
                f.close()
                
                myzip.write('{0}/{1}/config/{2}_{3}.json'.format(TMP_DIR, session.get('uuid','localuser'),mo_serial_number, config_type),'{0}_{1}.json'.format(mo_serial_number, config_type))

        elif config_type == 'afterCfg' or 'beforeCfg':        
            
            if not this_run['dummy']:
                query = [{ 'parent': session['this'] }, { 'child': session['this'] }]
                child_entries = localdb.childParentRelation.find({'$or': query})
          
                 

                for child in child_entries:
                    query = { 'component': child['child'], 'testRun': session['runId'] }
                    this_chip_ctr = localdb.componentTestRun.find_one(query)
                    if not this_chip_ctr.get(config_type,'...')=='...':
                        chipid = child['chipId']
                        configid = this_chip_ctr[config_type] 
                 
                        query = { '_id': ObjectId(configid) }
                        config_data = localdb.config.find_one(query)

                        file_path = '{0}/{1}/config/{2}_chip{3}_{4}.json'.format(TMP_DIR, session.get('uuid','localuser'),mo_serial_number, chipid, config_type)
                        f = open(file_path, 'wb')
                        f.write(fs.get(ObjectId(config_data['data_id'])).read())
                        f.close()
                        
                        myzip.write('{0}/{1}/config/{2}_chip{3}_{4}.json'.format(TMP_DIR, session.get('uuid','localuser'),mo_serial_number, chipid, config_type),'{0}_chip{1}_{2}.json'.format(mo_serial_number, chipid, config_type))
        
            else:
                query = {'testRun': session['runId'] }
                this_chip_ctrs = localdb.componentTestRun.find(query)
                for this_chip_ctr in this_chip_ctrs: 
                    if not this_chip_ctr.get(config_type,'...')=='...':
                        chipid = '1'
                        configid = this_chip_ctr[config_type] 
                          
                        query = { '_id': ObjectId(configid) }
                        config_data = localdb.config.find_one(query)

                        file_path = '{0}/{1}/config/{2}_chip{3}_{4}.json'.format(TMP_DIR, session.get('uuid','localuser'),mo_serial_number, chipid, config_type)
                        f = open(file_path, 'wb')
                        f.write(fs.get(ObjectId(config_data['data_id'])).read())
                        f.close()
                        
                        myzip.write('{0}/{1}/config/{2}_chip{3}_{4}.json'.format(TMP_DIR, session.get('uuid','localuser'),mo_serial_number, chipid, config_type),'{0}_chip{1}_{2}.json'.format(mo_serial_number, chipid, config_type))
        

    myzip.close()
    
    filename = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/config/' + str(mo_serial_number) + '_' + str(config_type) + '.zip'
    return filename

def make_dcsplot(runId):
    environmentId=localdb.testRun.find_one({"_id":ObjectId(runId)}).get('environment')
    if environmentId=="...":
        return 1

    startTime=localdb.testRun.find_one({"_id":ObjectId(runId)}).get('startTime')
    finishTime=localdb.testRun.find_one({"_id":ObjectId(runId)}).get('finishTime')
    startTime=time.mktime(startTime.timetuple())
    finishTime=time.mktime(finishTime.timetuple())

    DCS_data_block=localdb.environment.find_one({"_id":ObjectId(environmentId)})

    if not session['dcsStat'].get('timeRange') :
        session['dcsStat'].update({'timeRange' : [startTime-10,finishTime+10]})
    if not session['dcsStat'].get('RunTime') :
        session['dcsStat'].update({'RunTime' : [startTime,finishTime]})

    session['dcsList']=dcs_plot.dcs_plot(DCS_data_block,startTime,finishTime,session['dcsList'])
def setDCS():
    dcs_data={}
    session['dcsList']={}
    DCS_DIR  = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/dcs'

    cleanDir(DCS_DIR)

    if not session.get( 'runId' ) : return dcs_data    
    if not DODCS :
        dcs_data.update({'dcssw': False})
        return dcs_data

    if not session.get( 'dcsStat' ) : session['dcsStat']={}
    if not session['dcsStat'].get('runId') == session.get('runId'):
        session['dcsStat']={}
        session['dcsStat'].update({ 'runId' : session.get('runId')})
    results={}
    url={}
    results['iv']=[]
    results['other']=[]
    results['stat']={}

    dcs_status=make_dcsplot(session['runId'])
    if dcs_status==1 : 
        dcs_data.update({ 'dcssw' : True,
                          'dcs_data_exist' : False })
        return dcs_data
    if session.get('dcsList'):
        for dcsType in session.get( 'dcsList' ):
            if session['dcsList'][dcsType].get( 'file_num' ) :
                file_num=session['dcsList'][dcsType].get('file_num')
                fileList=session['dcsList'][dcsType].get('filename')
                if file_num==2 :
                    for i,filename in zip(["1","2"],fileList) :
                        if os.path.isfile( filename ) :
                            binary_image = open( filename, 'rb' )
                            code_base64 = base64.b64encode(binary_image.read()).decode()
                            binary_image.close()
                            url.update({ i : bin2image( 'png', code_base64 ) })
                    results['iv'].append({ 'dcsType' : dcsType ,
                                           'keyName' : session['dcsList'][dcsType].get('keyName'),
                                           'runId'   : session.get('runId'),
                                           'url_v'   : url.get("1"),
                                           'url_i'   : url.get("2"),
                                           'sortkey' : '{}0'.format(dcsType),
                                           'v_min'   : session['dcsList'][dcsType].get('v_min'),
                                           'v_max'   : session['dcsList'][dcsType].get('v_max'),
                                           'v_step'  : session['dcsList'][dcsType].get('v_step'),
                                           'i_min'   : session['dcsList'][dcsType].get('i_min'),
                                           'i_max'   : session['dcsList'][dcsType].get('i_max'),
                                           'i_step'  : session['dcsList'][dcsType].get('i_step')
                                       })
                if file_num==1 :
                    for filename in fileList :
                        if os.path.isfile( filename ) :
                            binary_image = open( filename, 'rb' )
                            code_base64 = base64.b64encode(binary_image.read()).decode()
                            binary_image.close()
                            i="1"
                            url.update({ i : bin2image( 'png', code_base64 ) })
                    results['other'].append({ 'dcsType' : dcsType ,
                                              'keyName' : dcsType ,
                                              'runId'   : session.get('runId'),
                                              'url'     : url.get("1"),
                                              'sortkey' : '{}0'.format(dcsType),
                                              'min'     : session['dcsList'][dcsType].get('min'),
                                              'max'     : session['dcsList'][dcsType].get('max'),
                                              'step'    : session['dcsList'][dcsType].get('step')
                                          })
    timeRange=[]
    timeRange.append(datetime.fromtimestamp(session['dcsStat'].get('timeRange')[0]))
    timeRange.append(datetime.fromtimestamp(session['dcsStat'].get('timeRange')[1]))

    results['stat']={ 'RunTime'  : { 'start'  : datetime.fromtimestamp(session['dcsStat']['RunTime'][0]),
                                     'finish' : datetime.fromtimestamp(session['dcsStat']['RunTime'][1])
                                 },
                      'runId'    : session.get('runId'),
                      'timeRange': { 'start' : { 'year'  : timeRange[0].strftime('%Y'),
                                                 'month' : timeRange[0].strftime('%m'),
                                                 'day'   : timeRange[0].strftime('%d'),
                                                 'hour'  : timeRange[0].strftime('%H'),
                                                 'minute': timeRange[0].strftime('%M'),
                                                 'second': timeRange[0].strftime('%S')
                                             },
                                     'end'   : { 'year'  : timeRange[1].strftime('%Y'),
                                                 'month' : timeRange[1].strftime('%m'),
                                                 'day'   : timeRange[1].strftime('%d'),
                                                 'hour'  : timeRange[1].strftime('%H'),
                                                 'minute': timeRange[1].strftime('%M'),
                                                 'second': timeRange[1].strftime('%S')
                                             }
                      },
                      'unixtimeR': { 'start' : datetime.fromtimestamp(session['dcsStat'].get('timeRange')[0]),
                                     'end'   : datetime.fromtimestamp(session['dcsStat'].get('timeRange')[1])
                      }
    }
    dcs_data.update({'dcssw'          : True,
                     'dcs_data_exist' : True,
                     'results'        : results})
    return dcs_data
