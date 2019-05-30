#################################
# Contacts: Arisa Kubota (akubota@hep.phys.titech.ac.jp)
# Project: Yarr
# Description: Viewer application
# Usage: python app.py --config conf.yml 
# Date: Feb 2019
################################

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

from flask            import Flask, request, redirect, url_for, render_template, session, make_response, jsonify
from flask_pymongo    import PyMongo
from pymongo          import MongoClient
from bson.objectid    import ObjectId 
from werkzeug         import secure_filename # for upload system
from PIL              import Image

sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) )

from scripts.src      import listset
from scripts.src      import static
from scripts.src.func import *

if os.path.isdir( TMP_DIR ): 
    shutil.rmtree( TMP_DIR )
os.mkdir( TMP_DIR )
_DIRS = [UPLOAD_DIR, STATIC_DIR, THUMBNAIL_DIR, JSON_DIR] 
for dir_ in _DIRS:
    os.mkdir( dir_ )

# app 
app = Flask( __name__ )

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
usermongo = PyMongo(app, uri=MONGO_URL+'/'+args.userdb)
usermongo.db.localdb.drop()
fs = gridfs.GridFS(mongo.db)
dbv=args.version

# top page 
@app.route('/', methods=['GET'])
def show_modules_and_chips():

    if session.get( 'uuid' ):
        user_dir = TMP_DIR + '/' + str(session.get( 'uuid' ))
        if os.path.isdir( user_dir ): shutil.rmtree( user_dir )
    else:
        session['uuid'] = str( uuid.uuid4() ) 

    make_dir()
    clean_dir( STATIC_DIR )
    session.pop( 'signup', None )

    query = { 'componentType': 'Module', 'dbVersion': dbv }
    module_entries = mongo.db.component.find( query )
    modules = {}

    for thisModule in module_entries:
        query = { 'parent': str(thisModule['_id']) }
        child_entries = mongo.db.childParentRelation.find( query )
        chipType = thisModule['chipType']
        chips = []

        # grade module
        #score = grade_module(str(thisModule['_id']))

        for child in child_entries:
            query = { '_id': ObjectId(child['child']) }
            thisChip = mongo.db.component.find_one( query )
            chips.append({ '_id'          : str(thisChip['_id']),
                           'serialNumber' : thisChip['serialNumber'],
                           'componentType': thisChip['componentType'],
                           'chipId'       : thisChip['chipId'],
                           'datetime'     : set_time(thisChip['sys']['cts']),
                           'grade'        : {} }) 

        if not chipType in modules:
            modules.update({ chipType: { 'modules': [], 'num': '' } })

        modules[chipType]['modules'].append({ '_id'         : str(thisModule['_id']),
                                              'serialNumber': thisModule['serialNumber'],
                                              'chips'       : chips,
                                              'datetime'    : set_time(thisModule['sys']['cts']),
                                              'grade'       : {},
                                              'stage'       : None })

    for chipType in modules:
        modules[chipType].update({ 'num': len(modules[chipType]['modules']) })
        module = sorted( modules[chipType]['modules'], key=lambda x:x['serialNumber'], reverse=True)
        modules[chipType]['modules'] = module

    return render_template( 'toppage.html', modules=modules )

@app.route('/development', methods=['GET'])
def show_modules_and_chips_develop():

    if session.get( 'uuid' ):
        user_dir = TMP_DIR + '/' + str(session.get( 'uuid' ))
        if os.path.isdir( user_dir ): shutil.rmtree( user_dir )
    else:
        session['uuid'] = str( uuid.uuid4() ) 

    make_dir()
    clean_dir( STATIC_DIR )
    session.pop( 'signup', None )

    query = { 'componentType': 'Module' }
    module_entries = mongo.db.component.find( query )
    modules = {}

    for thisModule in module_entries:
        query = { 'parent': str(thisModule['_id']) }
        child_entries = mongo.db.childParentRelation.find( query )
        chips = []
        chipType = thisModule['chipType']

        # grade module
        score  = grade_module(str(thisModule['_id'])) 

        for child in child_entries:
            query = { '_id': ObjectId(child['child']) }
            thisChip = mongo.db.component.find_one( query )
            if 'chipId' in thisChip['serialNumber']:
                chipId = thisChip['serialNumber'].split('chipId')[1]
            else:
                chipId = '1' 
            chips.append({ '_id'          : str(thisChip['_id']),
                           'serialNumber' : thisChip['serialNumber'],
                           'componentType': thisChip['componentType'],
                           'chipId'       : thisChip['chipId'],
                           'datetime'     : set_time(thisChip['sys']['cts']),
                           'grade'        : score.get(chipId,{}) }) 

        if not chipType in modules:
            modules.update({ chipType: { 'modules': [], 'num': '' } })


        modules[chipType]['modules'].append({ '_id'         : str(thisModule['_id']),
                                              'serialNumber': thisModule['serialNumber'],
                                              'chips'       : chips,
                                              'datetime'    : set_time(thisModule['sys']['cts']),
                                              'grade'       : score['module'],
                                              'stage'       : score['stage'] })

    for chipType in modules:
        modules[chipType].update({ 'num': len(modules[chipType]['modules']) })
        module = sorted( modules[chipType]['modules'], key=lambda x:x['serialNumber'], reverse=True)
        modules[chipType]['modules'] = module

    return render_template( 'toppage.html', modules=modules )

