#!/usr/bin/env python3
#coding:UTF-8
#################################
# Contacts: Arisa Kubota (akubota@hep.phys.titech.ac.jp)
# Project: Yarr
# Description: Viewer application
# Usage: python app.py --config conf.yml 
# Date: Feb 2019
################################
from configs import *

# module
import os
import hashlib
import datetime
import shutil
import uuid
import base64                          # Base64 encoding scheme
import gridfs                          # gridfs system 
import io
import sys
import yaml

from flask            import Flask, request, redirect, url_for, render_template, session, make_response, jsonify, send_file, send_from_directory
from flask_pymongo    import PyMongo
from pymongo          import MongoClient
from bson.objectid    import ObjectId 
from werkzeug         import secure_filename # for upload system
from PIL              import Image

sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) )

from scripts.src      import listset
from scripts.src      import static
from scripts.src.func import *

# Config python logging
# https://stackoverflow.com/questions/17743019/flask-logging-cannot-get-it-to-write-to-a-file
import logging, logging.config
logging.config.dictConfig(yaml.load(open('./configs/logging.yml')))

# Blue Prints
from controllers.callback   import callback_api
from controllers.component_dev   import component_dev_api


if os.path.isdir( TMP_DIR ): 
    shutil.rmtree( TMP_DIR )
os.mkdir( TMP_DIR )
_DIRS = [UPLOAD_DIR, STATIC_DIR, THUMBNAIL_DIR, JSON_DIR] 
for dir_ in _DIRS:
    os.mkdir( dir_ )
DAT_MIMETYPE = 'application/octet-stream'
JSON_MIMETYPE = 'application/json'
ZIP_MIMETYPE = 'application/zip'

# app 
app = Flask( __name__ )

# Regist Blue Prints
app.register_blueprint(callback_api)
app.register_blueprint(component_dev_api)

# Prefix
class PrefixMiddleware(object):
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):

        if environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            start_response('404', [('Content-Type', 'text/plain')])
            return ['This url does not belong to the app.'.encode()]

app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix='/localdb')
# static
app.register_blueprint(static.app)
# secret_key
app.config['SECRET_KEY'] = os.urandom(24)
#app.config['SECRET_KEY'] = 'key'

# MongoDB settings
if args.username:
    MONGO_URL = 'mongodb://' + args.username + ':' + args.password + '@' + args.host + ':' + str(args.port) 
else:
    MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
url = "mongodb://" + args.host + ":" + str(args.port)
print("Connecto to mongoDB server: " + url + "/" + args.db)
mongo     = PyMongo(app, uri=MONGO_URL+'/'+args.db)
fs = gridfs.GridFS(mongo.db)
dbv=args.version


# top page 
@app.route('/', methods=['GET'])
def show_toppage():

    if session.get( 'uuid' ):
        user_dir = TMP_DIR + '/' + str(session.get( 'uuid' ))
        if os.path.isdir( user_dir ): shutil.rmtree( user_dir )
    else:
        session['uuid'] = str( uuid.uuid4() ) 
    session['timezone'] = 0 #TODO

    makeDir()
    cleanDir( STATIC_DIR )
    session.pop( 'signup', None )

    return render_template( 'toppage.html' )

@app.route('/module', methods=['GET'])
def show_modules_and_chips():

    query = { 'componentType': 'Module', 'dbVersion': dbv }
    module_entries = mongo.db.component.find( query )
    module_ids = []
    for module in module_entries:
        module_ids.append(str(module['_id']))

    modules = {}
    for module_id in module_ids:
        query = { '_id': ObjectId(module_id) }
        this_module = mongo.db.component.find_one( query )
        chip_type = this_module['chipType']

        query = { 'parent': module_id }
        child_entries = mongo.db.childParentRelation.find( query )
        chip_ids = []
        for child in child_entries:
            chip_ids.append(child['child'])

        # grade module
        #score = grade_module(str(this_module['_id']))

        chips = []
        for chip_id in chip_ids:
            query = { '_id': ObjectId(chip_id) }
            this_chip = mongo.db.component.find_one( query )
            chips.append({ 
                '_id'          : chip_id,
                'serialNumber' : this_chip['serialNumber'],
                'componentType': this_chip['componentType'],
                'chipId'       : this_chip.get('chipId',-1),
                'datetime'     : setTime(this_chip['sys']['cts']),
                'stage'        : None,
                'grade'        : {} 
            }) 

        if not chip_type in modules:
            modules.update({ chip_type: { 'modules': [], 'num': '' } })

        modules[chip_type]['modules'].append({ '_id'         : module_id,
                                              'serialNumber' : this_module['serialNumber'],
                                              'componentType': 'Module',
                                              'chips'        : chips,
                                              'children'    : len(chips),
                                              'datetime'    : setTime(this_module['sys']['cts']),
                                              'grade'       : {},
                                              'stage'       : None })

    for chip_type in modules:
        modules[chip_type].update({ 'num': len(modules[chip_type]['modules']) })
        module = sorted( modules[chip_type]['modules'], key=lambda x:x['serialNumber'], reverse=True)
        modules[chip_type]['modules'] = module

    return render_template( 'module.html', modules=modules )

