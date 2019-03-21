# modules
import os
import pwd
import glob
import json
import re
import shutil
import base64  # Base64 encoding scheme
import datetime
import hashlib
import gridfs # gridfs system 
import io

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

# directories 
"""
 /
 `-- tmp
      |-- [username who execute app.py]
               |-- [reader1's userid] ... reader's directory (created and reset in app.py) 
               |      :
               |-- [reader#'s userid]
               |        |-- dat    ... dat files  (reset in write_dat())
               |        |-- plot   ... plot files (reset in make_plot()) 
               |        |-- before ... previous summary plots in add_summary function (reset in first time fill_summary_test())
               |        `-- after  ... modified summary plots in add_summary function (reset in first time fill_summary_test())
               | 
               |-- thumbnail ... summary plots (reset after add_summary function)
               |        `-- [reader's userid] ... summary plots for user (created and reset in show_summary())
               `-- json ... json file ; <reader's userid>_parameter.json (created in make_plot())
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
yarrdb = client[args.db]
if args.username:
    yarrdb.authenticate(args.username, args.password)
userdb = client[args.userdb]
fs = gridfs.GridFS(yarrdb)

#####
_EXTENSIONS = ['png', 'jpeg', 'jpg', 'JPEG', 'jpe', 'jfif', 'pjpeg', 'pjp', 'gif']

def allowed_file(filename):
   return '.' in filename and \
       filename.rsplit('.', 1)[1] in _EXTENSIONS

def bin_to_image( typ, binary ):
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
def add_request(userinfo):
    password = hashlib.md5(userinfo[5].encode('utf-8')).hexdigest()
    userdb.request.insert({ 'userName'   : userinfo[0],
                            'firstName'  : userinfo[1],
                            'lastName'   : userinfo[2],
                            'email'      : userinfo[3],
                            'institution': userinfo[4],
                            'type'       : 'user', 
                            'password'   : password })
def add_user(userinfo):
    userdb.user.insert({ 'userName'   : userinfo['userName'],
                         'firstName'  : userinfo['firstName'],
                         'lastName'   : userinfo['lastName'],
                         'authority'  : int(userinfo['authority']),
                         'institution': userinfo['institution'],
                         'type'       : userinfo['type'], 
                         'email'      : userinfo['email'],
                         'passWord'   : userinfo['password'] })
   
def remove_request(userid):
    userdb.request.remove({ '_id': ObjectId(userid) })

def remove_user(userid):
    userdb.user.remove({ '_id': ObjectId(userid) })

def input_v(message):
    answer = ''
    if args.fpython == 2: 
        answer = raw_input(message) 
    if args.fpython == 3: 
        answer =     input(message)
    return answer

######################################################################
# function 
def make_dir():
    if not os.path.isdir(TMP_DIR): 
        os.mkdir(TMP_DIR)
    user_dir = TMP_DIR + '/' + str(session.get('uuid','localuser'))
    if not os.path.isdir(user_dir): 
        os.mkdir(user_dir)
    for dir_ in _DIRS:
        if not os.path.isdir(dir_): 
            os.mkdir(dir_)

def clean_dir(dir_name):
    if os.path.isdir(dir_name): 
        shutil.rmtree(dir_name)
    os.mkdir(dir_name)

def update_mod(collection, query):
    yarrdb[collection].update(query, 
                                {'$set': {'sys.rev': int(yarrdb[collection].find_one(query)['sys']['rev']+1), 
                                          'sys.mts': datetime.datetime.utcnow()}}, 
                                multi=True)

def count_photoNum():
    if userdb.counter.find({'type': 'photoNumber'}).count() == 0:
        userdb.counter.insert({'type': 'photoNumber', 'num': 1})
    else:
        userdb.counter.update({'type': 'photoNumber'}, {'$set': {'num': int(userdb.counter.find_one({'type': 'photoNumber'})['num']+1)}})
    return int(userdb.counter.find_one({'type': 'photoNumber'})['num'])

def set_time(date):
    DIFF_FROM_UTC = args.timezone 
    time = (date+datetime.timedelta(hours=DIFF_FROM_UTC)).strftime('%Y/%m/%d %H:%M:%S')
    return time

def allowed_file(filename):
    ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def fill_env(thisTestRun):
    env_list = thisTestRun.get('environments',[])
    env_dict = { 'list': env_list,
                 'num' : len(env_list) }
    return env_dict

######################################################################
# component function
def fill_photoDisplay(thisComponent):
    photoDisplay = []
    if 'attachments' in thisComponent: 
        data_entries = thisComponent['attachments']
        for data in data_entries:
            if (data.get('imageType') == 'image') and (data.get('display') == True):
                filePath = '{0}/{1}_{2}'.format(STATIC_DIR, data['photoNumber'], data['filename'])
                f = open(filePath, 'wb')
                f.write(fs.get(ObjectId(data['code'])).read())
                f.close()
                url = url_for('upload.static', filename='{0}_{1}'.format(data['photoNumber'], data['filename']))
                photoDisplay.append({'url': url,
                                     'code': data['code'],
                                     'photoNumber': data['photoNumber'],
                                     'stage': data['stage'],
                                     'filename': data['filename']})
    return photoDisplay

def fill_photoIndex(thisComponent):
    photoIndex = []
    if 'attachments' in thisComponent: 
        data_entries = thisComponent['attachments']
        for data in data_entries:
            if data.get('imageType') == 'image':
                photoIndex.append({'code': data['code'],
                                   'photoNumber': data['photoNumber'],
                                   'datetime': set_time(data['dateTime']),
                                   'stage': data['stage']})
    return photoIndex

def fill_photos(thisComponent, code):
    photos = {}
    if not code == '':
        data_entries = thisComponent['attachments']
        for data in data_entries:
            if code == data.get('code'):
                filePath = '{0}/{1}'.format(STATIC_DIR, data['filename'])
                f = open(filePath, 'wb')
                f.write(fs.get(ObjectId(code)).read())
                f.close()

                url = url_for('upload.static', filename='{}'.format( data['filename']))
                photos = {'url': url,
                          'code': data['code'],
                          'photoNumber': data['photoNumber'],
                          'stage': data['stage'],
                          'display': data.get('display', 'False'),
                          'filename': data['filename']}
    return photos

######################################################################

# summary plot for each stage in component page
def fill_summary():

    query = { '_id': ObjectId(session['this']) } 
    thisComponent = yarrdb.component.find_one(query)
    chipType = thisComponent['chipType']
    serialNumber = thisComponent['serialNumber']

    summaryIndex = []

    entries = {}
    # pick runs with 'display: True' for each stage
    query = { 'component': session['this'] }
    ctr_entries = yarrdb.componentTestRun.find( query )
    for thisComponentTestRun in ctr_entries:
        query = { '_id': ObjectId(thisComponentTestRun['testRun']) }
        thisRun = yarrdb.testRun.find_one( query )
        if not thisRun.get('stage') == '':
            stage = thisRun['stage']
            if not stage in entries:
                entries.update({ stage: {} })
                for scan in listset.scan[chipType]:
                    entries[stage].update({ scan: None })
        if thisRun.get('display'): 
            entries[stage].update({ thisRun['testType']: thisRun['_id'] })

    for stage in entries:
        scandict = {}
        datadict = { '1': { 'name': '_Dist', 'count': 0 }, '2': { 'name': '', 'count': 0 } }
        for scan in entries[stage]:
            mapList = []
            total = False
            scandict.update({scan: {}})
            if entries[stage][scan]:
                query = { '_id': entries[stage][scan] }
                thisRun = yarrdb.testRun.find_one(query)
                query = { '_id': ObjectId(thisRun['user_id']) }
                thisUser = yarrdb.user.find_one( query )
                query = { 'component': session['this'], 'testRun': str(entries[stage][scan]) }
                thisComponentTestRun = yarrdb.componentTestRun.find_one(query)
                for mapType in listset.scan[chipType][scan]:
                    mapDict = {}
                    mapDict.update({'mapType': mapType[0]})
                    data_entries = thisComponentTestRun['attachments']
                    for data in data_entries:
                        for i in datadict:
                            if data['filename'] == '{0}{1}.png'.format(mapType[0], datadict[i]['name']):
                                datadict[i].update({ 'count': int(datadict[i]['count'])+1 })
                                filePath = '{0}/{1}_{2}_{3}_{4}.png'.format(THUMBNAIL_DIR, serialNumber, stage, scan, data['title'])
                                mapDict.update({'code{}D'.format(i): data['code']})
                                if not os.path.isfile(filePath):
                                    binary = fs.get(ObjectId(data['code'])).read()
                                    f = open( '{0}/image.png'.format( TMP_DIR ), 'wb' )
                                    f.write(binary)
                                    f.close()
                                    image_bin = io.BytesIO(binary)
                                    image = Image.open(image_bin)
                                    image.thumbnail((int(image.width/4),int(image.height/4)))
                                    image.save(filePath)

                                url = url_for('thumbnail.static', filename='{0}_{1}_{2}_{3}.png'.format(serialNumber, stage, scan, data['title']))
                                mapDict.update({'url{}Dthum'.format(i): url})

                    mapList.append(mapDict)

                #query = { 'resultId': str(entries[stage][scan]) }
                #thisRunInLocal = userdb.localdb.find_one( query )
                #if thisRunInLocal:
                #    count = thisRunInLocal['count']
                #else:
                #    write_dat(entries[stage][scan])
                #    count = {}
                #    if DOROOT:
                #        root.uuid = str(session.get('uuid','localuser'))
                #        count = root.countPix( scan, session['plotList'] )
                #    document = { 'resultId': str(entries[stage][scan]),
                #                 'count': count }
                #    userdb.localdb.insert( document )

                count = {}
                scandict[scan].update({'runNumber':    thisRun['runNumber'],
                                       'institution':  thisUser['institution'],
                                       'userName': thisUser['userName'], 
                                       'total':        count.get('module',{}).get('score',None)})

            scandict[scan].update({'map': mapList,
                                   'num': len(mapList)})

        if not scandict == {}:
            summaryIndex.append({'stage': stage,
                                 'scan': scandict,
                                 '2Dnum': datadict['2']['count'],
                                 '1Dnum': datadict['1']['count'] })

    return summaryIndex

# summary plot in add summary function page
def fill_summary_test():

    summaryIndex = {}
    scanList = ['digitalscan', 'analogscan', 'thresholdscan', 'totscan', 'noisescan', 'selftrigger'] 
    
    if not session.get('stage'): return summaryIndex 

    stage = session['stage']
    query = {'_id': ObjectId(session.get('this'))}
    thisComponent = yarrdb.component.find_one(query)

    # first step in add summary function: make current summary plots as thumbnail
    if not session['summaryList']['before']:

        after_dir  = '{0}/{1}/after'.format(TMP_DIR, session.get('uuid','localuser'))
        clean_dir(after_dir)

        before_dir = '{0}/{1}/before'.format(TMP_DIR, session.get('uuid','localuser'))
        clean_dir(before_dir)
     
        for scan in scanList:
            session['summaryList']['before'].update({scan: {'runId': None}})
            session['summaryList']['after'].update({scan: {'runId': None}})

            query = {'component': session.get('this'), 'stage': stage, 'testType': scan}
            run_entries = yarrdb.componentTestRun.find(query)
            for componentTestRun in run_entries:
                query = {'_id': ObjectId(componentTestRun['testRun'])}
                thisRun = yarrdb.testRun.find_one(query)
                if thisRun.get('display'): 
                    session['summaryList']['before'][scan].update({'runId': str(thisRun['_id'])})
                    session['summaryList']['after'][scan].update({'runId': str(thisRun['_id'])})

                    make_plot(str(thisRun['_id']))

                    for mapType in session.get('plotList'):
                        if session['plotList'][mapType]['HistoType'] == 1: continue
                        url = {} 
                        path = {}
                        datadict = {'1': '_Dist', '2': ''}
                        for i in datadict:
                            filepath = '{0}/{1}/plot/{2}_{3}_{4}.png'.format(TMP_DIR, str(session.get('uuid','localuser')), str(thisRun['testType']), str(mapType), i)
                            if os.path.isfile(filepath):
                                binary_file = open(filepath, 'rb')
                                binary = binary_file.read()
                                binary_file.close()

                                image_bin = io.BytesIO(binary)
                                image = Image.open(image_bin)
                                image.thumbnail((int(image.width/4),int(image.height/4)))
                                filename_before = '{0}/{1}_{2}_{3}_{4}{5}.png'.format(before_dir, stage, scan, thisComponent['serialNumber'], mapType, datadict[i])
                                image.save(filename_before)
                                filename_after  = '{0}/{1}_{2}_{3}_{4}{5}.png'.format(after_dir,  stage, scan, thisComponent['serialNumber'], mapType, datadict[i])
                                image.save(filename_after)

    # remove/replace summary plot: make replaced summary plots as thumbnail
    elif session['step'] == 1:
        after_dir  = '{0}/{1}/after'.format(TMP_DIR, session.get('uuid','localuser'))

        for scan in scanList:
            if not session.get('testType') == scan: continue

            for r in glob.glob('{0}/{1}_{2}*'.format(after_dir, stage, scan)): os.remove(r)
            
            if session['summaryList']['after'][scan]['runId']:
                query = {'_id': ObjectId(session['summaryList']['after'][scan]['runId'])}
                thisRun = yarrdb.testRun.find_one(query)

                make_plot(str(thisRun['_id']))

                for mapType in session.get('plotList'):
                    if session['plotList'][mapType]['HistoType'] == 1: continue
                    url = {} 
                    path = {}
                    datadict = {'1': '_Dist', '2': ''}
                    for i in datadict:
                        filepath = '{0}/{1}/plot/{2}_{3}_{4}.png'.format(TMP_DIR, str(session.get('uuid','localuser')), str(thisRun['testType']), str(mapType), i)
                        if os.path.isfile( filepath ):
                            binary_file = open(filepath, 'rb')
                            binary = binary_file.read()
                            binary_file.close()

                            image_bin = io.BytesIO(binary)
                            image = Image.open(image_bin)
                            image.thumbnail((int(image.width/4),int(image.height/4)))
                            filename_after = '{0}/{1}_{2}_{3}_{4}{5}.png'.format(after_dir, stage, scan, thisComponent['serialNumber'], mapType, datadict[i])
                            image.save(filename_after)

    # check path to thumbnails 
    scandict = {'before': {},
                'after': {}}
    total = 0
    submit = True
    for scan in scanList:

        abType = {'before': '{0}/{1}/before'.format(TMP_DIR,session.get('uuid','localuser')), 
                  'after': '{0}/{1}/after'.format(TMP_DIR,session.get('uuid','localuser'))}

        for ab in abType:

            scandict[ab].update({scan: {}})
            mapList = []

            for mapType in listset.scan[scan]:

                mapDict = {'mapType': mapType[0]}

                total += 1

                if session['summaryList'][ab][scan]['runId']:

                    query = {'_id': ObjectId(session['summaryList'][ab][scan]['runId'])}
                    thisRun = yarrdb.testRun.find_one(query)
                    query = {'testRun': session['summaryList'][ab][scan]['runId']}
                    thisComponentTestRun = yarrdb.componentTestRun.find_one(query)
                    env_dict = fill_env(thisComponentTestRun)

                    datadict = {'1': '_Dist', '2': ''}
                    for i in datadict:

                        filename = '{0}/{1}_{2}_{3}_{4}{5}.png'.format(abType[ab], stage, scan, thisComponent['serialNumber'], mapType[0], datadict[i])
                        if os.path.isfile(filename):
                            binary_image = open(filename, 'rb')
                            code_base64 = base64.b64encode(binary_image.read()).decode()
                            binary_image.close()
                            url = bin_to_image('png', code_base64) 
                            mapDict.update({'url{}Dthum'.format(i): url})

                    scandict[ab][scan].update({'runNumber': thisRun['runNumber'],
                                               'runId': str(thisRun['_id']),
                                               'institution': thisRun['institution'],
                                               'userIdentity': thisRun['userIdentity'],
                                               'environment': env_dict})
                mapList.append(mapDict)

            # put suitable comment for each run
            comment = '...'
            if session['summaryList']['before'][scan]['runId'] == session['summaryList']['after'][scan]['runId']: 
                comment = None
            elif session['summaryList']['after'][scan].get('comment') in listset.summary_comment: 
                comment = session['summaryList']['after'][scan]['comment']
            elif not session['summaryList']['before'][scan]['runId']:
                comment = 'add'
            else:
                submit =  False

            scandict[ab][scan].update({'map': mapList,
                                       'num': len(mapList),
                                       'comment': comment})

    if not scandict == {}:
        summaryIndex.update({'stage': stage,
                             'scan': scandict,
                             'total': total,
                             'submit': submit})

    return summaryIndex

def grade_module(moduleId):
    scoreIndex = { 'stage': None }
    scoreIndex.update({ 'module': {} })

    query = { '_id': ObjectId(moduleId) }
    thisModule = yarrdb.component.find_one( query )

    query = { 'parent': moduleId }
    child_entries = yarrdb.childParentRelation.find( query )
    for child in child_entries:
        query = { '_id': ObjectId(child['child']) }
        thisChip = yarrdb.component.find_one( query )
        if 'chipId' in thisChip['serialNumber']:
            scoreIndex.update({ str(thisChip['serialNumber'].split('chipId')[1]): {} })
        else:
            scoreIndex.update({ '1': {} })

    entries = {}
    for stage in listset.stage:
        query = { 'component': moduleId, 'stage': stage }
        run_entries = yarrdb.componentTestRun.find( query )
        if run_entries.count() == 0: continue

        scoreIndex.update({ 'stage': stage })

        for run in run_entries:
            query = { '_id': ObjectId(run['testRun']), 'display': True }
            thisRun = yarrdb.testRun.find_one( query )
            if thisRun:
                entries.update({ thisRun['testType']: str(thisRun['_id']) }) 
        break

    if entries == {}: return scoreIndex

    for scan in listset.scan:
        count = {}
        if scan in entries : 
            session['this'] = moduleId 

            query = { 'resultId': str(entries[scan]) }
            thisRunInLocal = userdb.localdb.find_one( query )
            if thisRunInLocal:
                count = thisRunInLocal['count']
            else:
                write_dat( entries[scan] )
                count = {}
                if DOROOT:
                    root.uuid = str(session.get('uuid','localuser'))
                    count = root.countPix( scan, session['plotList'] )
                document = { 'resultId': str(entries[scan]),
                             'count': count }
                userdb.localdb.insert( document )

        for component in scoreIndex:
            if component == 'stage': continue
            scoreIndex[component].update({ scan: count.get(component,0) })
            scoreIndex[component].update({ 'total': scoreIndex[component].get('total',0) + count.get(component,{}).get('score',0) })

    return scoreIndex


######################################################################

# run number list
def fill_resultIndex():

    resultIndex = {}
    testIndex = []
    runs = []

    chips = []
    query = { 'parent': session['this'] }
    child_entries = yarrdb.childParentRelation.find( query )
    for child in child_entries:
        chips.append({ 'component': child['child'] })

    query = { 'component': session['this'] }
    run_entries = yarrdb.componentTestRun.find( query )
    for run in run_entries:
        query = { '_id': ObjectId(run['testRun']) }
        thisRun = yarrdb.testRun.find_one(query)

        if chips == []:
            result = 'attachments' in run
        else:
            query = { '$or': chips }
            chip_run_entries = yarrdb.componentTestRun.find( query )
            result = True in [ 'attachments' in chip_run for chip_run in chip_run_entries ]

        stage = thisRun['stage']
        testType = thisRun.get('testType')

        if not testType in resultIndex: 
            resultIndex.update({ testType: { 'run': [] } })

        count = {}
        #TODO
        #query = { 'resultId': str(thisRun['_id']) }
        #thisRunInLocal = userdb.localdb.find_one( query )
        #if thisRunInLocal:
        #    count = thisRunInLocal['count']
        #else:
        #    write_dat(str(thisRun['_id'])) 
        #    count = {}
        #    if DOROOT:
        #        root.uuid = str(session.get('uuid','localuser'))
        #        count = root.countPix( run.get('testType'), session['plotList'] )
        #    document = { 'resultId': str(thisRun['_id']),
        #                 'count': count }
        #    userdb.localdb.insert( document )
        #TODO

        resultIndex[testType]['run'].append({ '_id'      : str(thisRun['_id']),
                                              'runNumber': thisRun['runNumber'],
                                              'datetime' : set_time(thisRun['startTime']),
                                              'result'   : result,
                                              'chips'    : len(chips),
                                              'stage'    : stage,
                                              'rate'     : count.get('module',{}).get('rate','-'),
                                              'score'    : count.get('module',{}).get('score',None),
                                              'values'   : count.get('module',{}).get('parameters',{}),
                                              'summary'  : thisRun.get('display') })
    for scan in resultIndex:
        runInd = sorted(resultIndex[scan]['run'], key=lambda x:x['datetime'], reverse=True)
        resultIndex.update({ scan: { 'num': len(runInd),
                                     'run': runInd } })
        testIndex.append( scan )
    testIndex.sort()
    resultIndex.update({ "index": testIndex })
    return resultIndex

# make result plot in component page for the run
def fill_results():

    results = {}

    if session.get('runId'):
        query = { 'component': session['this'], 
                  'testRun'  : session['runId'] }
        thisComponentTestRun = yarrdb.componentTestRun.find_one(query)
        query = { '_id': ObjectId(session['runId']) }
        thisRun = yarrdb.testRun.find_one(query)

        plots = []
        data_entries = thisComponentTestRun.get('attachments', [])
        for data in data_entries:
            if data['contentType'] == 'pdf' or data['contentType'] == 'png':
                binary = base64.b64encode(fs.get(ObjectId(data['code'])).read()).decode()
                url = bin_to_image(data['contentType'], binary)
                plots.append({ 'code'    : data['code'],
                               'url'     : url,
                               'filename': data['title'] })
        # Change scheme
        config = {}
        if 'afterCfg' in thisComponentTestRun:
            query = { '_id': ObjectId(thisComponentTestRun['afterCfg']) }
            config_data = yarrdb.config.find_one( query )
            fs.get(ObjectId(config_data['data_id'])).read()
            config.update({ "filename" : config_data['filename'],
                            "code"     : config_data['data_id'] })

        query = { '_id': ObjectId(thisRun['user_id']) }
        user = yarrdb.user.find_one( query )
        results.update({ 'testType'    : thisRun['testType'],
                         'runNumber'   : thisRun['runNumber'],
                         'comments'    : list(thisRun['comments']),
                         'stage'       : thisRun['stage'],
                         'address'     : thisRun.get('address','null'),
                         'institution' : user['institution'],
                         'userIdentity': user['userName'],
                         'plots'       : plots,
                         'config'      : config}) 

    return results

# create dat file from dat data in attachments of run
def write_dat(runId):

    session['plotList'] = {}

    plot_dir = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/plot'
    clean_dir(plot_dir)

    dat_dir = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/dat'
    clean_dir(dat_dir)

    jsonFile = JSON_DIR + '/{}_parameter.json'.format(session.get('uuid','localuser'))
    if not os.path.isfile( jsonFile ):
        jsonFile_default = './scripts/json/parameter_default.json'
        with open(jsonFile_default, 'r') as f: jsonData_default = json.load(f)
        with open(jsonFile,         'w') as f: json.dump(jsonData_default, f, indent=4)
 
    query = { '_id': ObjectId(runId) }
    thisRun = yarrdb.testRun.find_one(query)

    chipIds = {}
    chipIdNums = []

    chips = []
    query = [{ 'parent': session['this'] }, { 'child': session['this'] }]
    child_entries = yarrdb.childParentRelation.find({'$or': query})
    for child in child_entries:
        chips.append({ 'component': child['child'] })
        query = { '_id': ObjectId(child['child']) }
        thisChip = yarrdb.component.find_one( query )
        chipIds.update({ child['child']: { 'chipId': str(thisChip['chipId']),
                                           'name':   thisChip['name'] }})
        chipIdNums.append( str(thisChip['chipId']) )

    query = { 'testRun': str(thisRun['_id']) }
    run_entries = yarrdb.componentTestRun.find(query)

    for run in run_entries:
        query = { '_id': ObjectId(run['testRun']) }
        chiprun = yarrdb.testRun.find_one(query)

        data_entries = chiprun.get('attachments')
        for data in data_entries:
            if data['contentType'] == 'dat':

                mapType = data['title']
                f = open( '{0}/{1}/dat/{2}_chipId{3}.dat'.format( TMP_DIR, session.get('uuid','localuser'), mapType, chipIds[run['component']]['chipId'] ), 'wb' )
                f.write(fs.get(ObjectId(data['code'])).read())
                f.close()
                session['plotList'].update({mapType: {'draw': True, 'chips': chipIdNums}})

# make plot using PyROOT
def make_plot(runId):
    query = { '_id': ObjectId(runId) }
    thisRun = yarrdb.testRun.find_one( query )

    if DOROOT:
        root.uuid = str(session.get('uuid','localuser'))

        if session.get('rootType'):
            mapType = session['mapType']

            if session['rootType'] == 'set': 
                root.setParameter(thisRun['testType'], mapType, session['plotList'])
                for mapType in session['plotList']: session['plotList'][mapType].update({'draw': True, 'parameter': {}})

            elif session['rootType'] == 'make':
                session['plotList'][mapType].update({'draw': True, 'parameter': session['parameter']})

        else:
            write_dat(runId)

        session['plotList'] = root.drawScan(thisRun['testType'], session['plotList'])

        session.pop('rootType', None)
        session.pop('mapType', None)
        session.pop('parameter', None)

def write_dat_for_component(componentId, runId):

    query = { 'testRun': runId, 'component': componentId }
    thisComponentTestRun = yarrdb.componentTestRun.find_one( query )
    if not thisComponentTestRun: return

    query = { '_id': ObjectId(componentId) }
    thisComponent = yarrdb.component.find_one( query )
    chipId = thisComponent['chipId']
    for data in thisComponentTestRun.get('attachments'):
        if data['contentType'] == 'dat':
            query = { '_id': ObjectId(data['code']) }
            filePath = '{0}/{1}/dat/{2}-{3}.dat'.format(TMP_DIR, session.get('uuid','localuser'), chipId, data['title'])
            f = open(filePath, 'wb')
            f.write(fs.get(ObjectId(data['code'])).read())
            f.close()
            if data['title'] in session['plotList']:
                session['plotList'][data['title']]['chipIds'].append( chipId )

def make_plot_for_run(componentId, runId):
    query = { '_id': ObjectId(runId) }
    thisRun = yarrdb.testRun.find_one( query )
    if session.get('rootType'):
        mapType = session['mapType']
        if session['rootType'] == 'set':
            root.setParameter( thisRun['testType'], mapType, session['plotList'] )
            for mapType in session['plotList']: session['plotList'][mapType].update({'draw': True, 'parameter': {}})
        elif session['rootType'] == 'make':
            session['plotList'][mapType].update({'draw': True, 'parameter': session['parameter']})
    else:
        dat_dir = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/dat'
        clean_dir(dat_dir)

        session['plotList'] = {}
        for mapType in thisRun.get('plots',[]):
            session['plotList'].update({mapType: {'draw': True, 'chipIds': []}})
        query = [{ 'parent': componentId }, { 'child': componentId }]
        child_entries = yarrdb.childParentRelation.find({'$or': query})
        for child in child_entries:
            write_dat_for_component( child['child'], runId )

    for mapType in thisRun.get('plots',[]):
        if not session['plotList'][mapType]['draw']: continue
        session['plotList'][mapType]['filled'] = False
        chipIds = session['plotList'][mapType]['chipIds']
        for chipId in chipIds:
            session['plotList'] = root.fillHisto(thisRun['testType'], mapType, int(chipId), session['plotList'])
        if session['plotList'][mapType]['filled']:
            root.outHisto(thisRun['testType'], mapType, session['plotList'])
        session['plotList'][mapType]['draw'] = False

    session.pop('rootType',  None)
    session.pop('mapType',   None)
    session.pop('parameter', None)

# list plot created by 'make_plot' using PyROOT
def fill_roots():

    roots = {}

    if not session.get('runId'): return roots

    if not DOROOT:
        roots.update({'rootsw': False})
        return roots

    root.uuid = str(session.get('uuid','localuser'))
    make_plot_for_run( session['this'], session['runId'] )
    query = { '_id': ObjectId(session['runId']) }
    thisRun = yarrdb.testRun.find_one(query)

    results = []
    for mapType in thisRun.get('plots',[]):
        if session['plotList'][mapType]['HistoType'] == 1: continue
        url = {} 
        for i in ['1', '2']:
            filename = TMP_DIR + '/' + str(session.get('uuid','localuser')) + '/plot/' + str(thisRun['testType']) + '_' + str(mapType) + '_{}.png'.format(i)
            if os.path.isfile(filename):
                binary_image = open(filename, 'rb')
                code_base64 = base64.b64encode(binary_image.read()).decode()
                binary_image.close()
                url.update({i: bin_to_image('png', code_base64)}) 
        results.append({ 'mapType' : mapType, 
                         'sortkey' : '{}0'.format(mapType), 
                         'runId'   : session['runId'],
                         'urlDist' : url.get('1'), 
                         'urlMap'  : url.get('2'), 
                         'setLog'  : session['plotList'][mapType]['parameter']['log'], 
                         'minValue': session['plotList'][mapType]['parameter']['min'],
                         'maxValue': session['plotList'][mapType]['parameter']['max'],
                         'binValue': session['plotList'][mapType]['parameter']['bin']})

    results = sorted(results, key=lambda x:int((re.search(r'[0-9]+',x['sortkey'])).group(0)), reverse=True)

    roots.update({ 'rootsw' : True,
                   'results': results})

    return roots