# component page 
@app.route('/component', methods=['GET', 'POST'])
def show_component():

    make_dir()

    session['this']  = request.args.get( 'id' )
    session['code']  = request.args.get( 'code', '' )
    session['runId'] = request.args.get( 'runId' )

    # this component
    query = { '_id': ObjectId(session['this']) }
    thisComponent = mongo.db.component.find_one( query )
    componentType = thisComponent['componentType']

    # chips and parent
    if componentType == 'Module':
        ParentId = session['this']
    else:
        query = { 'child': session['this'] }
        thisCPR = mongo.db.childParentRelation.find_one( query )
        ParentId = thisCPR['parent']

    # this module
    query = { '_id': ObjectId(ParentId) }
    thisModule = mongo.db.component.find_one( query )

    # chips of module
    query = { 'parent': ParentId }
    child_entries = mongo.db.childParentRelation.find( query )

    # fill chip and module information
    component = {}
    component_chips = []
    component['chipType'] = thisComponent['chipType']
    for child in child_entries:
        query = { '_id': ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        component_chips.append({ '_id'         : child['child'],
                                 'serialNumber': thisChip['serialNumber'] })

    module = { '_id'         : ParentId,
               'serialNumber': thisModule['serialNumber'] }
    
    # fill photos
    photoDisplay = []
    photoIndex = []
    photos = {}
    #photoDisplay = fill_photoDisplay( thisComponent )            #TODO
    #photoIndex   = fill_photoIndex( thisComponent )              #TODO
    #photos       = fill_photos( thisComponent, session['code'] ) #TODO

    # fill summary 
    summary = fill_summary()

    # fill results
    resultIndex  = fill_resultIndex() 
    results      = fill_results()     
    roots        = fill_roots()    

    component.update({ '_id'         : session['this'],
                       'serialNumber': thisComponent['serialNumber'],
                       'module'      : module,
                       'chips'       : component_chips,
                       'unit'        : thisComponent['componentType'], 
                       'photoDisplay': photoDisplay,
                       'photoIndex'  : photoIndex,
                       'photos'      : photos,
                       'resultIndex' : resultIndex,
                       'results'     : results,
                       'roots'       : roots,
                       'summary'     : summary })

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
    runId       = request.args.get( 'runId' )

    return redirect( url_for('show_component', id=componentId, runId=runId) )

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
    thisComponent = mongo.db.component.find_one( query )

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
        ParentId = child['parent']

    # this module
    query = { '_id': ObjectId(ParentId) }
    thisModule = mongo.db.component.find_one( query )

    # chips of module
    query = { 'parent': ParentId }
    child_entries = mongo.db.childParentRelation.find( query )

    # fill chip and module information
    component = {}
    component_chips = []
    for child in child_entries:
        query = { '_id': ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        component['componentType'] = thisChip['componentType']
        component_chips.append({ '_id'        : child['child'],
                                 'serialNumber': thisChip['serialNumber'] })
    module = { '_id'         : ParentId,
               'serialNumber': thisModule['serialNumber'] }

    query = { '$or': chips }
    run_entries = mongo.db.componentTestRun.find( query )
    stages = []
    for run in run_entries:
        stages.append( run.get('stage') )
    stages = list(set(stages))

    # fill summary 
    summary = fill_summary_test( )

    # fill result index 
    resultIndex = fill_resultIndex()

    component.update({ '_id'         : session['this'],
                       'serialNumber': thisComponent['serialNumber'],
                       'module'      : module,
                       'chips'       : component_chips,
                       'unit'        : unit,
                       'summary'     : summary,
                       'stages'      : stages,
                       'step'        : session['step'],
                       'comments'    : listset.summary_comment,
                       'resultIndex' : resultIndex,
                       'stage'       : session['stage'] })

    return render_template( 'add_summary.html', component=component )

# write summary into db 
@app.route('/add_summary', methods=['GET', 'POST'])
def add_summary():

    componentId = request.args.get( 'id' )
    query = { '_id': ObjectId( componentId ) }
    thisComponent = mongo.db.component.find_one( query )

    for scan in session['summaryList']['before']:

        if session['summaryList']['before'][scan]['runId'] == session['summaryList']['after'][scan]['runId']: continue

        if session['summaryList']['after'][scan]['runId']:

            # make plot 
            make_plot( session['summaryList']['after'][scan]['runId'] )

            # insert testRun and componentTestRun
            query = { 'testRun': session['summaryList']['after'][scan]['runId'] }
            thisComponentTestRun = mongo.db.componentTestRun.find_one( query ) 

            if thisComponentTestRun['component'] == componentId: 
                runId = session['summaryList']['after'][scan]['runId']  

            else:
                thistime = datetime.datetime.utcnow()

                moduleComponentTestRun = thisComponentTestRun
                query = { '_id': ObjectId(session['summaryList']['after'][scan]['runId']) }
                moduleTestRun = mongo.db.testRun.find_one( query )
                moduleComponentTestRun.pop( '_id', None )
                moduleTestRun.pop( '_id', None )

                moduleTestRun.update({ 'attachments': [] })
                moduleTestRun.update({ 'sys': { 'rev': 0,
                                                 'cts': thistime,
                                                 'mts': thistime }})
                runId = str(mongo.db.testRun.insert( moduleTestRun ))
                moduleComponentTestRun.update({ 'component': componentId,
                                                'testRun' : runId,
                                                'sys'       : { 'rev': 0,
                                                                  'cts': thistime,
                                                                  'mts': thistime }})
                mongo.db.componentTestRun.insert( moduleComponentTestRun )

            # add attachments into module TestRun
            query = { 'component': componentId, 'testRun': runId }
            thisComponentTestRun = mongo.db.componentTestRun.find_one( query )
            query = { '_id': ObjectId(runId) }
            thisRun = mongo.db.testRun.find_one( query )

            for mapType in session.get('plotList'):
                if session['plotList'][mapType]['HistoType'] == 1: continue
                url = {} 
                path = {}
                datadict = { '1': '_Dist', '2': '' }
                for i in datadict:
                    filename = '{0}_{1}{2}'.format( thisComponent['serialNumber'], mapType, datadict[i] )
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
        # remove 'display: True' in current summary run
        if session['summaryList']['before'][scan]['runId']:
            query = { '_id': ObjectId(session['summaryList']['before'][scan]['runId']) }
            thisRun = mongo.db.testRun.find_one( query )

            keys = [ 'runNumber', 'institution', 'userIdentity', 'testType' ]
            query_id = dict( [ (key, thisRun[key]) for key in keys ] )
            mongo.db.testRun.update( query_id, { '$set': { 'display': False }}, multi=True )

            mongo.db.testRun.update( query_id, { '$push': { 'comments': { 'userIdentity': session['userIdentity'],
                                                                            'userid'     : session['uuid'],
                                                                            'comment'    : session['summaryList']['after'][scan]['comment'], 
                                                                            'after'      : session['summaryList']['after'][scan]['runId'],
                                                                            'datetime'   : datetime.datetime.utcnow(), 
                                                                            'institution': session['institution'],
                                                                            'description': 'add_summary' }}}, multi=True )
            update_mod( 'testRun', query_id ) 

        query = { 'component': componentId, 'stage': session['stage'], 'testType': scan }
        entries = mongo.db.componentTestRun.find( query )
        for entry in entries:
            query = { '_id': ObjectId( entry['testRun'] )}
            thisRun = mongo.db.testRun.find_one( query )
            keys = [ 'runNumber', 'institution', 'userIdentity', 'testType' ]
            query_id = dict( [ (key, thisRun[key]) for key in keys ] )
            run_entries = mongo.db.testRun.find( query_id )
            for run in run_entries:
                if run.get( 'display' ):
                    query = { '_id': run['_id'] }
                    mongo.db.testRun.update( query, { '$set': { 'display': False }} )
                    update_mod( 'testRun', query )

        # add 'display: True' in selected run
        if session['summaryList']['after'][scan]['runId']:
            query = { '_id': ObjectId(session['summaryList']['after'][scan]['runId']) }
            thisRun = mongo.db.testRun.find_one( query )

            keys = [ 'runNumber', 'institution', 'userIdentity', 'testType' ]
            query_id = dict( [ (key, thisRun[key]) for key in keys ] )

            mongo.db.testRun.update( query_id, { '$set': { 'display': True }}, multi=True )
            update_mod( 'testRun', query_id ) 

    # pop session
    session.pop( 'testType',    None )
    session.pop( 'runId',       None )
    session.pop( 'summaryList', None )
    session.pop( 'stage',       None )
    session.pop( 'step',        None )
    clean_dir( THUMBNAIL_DIR )

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
    clean_dir( thum_dir )
    
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
    runId   = request.args.get( 'runId' )
    histo   = request.args.get( 'histo' )
    mapType = request.args.get( 'mapType' )

    query = { '_id': ObjectId(runId) }
    thisRun = mongo.db.testRun.find_one( query )

    make_plot( runId )

    url = ''
    filename = TMP_DIR + '/' + str(session.get('uuid')) + '/plot/' + str(thisRun['testType']) + '_' + str(mapType) + '_{}.png'.format(histo)
    if os.path.isfile( filename ):
        binary_image = open( filename, 'rb' )
        code_base64 = base64.b64encode(binary_image.read()).decode()
        binary_image.close()
        url = bin_to_image( 'png', code_base64 )  
 
    return redirect( url )

# download config file 
@app.route('/download_config', methods=['GET'])
def download_config() :
    # get code of config file
    code = request.args.get( 'code' )
    json_data = jsonify( json.loads( fs.get( ObjectId(code)).read().decode('ascii') ) )
    response = make_response( json_data )

    return response

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
                 update_mod( collection, query )
            elif session.get('tag') == 'untag':
                 mongo.db[collection].update( query, { '$unset': { 'attachments.{}.display'.format( data_entries.index(data) ): True }})
                 mongo.db[collection].update( query, { '$set' : { 'attachments.{}.description'.format( data_entries.index(data) ): '' }})
                 update_mod( collection, query )
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
    thisComponentTestRun = mongo.db.componentTestRun.find_one({ 'testRun': str(thisRun['_id']) })
    env_dict = fill_env( thisComponentTestRun )
 
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
    update_mod( 'component', query )

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

                update_mod( str(col), query )

    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/edit_comment', methods=['GET','POST'])
def edit_comment():

    query = { '_id': ObjectId(request.form.get( 'id' ))}
    thisComponent = mongo.db.component.find_one( query )

    if thisComponent['componentType'] == 'Module':
        query = { 'parent': request.form.get('id') }
    else:
        query = { 'child': request.form.get('id') }
        parentId = mongo.db.childParentRelation.find_one( query )['parent']
        query = { 'parent': parentId }

    child_entries = mongo.db.childParentRelation.find( query )
    component_chips = []
    for child in child_entries:
        component_chips.append({ 'component': child['child'] })

    query = { '$or': component_chips, 'runNumber': int(request.form.get( 'runNumber' )) }
    run_entries = mongo.db.componentTestRun.find( query )
    for run in run_entries:
        query = { '_id': ObjectId(run['testRun']) }
        comment_entries = mongo.db.testRun.find_one( query )['comments']
        if session['user_name'] in [ comment.get('user') for comment in comment_entries ]:
            mongo.db.testRun.update( query, { '$set': { 'comments.{}.comment'.format( comment_entries.index(comment) ): request.form.get('text') } } )
            mongo.db.testRun.update( query, { '$set': { 'comments.{}.datetime'.format( comment_entries.index(comment) ): datetime.datetime.utcnow() } } )
        elif comment_entries == {}:
            mongo.db.testRun.update( query, { '$set': { 'comments': [{ 'user'    : session['user_name'],
                                                                         'userid'  : session['user_id'],
                                                                         'comment' : request.form.get('text'), 
                                                                         'datetime': datetime.datetime.utcnow(), 
                                                                         'institution': session['institution'] }] }} )
        else:
            mongo.db.testRun.update( query, { '$push': { 'comments': { 'user'    : session['user_name'],
                                                                         'userid'  : session['user_id'],
                                                                         'comment' : request.form.get('text'), 
                                                                         'datetime': datetime.datetime.utcnow(), 
                                                                         'institution': session['institution'] } }} )
        update_mod( 'testRun', query )
        #userquery = { 'userName': session['user_name'] }
        #usermongo.db.user.update( userquery , { '$push': { 'commentTestRun': query }})
 
    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), runNumber=request.form.get( 'runNumber' )) )