@app.route('/development', methods=['GET'])
def show_modules_and_chips_develop():

    if session.get( 'uuid' ):
        user_dir = TMP_DIR + '/' + str(session.get( 'uuid' ))
        if os.path.isdir( user_dir ): shutil.rmtree( user_dir )
    else:
        session['uuid'] = str( uuid.uuid4() ) 

    makeDir()
    cleanDir( STATIC_DIR )
    session.pop( 'signup', None )

    query = { 'componentType': 'Module' }
    module_entries = mongo.db.component.find( query )
    modules = {}

    for this_module in module_entries:
        query = { 'parent': str(this_module['_id']) }
        child_entries = mongo.db.childParentRelation.find( query )
        chips = []
        chip_type = this_module['chipType']

        # grade module
        score  = grade_module(str(this_module['_id'])) 

        for child in child_entries:
            query = { '_id': ObjectId(child['child']) }
            this_chip = mongo.db.component.find_one( query )
            if 'chipId' in this_chip['serialNumber']:
                chipId = this_chip['serialNumber'].split('chipId')[1]
            else:
                chipId = '1' 
            chips.append({ 
                '_id'          : str(this_chip['_id']),
                'serialNumber' : this_chip['serialNumber'],
                'componentType': this_chip['componentType'],
                'chipId'       : this_chip.get('chipId',-1),
                'datetime'     : setTime(this_chip['sys']['cts']),
                'grade'        : score.get(chipId,{}) 
            }) 

        if not chip_type in modules:
            modules.update({ chip_type: { 'modules': [], 'num': '' } })


        modules[chip_type]['modules'].append({ 
            '_id'         : str(this_module['_id']),
            'serialNumber': this_module['serialNumber'],
            'chips'       : chips,
            'datetime'    : setTime(this_module['sys']['cts']),
            'grade'       : score['module'],
            'stage'       : score['stage'] 
        })

    for chip_type in modules:
        modules[chip_type].update({ 'num': len(modules[chip_type]['modules']) })
        module = sorted( modules[chip_type]['modules'], key=lambda x:x['serialNumber'], reverse=True)
        modules[chip_type]['modules'] = module

    return render_template( 'module.html', modules=modules )


# component page 
@app.route('/component', methods=['GET', 'POST'])
def show_component():

    makeDir()

    session['this']  = request.args.get( 'id' )
    session['code']  = request.args.get( 'code', '' )
    session['runId'] = request.args.get( 'runId' )

    # this component
    query = { '_id': ObjectId(session['this']) }
    this_cmp = mongo.db.component.find_one( query )
    cmp_type = this_cmp['componentType']

    # chips and parent
    if cmp_type == 'Module':
        parent_id = session['this']
    else:
        query = { 'child': session['this'] }
        parent_id = mongo.db.childParentRelation.find_one( query )['parent']

    # this module
    query = { '_id': ObjectId(parent_id) }
    this_module = mongo.db.component.find_one( query )

    # chips of module
    query = { 'parent': parent_id }
    child_entries = mongo.db.childParentRelation.find( query )
    chip_ids = []
    for child in child_entries:
        chip_ids.append(child['child'])

    # get comments for this module
    if cmp_type == 'Module':
        parent_id = session['this']
    else:
        query = { 'child': session['this'] }
        parent_id = mongo.db.childParentRelation.find_one( query )['parent']

    query = { 'parent': parent_id }
    child_entries = mongo.db.childParentRelation.find( query )
    queryids = [{'componentId':parent_id}]
    for child in child_entries:
        queryids.append({'componentId':child['child']})
 
    comments=[]
    comment_entries = mongo.db.comments.find({'$or':queryids})
    for comment in comment_entries:
        comments.append(comment)
  
    # set chip and module information
    component_chips = []
    for chip_id in chip_ids:
        query = { '_id': ObjectId(chip_id) }
        this_chip = mongo.db.component.find_one( query )
        component_chips.append({ 
            '_id'         : chip_id,
            'chipId'      : this_chip.get('chipId',-1),
            'serialNumber': this_chip['serialNumber'] 
        })

    module = { 
        '_id'         : parent_id,
        'serialNumber': this_module['serialNumber'] 
    }
    
    # set photos
    photo_display = []
    photo_index = []
    photos = {}
    #photo_display = setPhotoDisplay( this_cmp )            #TODO
    #photo_index   = setPhotoIndex( this_cmp )              #TODO
    #photos       = setPhotos( this_cmp, session['code'] ) #TODO

    # set summary 
    summary = setSummary()

    # set results
    result_index  = setResultIndex() 
    results      = setResults()     
    roots        = setRoots()    

    component = { 
        '_id'         : session['this'],
        'serialNumber': this_cmp['serialNumber'],
        'module'      : module,
        'chips'       : component_chips,
        'unit'        : this_cmp['componentType'], 
        'chipType'    : this_cmp['chipType'],
        'comments_for_component': comments, 
        'photoDisplay': photo_display,
        'photoIndex'  : photo_index,
        'photos'      : photos,
        'resultIndex' : result_index,
        'results'     : results,
        'roots'       : roots,
        'summary'     : summary,
        'dummy'       : False
    }

    return render_template( 'component.html', component=component )