@app.route('/remove_comment', methods=['GET','POST'])
def remove_comment():

    query = { '_id': ObjectId(request.form.get( 'id' ))}
    thisComponent = mongo.db.component.find_one( query )

    if thisComponent['componentType'] == 'Module':
        query = { 'parent': request.form.get('id') }
    else:
        query = { 'child': request.form.get('id') }
        parentId = mongo.db.childParentRelation.find_one( query )['parent']
        query = { 'parent': parentId }

    child_entries = mongo.db.childParentRelation.find( query )
    component_chips = []
    for child in child_entries:
        component_chips.append({ 'component': child['child'] })

    query = { '$or': component_chips, 'runNumber': int(request.form.get( 'runNumber' )) }

    run_entries = mongo.db.componentTestRun.find( query )
    for run in run_entries:
        query = { '_id': ObjectId(run['testRun']) }
        mongo.db.testRun.update( query, { '$pull': { 'comments': { 'user': request.form.get( 'user' ) }}} )
        update_mod( 'testRun', query )
        #userquery = { 'userName': request.form.get('user') }
        #usermongo.db.user.update( userquery , { '$pull': { 'commentTestRun': query }})

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
                                                                          'photoNumber': count_photoNum(),
                                                                          'contentType': filename.rsplit( '.', 1 )[1],
                                                                          'filename'  : filename }}})
        update_mod( 'component', query )

    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/remove_attachment',methods=['GET','POST'])