# test run page without component
@app.route('/scan', methods=['GET', 'POST'])
def show_test():
    
    max_num = 10
    sort_cnt = int(request.args.get('p',0))

    query = { 'dbVersion': dbv }
    run_entries = mongo.db.testRun.find(query).sort([( '$natural', -1 )] )
    run_ids = []
    for i, run in enumerate(run_entries):
        if i//max_num<sort_cnt: continue
        elif i//max_num==sort_cnt: run_ids.append(str(run['_id']))
        else: break
    cnt = []
    for i in range((run_entries.count()//max_num)+1):
        if sort_cnt-(max_num/2)<i:
            cnt.append(i)
        if len(cnt)==max_num:
            break

    scans = {
        'run':[],
        'total': run_entries.count(),
        'cnt': cnt,
        'now_cnt': sort_cnt,
        'max_cnt': (run_entries.count()//max_num)
    }

    for run_id in run_ids:
        query = { '_id': ObjectId(run_id) }
        this_run = mongo.db.testRun.find_one (query)
        query = { '_id': ObjectId(this_run['user_id']) }
        this_user = mongo.db.user.find_one(query)
        query = { '_id': ObjectId(this_run['address']) }
        this_site = mongo.db.institution.find_one(query)
        cmp_id = ''
        if not this_run['dummy']:
            query = { 'serialNumber': this_run['serialNumber'] }
            this_cmp = mongo.db.component.find_one(query)
            cmp_id = str(this_cmp['_id'])
        else:
            cmp_id = this_run['serialNumber']
        if 'DUMMY' in this_run['serialNumber']:
            serial_number = '---'
        else:
            serial_number = this_run['serialNumber']
        run_data = {
            '_id':          run_id,
            'serialNumber': serial_number,
            'datetime':     this_run['startTime'],
            'testType':     this_run['testType'],
            'stage':        this_run['stage'],
            'runNumber':    this_run['runNumber'],
            'dummy':        this_run['dummy'],
            'plots':        (this_run['plots']!=[]),
            'component':    cmp_id,
            'user':         this_user['userName'].replace('_', ' '),
            'site':         this_site['institution'].replace('_', ' ')
        }
        scans['run'].append(run_data)

    return render_template( 'scan.html', scans=scans )

# component page 
@app.route('/dummy', methods=['GET', 'POST'])
def show_dummy():

    makeDir()

    serial_number = request.args.get( 'id' )
    session['this'] = serial_number
    session['runId'] = request.args.get( 'runId' )
    query = { '_id': ObjectId(session['runId']) }
    this_run = mongo.db.testRun.find_one(query)

    # this component
    if session['this']==this_run['serialNumber']: cmp_type = 'Module'
    else: cmp_type = 'Front-end Chip'

    # chips and parent
    if cmp_type == 'Module': parent_id = session['this']
    else: parent_id = this_run['serialNumber']

    # this module
    module = { 
        '_id': parent_id,
        'serialNumber': 'DummyModule' 
    }

    # chips of module
    component_chips = []
    query = { 
        'testRun': session['runId'], 
        'component':{'$ne': this_run['serialNumber']} 
    }
    ctr_entries = mongo.db.componentTestRun.find(query)
    for ctr_entry in ctr_entries:
        component_chips.append({
            '_id': ctr_entry['component'],
            'geomId': ctr_entry['geomId'],
            'serialNumber': 'DummyChip{}'.format(ctr_entry['geomId'])
        })

    # set photos
    photo_display = []
    photo_index = []
    photos = {}
 
    # set results
    result_index = {}
    results      = setResults()
    roots        = setRoots()    

    component = { 
        '_id'         : session['this'],
        #'serialNumber': this_run['serialNumber'],
        'serialNumber': '---',
        'module'      : module,
        'chips'       : component_chips,
        'unit'        : cmp_type,
        'chipType'    : '', #TODO
        'photoDisplay': photo_display,
        'photoIndex'  : photo_index,
        'photos'      : photos,
        'resultIndex' : result_index,
        'results'     : results,
        'roots'       : roots,
        'summary'     : {},
        'dummy'       : True
    }

    return render_template( 'component.html', component=component )

# make histogram 
@app.route('/makehisto', methods=['GET','POST'])
def makehisto():
    # get from form
    session['rootType']  = request.form.get( 'root' )
    session['mapType']   = request.form.get( 'mapType' )
    session['parameter'] = { 'min': request.form.get( 'min' ), 
                             'max': request.form.get( 'max' ), 
                             'bin': request.form.get( 'bin' ), 
                             'log': request.form.get( 'log', False) }
    # get from args
    componentId = request.args.get( 'id' )
    runoid       = request.args.get( 'runId' )

    return redirect( url_for('show_component', id=componentId, runId=runoid) )

# select page
@app.route('/select_summary', methods=['GET','POST'])
def select_summary():

    session.pop( 'testType', None )
    session.pop( 'runId',    None )
    session.pop( 'code',     None )
    session.pop( 'plotList', None )
   
    # get from args
    session['this']  = request.args.get( 'id' ) 
    # this component
    query = { '_id': ObjectId(session['this']) }

    if not mongo.db.component.find_one( query )['componentType'] == 'Module':
        query = { 'child': session['this'] }
        session['this'] = mongo.db.childParentRelation.find_one( query )['parent']

    query = { '_id': ObjectId(session['this']) }
    this_cmp = mongo.db.component.find_one( query )

    unit = 'module'

    # get from form
    if request.form.get('step'):
        session['step'] = int(request.form.get('step'))

    if session.get( 'step' ) == 4:
        return redirect( url_for('add_summary', id=request.args.get( 'id' )) )

    if not request.form.get( 'stage' ) == session.get( 'stage' ) or not session.get( 'stage' ):
        session['summaryList'] = { 'after': {},
                                   'before': {} }
        session['step'] = 1

    session['stage'] = request.form.get( 'stage' )

    if request.form.get('testType'):
        if session['step'] == 1:
            session['summaryList']['after' ][request.form.get('testType')].update({ 'runId': request.form.get('runId') })
            session['testType'] = request.form.get('testType')
        else:
            session['summaryList']['after' ][request.form.get('testType')].update({ 'comment': str(request.form.get('comment')) })

    # chips and parent
    chips = []
    query = [{ 'parent': session['this'] },{ 'child': session['this'] }]
    child_entries = mongo.db.childParentRelation.find({ '$or': query })
    for child in child_entries:
        chips.append({ 'component': child['child'] })
        parent_id = child['parent']

    # this module
    query = { '_id': ObjectId(parent_id) }
    this_module = mongo.db.component.find_one( query )

    # chips of module
    query = { 'parent': parent_id }
    child_entries = mongo.db.childParentRelation.find( query )
    chip_ids = []
    for child in child_entries:
        chip_ids.append(child['child'])

    # set chip and module information
    component = {}
    component_chips = []
    for chip_id in chip_ids:
        query = { '_id': ObjectId(chip_id) }
        this_chip = mongo.db.component.find_one( query )
        component['componentType'] = this_chip['componentType']
        component_chips.append({ '_id'        : chip_id,
                                 'serialNumber': this_chip['serialNumber'] })
    module = { '_id'         : parent_id,
               'serialNumber': this_module['serialNumber'] }

    query = { '$or': chips }
    run_entries = mongo.db.componentTestRun.find( query )
    stages = []
    for run in run_entries:
        stages.append( run.get('stage') )
    stages = list(set(stages))

    # set summary 
    summary = setSummaryTest( )

    # set result index 
    result_index = setResultIndex()

    component.update({ '_id'         : session['this'],
                       'serialNumber': this_cmp['serialNumber'],
                       'module'      : module,
                       'chips'       : component_chips,
                       'unit'        : unit,
                       'summary'     : summary,
                       'stages'      : stages,
                       'step'        : session['step'],
                       'comments'    : listset.summary_comment,
                       'resultIndex' : result_index,
                       'stage'       : session['stage'] })

    return render_template( 'add_summary.html', component=component )

# write summary into db 
@app.route('/add_summary', methods=['GET', 'POST'])
def add_summary():

    componentId = request.args.get( 'id' )
    query = { '_id': ObjectId( componentId ) }
    this_cmp = mongo.db.component.find_one( query )

    for scan in session['summaryList']['before']:

        if session['summaryList']['before'][scan]['runId'] == session['summaryList']['after'][scan]['runId']: continue

        if session['summaryList']['after'][scan]['runId']:

            # make plot 
            makePlot( session['summaryList']['after'][scan]['runId'] )

            # insert testRun and componentTestRun
            query = { 'testRun': session['summaryList']['after'][scan]['runId'] }
            this_ctr = mongo.db.componentTestRun.find_one( query ) 

            if this_ctr['component'] == componentId: 
                runoid = session['summaryList']['after'][scan]['runId']  

            else:
                thistime = datetime.datetime.utcnow()

                moduleComponentTestRun = this_ctr
                query = { '_id': ObjectId(session['summaryList']['after'][scan]['runId']) }
                moduleTestRun = mongo.db.testRun.find_one( query )
                moduleComponentTestRun.pop( '_id', None )
                moduleTestRun.pop( '_id', None )

                moduleTestRun.update({ 'attachments': [] })
                moduleTestRun.update({ 'sys': { 'rev': 0,
                                                 'cts': thistime,
                                                 'mts': thistime }})
                runoid = str(mongo.db.testRun.insert( moduleTestRun ))
                moduleComponentTestRun.update({ 'component': componentId,
                                                'testRun' : runoid,
                                                'sys'       : { 'rev': 0,
                                                                  'cts': thistime,
                                                                  'mts': thistime }})
                mongo.db.componentTestRun.insert( moduleComponentTestRun )

            # add attachments into module TestRun
            query = { 'component': componentId, 'testRun': runoid }
            this_ctr = mongo.db.componentTestRun.find_one( query )
            query = { '_id': ObjectId(runoid) }
            thisRun = mongo.db.testRun.find_one( query )

            for mapType in session.get('plotList'):
                if session['plotList'][mapType]['HistoType'] == 1: continue
                url = {} 
                path = {}
                datadict = { '1': '_Dist', '2': '' }
                for i in datadict:
                    filename = '{0}_{1}{2}'.format( this_cmp['serialNumber'], mapType, datadict[i] )
                    for attachment in thisRun['attachments']:
                        if filename == attachment.get('filename'):
                            fs.delete( ObjectId(attachment.get('code')) )
                            mongo.db.testRun.update( query, { '$pull': { 'attachments': { 'code': attachment.get('code') }}}) 


                    filepath = '{0}/{1}/plot/{2}_{3}_{4}.png'.format(TMP_DIR, str(session.get('uuid')), str(thisRun['testType']), str(mapType), i)
                    if os.path.isfile( filepath ):
                        binary_image = open( filepath, 'rb' )
                        image = fs.put( binary_image.read(), filename='{}.png'.format(filename) )
                        binary_image.close()
                        mongo.db.testRun.update( query, { '$push': { 'attachments': { 'code'      : str(image),
                                                                                        'dateTime'  : datetime.datetime.utcnow(),
                                                                                        'title'     : 'title',
                                                                                        'description': 'describe',
                                                                                        'contentType': 'png',
                                                                                        'filename'  : filename }}}) 
        # remove 'summary: True' in current summary run
        if session['summaryList']['before'][scan]['runId']:
            query = { '_id': ObjectId(session['summaryList']['before'][scan]['runId']) }
            thisRun = mongo.db.testRun.find_one( query )

            keys = [ 'runNumber', 'institution', 'userIdentity', 'testType' ]
            query_id = dict( [ (key, thisRun[key]) for key in keys ] )
            mongo.db.testRun.update( query_id, { '$set': { 'summary': False }}, multi=True )

            mongo.db.testRun.update( query_id, { '$push': { 'comments': { 'userIdentity': session['userIdentity'],
                                                                            'userid'     : session['uuid'],
                                                                            'comment'    : session['summaryList']['after'][scan]['comment'], 
                                                                            'after'      : session['summaryList']['after'][scan]['runId'],
                                                                            'datetime'   : datetime.datetime.utcnow(), 
                                                                            'institution': session['institution'],
                                                                            'description': 'add_summary' }}}, multi=True )
            updateData( 'testRun', query_id ) 

        query = { 'component': componentId, 'stage': session['stage'], 'testType': scan }
        entries = mongo.db.componentTestRun.find( query )
        run_ids = []
        for entry in entries:
            run_ids.append(entry['testRun'])
        for run_id in run_ids:
            query = { '_id': ObjectId(run_id)}
            thisRun = mongo.db.testRun.find_one( query )
            keys = [ 'runNumber', 'institution', 'userIdentity', 'testType' ]
            query_id = dict( [ (key, thisRun[key]) for key in keys ] )
            run_entries = mongo.db.testRun.find( query_id )
            for run in run_entries:
                if run.get( 'summary' ):
                    query = { '_id': run['_id'] }
                    mongo.db.testRun.update( query, { '$set': { 'summary': False }} )
                    updateData( 'testRun', query )

        # add 'summary: True' in selected run
        if session['summaryList']['after'][scan]['runId']:
            query = { '_id': ObjectId(session['summaryList']['after'][scan]['runId']) }
            thisRun = mongo.db.testRun.find_one( query )

            keys = [ 'runNumber', 'institution', 'userIdentity', 'testType' ]
            query_id = dict( [ (key, thisRun[key]) for key in keys ] )

            mongo.db.testRun.update( query_id, { '$set': { 'summary': True }}, multi=True )
            updateData( 'testRun', query_id ) 

    # pop session
    session.pop( 'testType',    None )
    session.pop( 'runId',       None )
    session.pop( 'summaryList', None )
    session.pop( 'stage',       None )
    session.pop( 'step',        None )
    cleanDir( THUMBNAIL_DIR )

    return redirect( url_for('show_component', id=componentId) )

# show summary plot 
@app.route('/show_summary', methods=['GET'])
def show_summary():

    # get from args
    code = request.args.get('code')
    scan = request.args.get('scan')
    stage = request.args.get('stage')

    query = { '_id': ObjectId(code) }
    data = mongo.db.fs.files.find_one( query )
    if not 'png' in data['filename']: 
        filePath = '{0}/{1}/{2}_{3}_{4}.png'.format( THUMBNAIL_DIR, session.get( 'uuid' ), stage, scan, data['filename'] )
    else:
        filePath = '{0}/{1}/{2}_{3}_{4}'.format( THUMBNAIL_DIR, session.get( 'uuid' ), stage, scan, data['filename'] )

    thum_dir = '{0}/{1}'.format( THUMBNAIL_DIR, session.get( 'uuid' ) )
    cleanDir( thum_dir )
    
    binary = fs.get(ObjectId(code)).read()
    image_bin = io.BytesIO( binary )
    image = Image.open( image_bin )
    image.save( filePath )
    if not 'png' in data['filename']: 
        url = url_for( 'thumbnail.static', filename='{0}/{1}_{2}_{3}.png'.format( session.get( 'uuid' ), stage, scan, data['filename'] ))
    else:
        url = url_for( 'thumbnail.static', filename='{0}/{1}_{2}_{3}'.format( session.get( 'uuid' ), stage, scan, data['filename'] ))
 
    return redirect( url )

# show summary plot ( in add function ) 
@app.route('/show_summary_selected', methods=['GET'])
def show_summary_selected():
    # get from args
    runoid   = request.args.get( 'runId' )
    histo   = request.args.get( 'histo' )
    mapType = request.args.get( 'mapType' )

    query = { '_id': ObjectId(runoid) }
    thisRun = mongo.db.testRun.find_one( query )

    makePlot( runoid )

    url = ''
    filename = TMP_DIR + '/' + str(session.get('uuid')) + '/plot/' + str(thisRun['testType']) + '_' + str(mapType) + '_{}.png'.format(histo)
    if os.path.isfile( filename ):
        binary_image = open( filename, 'rb' )
        code_base64 = base64.b64encode(binary_image.read()).decode()
        binary_image.close()
        url = bin2image( 'png', code_base64 )  
 
    return redirect( url )

# download config file 
@app.route('/download_config', methods=['GET'])
def download_config() :
    
    # get code of config file
    code = request.args.get( 'code' )
    json_data = jsonify( json.loads( fs.get( ObjectId(code)).read().decode('ascii') ) )
    response = make_response( json_data )

    return response

@app.route('/config_downloader', methods=['GET'])
def config_downloader() : 
    configType = request.args.get( 'configType' )
    ModuleName = request.args.get( 'ModuleName' )
    downloadFileName =  str(ModuleName)+'_'+str(configType) + '.zip'
    downloadFile = writeConfig(ModuleName,configType)
    return send_file(downloadFile, as_attachment = True, attachment_filename = downloadFileName, mimetype = ZIP_MIMETYPE)

@app.route('/data_downloader', methods=['GET'])
def data_downloader() : 
    mapType = request.args.get( 'mapType' )
    ModuleName = request.args.get( 'ModuleName' )
    downloadFileName = str(ModuleName) + '_' + str(mapType) + '.zip'
    downloadFile = getData(ModuleName, mapType)    
    return send_file(downloadFile, as_attachment = True, attachment_filename = downloadFileName, mimetype = ZIP_MIMETYPE)

# tag method
@app.route('/tag', methods=['GET'])
def tag():
    query = { '_id': ObjectId(session.get('tagid')) }
    collection = str(session.get('collection'))

    data_entries = mongo.db[collection].find_one( query )['attachments']
    for data in data_entries:
        if data['code'] == request.args.get( 'code' ):
            if session.get('tag') == 'tag':
                 mongo.db[collection].update( query, { '$set': { 'attachments.{}.display'.format( data_entries.index(data) ): True }})
                 updateData( collection, query )
            elif session.get('tag') == 'untag':
                 mongo.db[collection].update( query, { '$unset': { 'attachments.{}.display'.format( data_entries.index(data) ): True }})
                 mongo.db[collection].update( query, { '$set' : { 'attachments.{}.description'.format( data_entries.index(data) ): '' }})
                 updateData( collection, query )
            else:
                 print('can\'t get tag session')

    forUrl = 'show_component'

    session.pop('collection', None)
    session.pop('tagid',      None)
    session.pop('tag',        None)

    return redirect( url_for(forUrl, id=request.args.get( 'id' )) )

@app.route('/tag_image', methods=['GET','POST'])
def tag_image():
    session['tagid'] = request.form.get( 'id' )
    session['collection'] = 'component'
    session['tag'] = str(request.form.get( 'tag' ))

    return redirect( url_for('tag', id=request.form.get( 'id' ), code=request.form.get( 'code' )) )

@app.route('/tag_result', methods=['GET','POST'])
def tag_result():
    #if session['component'] == 'module':
    #    session['tagid'] = request.form.get('id')
    #    session['collection'] = 'component'
    #if session['component'] == 'chip':
    #    session['tagid'] = request.form.get('runId')
    #    session['collection'] = 'testRun'
    session['tag'] = str(request.form.get('tag'))

    return redirect( url_for('tag', id=request.form.get( 'id' ), code=request.form.get('code')) )

# add attachment 
@app.route('/add_attachment_result', methods=['GET','POST'])
def add_attachment_result():
    fileResult = request.form.get( 'path' ) 
    binary_image = open( fileResult, 'rb' )
    runNumber = fileResult.rsplit( '/', 4 )[4].rsplit( '_', 2 )[0]
    mapType = fileResult.rsplit( '/', 4 )[4].rsplit( '_', 2 )[1]
    testType = fileResult.rsplit( '/', 4 )[3]
    filename = '{0}_{1}_{2}.png'.format( runNumber, testType, mapType )
    image = fs.put( binary_image.read(), filename=filename )
    binary_image.close()
    
    chips = []
    query = { 'parent': request.form.get( 'id' ) } 
    child_entries = mongo.db.childParentRelation.find( query )
    for child in child_entries:
        chips.append( { 'component': child['child'] } )
    query = { '$or': chips, 'runNumber': int( runNumber ) }
    query = { '_id': ObjectId(mongo.db.componentTestRun.find_one( query )['testRun']) }
    thisRun = mongo.db.testRun.find_one( query )
    this_ctr = mongo.db.componentTestRun.find_one({ 'testRun': str(thisRun['_id']) })
    env_dict = setEnv( this_ctr )
 
    query = { '_id': image }
    date = mongo.db.fs.files.find_one( query )['uploadDate']
    query = { '_id': ObjectId(request.form.get('id')) }
    mongo.db.component.update( query, { '$push': { 'attachments': { 'code'      : str(image),
                                                                      'dateTime'  : date,
                                                                      'title'     : '',
                                                                      'description': '',
                                                                      'display'   : True,
                                                                      'imageType' : 'result',
                                                                      'contentType': filename.rsplit( '.', 1 )[1],
                                                                      'filename'  : filename,
                                                                      'environment': env_dict }}})
    updateData( 'component', query )

    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )


@app.route('/edit_description', methods=['GET','POST'])
def edit_description():

    col = request.form.get('collection')
    if col == 'testRun': 
        query = { '_id': ObjectId(request.form.get('runId')) }
    elif col == 'component':
        query = { '_id': ObjectId(request.form.get('id')) }
    else:
        return render_template( 'error.html', txt='something error' )
    data_entries = mongo.db[ str(col) ].find_one( query )['attachments']
    for data in data_entries:
        if data['code'] == request.form.get( 'code' ):
            if 'display' in data:
                mongo.db[ str(col) ].update( query, { '$set': { 'attachments.{}.description'.format( data_entries.index(data) ): request.form.get('description') }})

                updateData( str(col), query )

    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

#@app.route('/edit_comment_for_test', methods=['GET','POST'])
#def edit_comment_for_test():
#
#    query = { '_id': ObjectId(request.form.get( 'id' ))}
#    this_cmp = mongo.db.component.find_one( query )
#
#    if this_cmp['componentType'] == 'Module':
#        query = { 'parent': request.form.get('id') }
#    else:
#        query = { 'child': request.form.get('id') }
#        parentoid = mongo.db.childParentRelation.find_one( query )['parent']
#        query = { 'parent': parentoid }
#
#    child_entries = mongo.db.childParentRelation.find( query )
#    component_chips = []
#    for child in child_entries:
#        component_chips.append({ 'component': child['child'] })
#
#    runoid = request.args.get('runId')
#    query = { '_id': ObjectId(runoid) }
#    mongo.db.testRun.update( 
#        query, { 
#            '$push': { 
#                'comments': { 
#                    'comment':request.form.get('text').replace('\r\n','<br>'),
#                    'name'  :request.form.get('text2'),
#                    'institution'  :request.form.get('text3'),
#                    'datetime':datetime.datetime.utcnow() 
#                } 
#            }
#        } 
#    )
#    updateData( 'testRun', query )
#    forUrl = 'show_component'
#
#    return redirect( url_for(forUrl, id=request.args.get( 'id' ), runId=request.args.get( 'runId' ) ))

@app.route('/edit_comment_for_test', methods=['GET','POST'])
def edit_comment_for_test():
    
    # this component
    query = { '_id': ObjectId(session['runId']) }
    this_test = mongo.db.testRun.find_one( query )
    if not this_test['dummy']:
        query = { '_id': ObjectId(session['this']) }
        this_cmp = mongo.db.component.find_one( query )
        cmp_type = this_cmp['serialNumber']
        componentId = request.args.get( 'id' )
    else:
        cmp_type = -1
        componentId = -1

    mongo.db.comments.insert( 
    { 
        'componentId': componentId,
        'runId': request.args.get( 'runId' ),
        'comment':request.form.get('text').replace('\r\n','<br>'),
        'componentType':cmp_type,
        'name'  :request.form.get('text2'),
        'institution'  :request.form.get('text3'),
        'datetime':datetime.datetime.utcnow() 
    } 
    )

    if not this_test['dummy']:
        forUrl = 'show_component'
    else:
        forUrl = 'show_dummy'

    return redirect( url_for(forUrl, id=request.args.get( 'id' ), runId=request.args.get( 'runId' ) ))


#@app.route('/edit_comment_for_component', methods=['GET','POST'])
#def edit_comment_for_component():
#
#    query = { '_id': ObjectId(request.form.get( 'id' ))}
#
#    mongo.db.component.update( 
#        query, { 
#            '$push': { 
#                'comments': { 
#                    'comment':request.form.get('text').replace('\r\n','<br>'),
#                    'name'  :request.form.get('text2'),
#                    'institution'  :request.form.get('text3'),
#                    'datetime':datetime.datetime.utcnow() 
#                } 
#            }
#        }
#    )
#    updateData( 'component', query )
# 
#    forUrl = 'show_component'
#
#    return redirect( url_for(forUrl, id=request.args.get( 'id' ), runId=request.args.get( 'runId' ) ))

@app.route('/edit_comment_for_component', methods=['GET','POST'])
def edit_comment_for_component():
    
    # this component
    query = { '_id': ObjectId(session['this']) }
    this_cmp = mongo.db.component.find_one( query )
    cmp_type = this_cmp['serialNumber']

    mongo.db.comments.insert( 
        {
        'componentId': request.form.get( 'id' ),
        'runId': -1,
        'comment':request.form.get('text').replace('\r\n','<br>'),
        'componentType':cmp_type,
        'name'  :request.form.get('text2'),
        'institution'  :request.form.get('text3'),
        'datetime':datetime.datetime.utcnow() 
        } 
    )
 
    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.args.get( 'id' ), runId=request.args.get( 'runId' ) ))


@app.route('/remove_comment', methods=['GET','POST'])
def remove_comment():

    query = { '_id': ObjectId(request.form.get( 'id' ))}
    this_cmp = mongo.db.component.find_one( query )

    if this_cmp['componentType'] == 'Module':
        query = { 'parent': request.form.get('id') }
    else:
        query = { 'child': request.form.get('id') }
        parentoid = mongo.db.childParentRelation.find_one( query )['parent']
        query = { 'parent': parentoid }

    child_entries = mongo.db.childParentRelation.find( query )
    component_chips = []
    for child in child_entries:
        component_chips.append({ 'component': child['child'] })

    query = { '$or': component_chips, 'runNumber': int(request.form.get( 'runNumber' )) }

    run_entries = mongo.db.componentTestRun.find( query )
    for run in run_entries:
        query = { '_id': ObjectId(run['testRun']) }
        mongo.db.testRun.update( query, { '$pull': { 'comments': { 'user': request.form.get( 'user' ) }}} )
        updateData( 'testRun', query )

    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), runNumber=request.form.get( 'runNumber' )) )

@app.route('/add_attachment', methods=['GET','POST'])
def add_attachment():

    file = request.files.get( 'file' )
    if file and allowed_file( file.filename ):
        filename = secure_filename( file.filename )
        if not os.path.isdir( UPLOAD_DIR ):
            os.mkdir( UPLOAD_DIR )
        file.save( os.path.join(UPLOAD_DIR, filename) )

        fileUp = '{0}/{1}'.format( UPLOAD_DIR, filename )
        binary_image = open( fileUp, 'rb' )
        description = request.form.get( 'description' )
        stage = request.form.get( 'stage' )
        image = fs.put( binary_image.read(), filename=filename )
        binary_image.close()
        
        query = { '_id': image }
        date = mongo.db.fs.files.find_one( query )['uploadDate']
        query = { '_id': ObjectId(request.form.get('id')) }
        mongo.db.component.update( query, { '$push': { 'attachments': { 'code'      : str(image),
                                                                          'dateTime'  : date,
                                                                          'title'     : 'title',
                                                                          'description': description,
                                                                          'imageType' : 'image',
                                                                          'stage'     : stage,
                                                                          'photoNumber': countPhotoNum(),
                                                                          'contentType': filename.rsplit( '.', 1 )[1],
                                                                          'filename'  : filename }}})
        updateData( 'component', query )

    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/remove_attachment',methods=['GET','POST'])