def remove_attachment():
    code = request.form.get( 'code' )
    
    fs.delete( ObjectId(code) )
    query = { '_id': ObjectId(request.form.get('id')) }
    mongo.db.component.update( query, { '$pull': { 'attachments': { 'code': code }}}) 
    update_mod( 'component', query )

    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get('id')) )

@app.route('/login',methods=['POST'])
def login():

    query = { 'userName': request.form['username'] }
    userName = usermongo.db.user.find_one( query )
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
        if usermongo.db.user.find({ 'userName': userinfo[0] }).count() == 1 or usermongo.db.request.find({ 'userName': userinfo[0] }).count() == 1:
            text = 'The username you entered is already in use, please select an alternative.'
            stage = 'input'
            return render_template( 'signup.html', userInfo=userinfo, nametext=text, stage=stage )
        else:
            if stage == 'request':
                add_request(userinfo)        
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
    request_entries = usermongo.db.request.find({}, { 'userName': 0, 'password': 0 })
    user_entries = usermongo.db.user.find({ 'type': 'user' }, { 'userName': 0, 'password': 0 })
    admin_entries = usermongo.db.user.find({ 'type': 'administrator' }, { 'userName': 0, 'password': 0 })
    request = []
    for req in request_entries:
        req.update({ 'authority': 3,
                     'approval': '' }) 
        request.append(req) 
    return render_template( 'admin.html', request=request, user=user_entries, admin=admin_entries )

@app.route('/remove_user',methods=['GET','POST'])
def remove_user():
    userid=request.form.get('id')
    remove_user( userid )

    return redirect( url_for('admin_page') ) 

@app.route('/add_user',methods=['GET','POST'])
def add_user():
    user_entries=request.form.getlist('id')
    authority=request.form.getlist('authority')
    approval=request.form.getlist('approval')
    for user in user_entries:
        if approval[user_entries.index( user )] == 'approve':
            query = { '_id': ObjectId( user ) }
            userinfo = usermongo.db.request.find_one( query )
            userinfo.update({ 'authority': authority[user_entries.index( user )] })
            add_user( userinfo ) 
            remove_request( user )
        elif approval[user_entries.index(user)] == 'deny':
            remove_request( user )

    return redirect( url_for('admin_page') ) 

if __name__ == '__main__':
    app.run(host=args.fhost, port=args.fport)