def remove_attachment():
    code = request.form.get( 'code' )
    
    fs.delete( ObjectId(code) )
    query = { '_id': ObjectId(request.form.get('id')) }
    mongo.db.component.update( query, { '$pull': { 'attachments': { 'code': code }}}) 
    updateData( 'component', query )

    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get('id')) )

@app.route('/login',methods=['POST'])
def login():

    query = { 'userName': request.form['username'] }
    userName = mongo.db.user.find_one( query )
    try:
        if hashlib.md5( request.form['password'].encode('utf-8') ).hexdigest() == userName['passWord']:
            session['logged_in'] = True
            session['user_id'] = str(userName['_id'])
            session['user_name'] = userName['userName']
            session['institution'] = userName['institution']
            session['read'] = userName['authority']%2
            session['write'] = int(userName['authority']/2)%2
            session['edit'] = int(userName['authority']/4)%2
        else:
            txt = 'not match password'
            return render_template( 'error.html', txt=txt )
    except:
        txt = 'not found user'
        return render_template( 'error.html', txt=txt )
    return redirect( url_for('show_modules_and_chips') )

@app.route('/logout',methods=['GET','POST'])
def logout():
    session['logged_in'] = False
    session['user_id'] = ''
    session['user_name'] = ''
    session['institution'] = '' 
    session['read'] = 1
    session['write'] = 0
    session['edit'] = 0

    return redirect( url_for('show_modules_and_chips') )

@app.route('/signup',methods=['GET','POST'])
def signup():
    stage = request.form.get('stage', 'input')
    if session['signup']:
        userinfo = request.form.getlist('userinfo')
        if not userinfo[5] == userinfo[6]:
            text = 'Please make sure your passwords match'
            stage = 'input'
            return render_template( 'signup.html', userInfo=userinfo, passtext=text, stage=stage )
        if mongo.db.user.find({ 'userName': userinfo[0] }).count() == 1 or mongo.db.request.find({ 'userName': userinfo[0] }).count() == 1:
            text = 'The username you entered is already in use, please select an alternative.'
            stage = 'input'
            return render_template( 'signup.html', userInfo=userinfo, nametext=text, stage=stage )
        else:
            if stage == 'request':
                addRequest(userinfo)        
                userinfo = ['','','','','','','']
                session['signup'] = False
                return render_template( 'signup.html', userInfo=userinfo, stage=stage )
            else:
                return render_template( 'signup.html', userInfo=userinfo, stage=stage )
        
    userinfo = ['','','','','','','']
    #stage = 'input'
    session['signup'] = True
    return render_template( 'signup.html', userInfo=userinfo, stage=stage )

@app.route('/admin',methods=['GET','POST'])
def admin_page():
    request_entries = mongo.db.request.find({}, { 'userName': 0, 'password': 0 })
    user_entries = mongo.db.user.find({ 'type': 'user' }, { 'userName': 0, 'password': 0 })
    admin_entries = mongo.db.user.find({ 'type': 'administrator' }, { 'userName': 0, 'password': 0 })
    request = []
    for req in request_entries:
        req.update({ 'authority': 3,
                     'approval': '' }) 
        request.append(req) 
    return render_template( 'admin.html', request=request, user=user_entries, admin=admin_entries )

@app.route('/remove_user',methods=['GET','POST'])
def remove_user():
    userid=request.form.get('id')
    removeUser( userid )

    return redirect( url_for('admin_page') ) 

@app.route('/add_user',methods=['GET','POST'])
def add_user():
    user_entries=request.form.getlist('id')
    authority=request.form.getlist('authority')
    approval=request.form.getlist('approval')
    for user in user_entries:
        if approval[user_entries.index( user )] == 'approve':
            query = { '_id': ObjectId( user ) }
            userinfo = mongo.db.request.find_one( query )
            userinfo.update({ 'authority': authority[user_entries.index( user )] })
            addUser( userinfo ) 
            removeRequest( user )
        elif approval[user_entries.index(user)] == 'deny':
            removeRequest( user )

    return redirect( url_for('admin_page') ) 

if __name__ == '__main__':
    app.run(host=args.fhost, port=args.fport)
