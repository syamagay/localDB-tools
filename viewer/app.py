#!/usr/bin/env python3
#coding:UTF-8
#################################
# Contacts: Arisa Kubota (akubota@hep.phys.titech.ac.jp)
# Project: Yarr
# Description: Viewer application
# Usage: python app.py --config conf.yml 
# Date: Feb 2019
################################
import os
import sys
sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) )

# Magical word
from configs.development import *

#==============================
# Setup logging
#==============================
setupLogging("logs/development.log")

# module
import hashlib
import datetime
import shutil
import uuid
import base64                          # Base64 encoding scheme
import gridfs                          # gridfs system 
import io
import yaml
import pytz
import string
import secrets

from flask              import Flask, request, redirect, url_for, render_template, session, make_response, jsonify, send_file, send_from_directory
from flask_pymongo      import PyMongo
from flask_httpauth     import HTTPBasicAuth
from flask_httpauth     import HTTPDigestAuth
from flask_mail         import Mail, Message
from pymongo            import MongoClient, errors
from bson.objectid      import ObjectId 
from werkzeug           import secure_filename # for upload system
from PIL                import Image
from getpass            import getpass

# For retriever
from retrievers.component import retrieve_component_api
from retrievers.testrun import retrieve_testrun_api
from retrievers.config import retrieve_config_api
from retrievers.log import retrieve_log_api
from retrievers.remote import retrieve_remote_api

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
app.register_blueprint(sync_statistics_api)
app.register_blueprint(retrieve_component_api)
app.register_blueprint(retrieve_testrun_api)
app.register_blueprint(retrieve_config_api)
app.register_blueprint(retrieve_log_api)
app.register_blueprint(retrieve_remote_api)

mail = Mail(app)

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
auth = HTTPBasicAuth()

dbv=1.01

if args.localdbkey:
    password_text = open(args.localdbkey,"r")
    password = password_text.read().split()
    password_text.close()

# MongoDB settings
def init():
    global USER_FUNCTION
    USER_FUNCTION = False
    max_server_delay = 10
    url = 'mongodb://{0}:{1}'.format(args.host,args.port)
    ### check ssl
    db_ssl = args.ssl
    if db_ssl==True:
        db_ca_certs = args.sslCAFile
        db_certfile = args.sslPEMKeyFile
        url+='/?ssl=true&ssl_ca_certs={0}&ssl_certfile={1}&ssl_match_hostname=false&authMechanism=MONGODB-X509'.format(db_ca_certs,db_certfile)
    else:
        db_ca_certs = None 
        db_certfile = None 
    client = MongoClient( url,
                          serverSelectionTimeoutMS=max_server_delay,
    )
    localdb = client[args.db]
    username = None
    password = None
    auth = ''
    try:
        localdb.collection_names()
    except errors.ServerSelectionTimeoutError as err:
        ### Connection failed
        print('The connection of Local DB {} is BAD.'.format(url))
        print(err)
        sys.exit(1)
    except errors.OperationFailure as err: 
        print('Need user authentication.')
        USER_FUNCTION = True
        ### Need user authentication
        if args.localdbkey: username = password[0]
        if args.localdbkey: password = password[1]
        through = False
        while through==False:
            if not username or not password: 
                answer = input('Continue? [y/n(skip)]\n> ')
                print('')
                if answer.lower()=='y':
                    username = None
                    password = None
                else:
                    sys.exit(1)
                username = input('User name > ')
                print('')
                password = getpass('Password > ')
                print('')
            try:
                localdb.authenticate(username, password)
                through = True
            except errors.OperationFailure as err: 
                args.localdbkey = None
                print('Authentication failed.')
                answer = input('Try again? [y/n(skip)]\n> ')
                print('')
                if answer.lower()=='y':
                    username = input('User name > ')
                    print('')
                    password = getpass('Password > ')
                    print('')
                else:
                    sys.exit(1)
    if username and password:
        auth = '{0}:{1}@'.format(username,password)

    MONGO_URL = 'mongodb://{0}{1}:{2}/{3}'.format(auth,args.host,args.port,args.db)
    if db_ssl==True:
        MONGO_URL+='?ssl=true&ssl_ca_certs={0}&ssl_certfile={1}&ssl_match_hostname=false&authMechanism=MONGODB-X509'.format(db_ca_certs,db_certfile)

    return MONGO_URL

############
### Top Page 
@app.route('/', methods=['GET'])
def show_toppage():

    if session.get( 'uuid' ):
        user_dir = TMP_DIR + '/' + str(session.get( 'uuid' ))
        if os.path.isdir( user_dir ): shutil.rmtree( user_dir )
    else:
        session['uuid'] = str( uuid.uuid4() ) 

    makeDir()
    cleanDir( STATIC_DIR )
    session.pop( 'signup', None )

    return render_template( 'toppage.html', timezones=setTimezone() )

##########################
### Registered Module Page 
@app.route('/module', methods=['GET'])
def show_modules_and_chips():

    ### query modules
    query = { 
        '$or': [{'componentType': 'module'}, {'componentType': 'Module'}], 
        'dbVersion'    : dbv 
    }
    module_entries = mongo.db.component.find( query )
    module_ids = []
    for module in module_entries:
        module_ids.append(str(module['_id']))
    modules = {}
    for module_id in module_ids:
        query = { '_id': ObjectId(module_id) }
        this_module = mongo.db.component.find_one( query )
        chip_type = this_module['chipType']
        if not chip_type in modules:
            modules.update({ chip_type: { 'modules': [], 'num': '' } })

        ### child chips
        query = { 'parent': module_id }
        child_entries = mongo.db.childParentRelation.find( query )
        chip_ids = []
        for child in child_entries:
            chip_ids.append(child['child'])
        chips = []
        for chip_id in chip_ids:
            query = { '_id': ObjectId(chip_id) }
            this_chip = mongo.db.component.find_one( query )
            try:
                name = this_chip['name']
            except:
                name = this_chip['serialNumber']
            chips.append({ 
                '_id'         : chip_id,
                'collection'  : 'component',
                'name'        : name,
                'grade'       : {} 
            }) 

        ### Latest Scan
        query = { 'component': module_id  }
        run_entries = mongo.db.componentTestRun.find(query).sort([( '$natural', -1 )]).limit(1)
        result = { 
            'stage'   : None, 
            'runId'   : None,
            'datetime': None,
            'user'    : None,
            'site'    : None 
        }
        for this_ctr in run_entries:
            query = { '_id': ObjectId(this_ctr['testRun']) }
            this_run = mongo.db.testRun.find_one(query)
            ### user
            query = { '_id': ObjectId(this_run['user_id']) }
            this_user = mongo.db.user.find_one(query)
            ### site
            query = { '_id': ObjectId(this_run['address']) }
            this_site = mongo.db.institution.find_one(query)
            result.update({ 
                'stage'   : this_run['stage'].replace('_', ' '), 
                'runId'   : str(this_run['_id']),
                'datetime': setTime(this_run['startTime']),
                'user'    : this_user['userName'].replace('_', ' '),
                'site'    : this_site['institution'].replace('_', ' ')
            })

        try:
            name = this_module['name']
        except:
            name = this_module['serialNumber']
        modules[chip_type]['modules'].append({ 
            '_id'          : module_id,
            'collection'   : 'component',
            'name'         : name,
            'chips'        : chips,
            'grade'        : {},
            'stage'        : result['stage'], 
            'runId'        : result['runId'], 
            'datetime'     : result['datetime'],
            'user'         : result['user'],
            'site'         : result['site'],
            'proDB'        : this_module.get('proDB',False) 
        })

    for chip_type in modules:
        modules[chip_type].update({ 'num': len(modules[chip_type]['modules']) })
        module = sorted( modules[chip_type]['modules'], key=lambda x:x['name'], reverse=True)
        modules[chip_type]['modules'] = module

    return render_template( 'module.html', modules=modules, timezones=setTimezone() )

####################
### Tested Chip Page 
@app.route('/chip', methods=['GET'])
def show_chips():

    ### query chips
    query = { 'dbVersion': dbv }
    chip_entries = mongo.db.chip.find( query )
    chip_ids = []
    for chip in chip_entries:
        chip_ids.append(str(chip['_id']))
    chips = {}
    for chip_id in chip_ids:
        query = { '_id': ObjectId(chip_id) }
        this_chip = mongo.db.chip.find_one( query )
        chip_type = this_chip['chipType']
        if not chip_type in chips:
            chips.update({ chip_type: { 'chips': [], 'num': '' } })

        ### Latest Result
        query = { 'chip': chip_id }
        run_entries = mongo.db.componentTestRun.find(query).sort([( '$natural', -1 )]).limit(1)
        result = { 
            'stage'   : None, 
            'runId'   : None,
            'datetime': None,
            'user'    : None,
            'site'    : None 
        }
        for this_ctr in run_entries:
            query = { '_id': ObjectId(this_ctr['testRun']) }
            this_run = mongo.db.testRun.find_one(query)
            ### user
            query = { '_id': ObjectId(this_run['user_id']) }
            this_user = mongo.db.user.find_one(query)
            ### site
            query = { '_id': ObjectId(this_run['address']) }
            this_site = mongo.db.institution.find_one(query)
            result.update({ 
                'stage'   : this_run['stage'].replace('_', ' '), 
                'runId'   : str(this_run['_id']),
                'datetime': setTime(this_run['startTime']),
                'user'    : this_user['userName'].replace('_', ' '),
                'site'    : this_site['institution'].replace('_', ' ')
            })

        chips[chip_type]['chips'].append({ 
            '_id'          : chip_id,
            'collection'   : 'chip',
            'name'         : this_chip['name'],
            'chipId'       : this_chip.get('chipId',-1),
            'stage'        : result['stage'], 
            'runId'        : result['runId'], 
            'datetime'     : result['datetime'], 
            'user'         : result['user'], 
            'site'         : result['site'] 
        }) 

    for chip_type in chips:
        chips[chip_type].update({ 'num': len(chips[chip_type]['chips']) })
        chip = sorted( chips[chip_type]['chips'], key=lambda x:x['name'], reverse=True)
        chips[chip_type]['chips'] = chip

    return render_template( 'chip.html', chips=chips, timezones=setTimezone() )

### component page 
@app.route('/component', methods=['GET', 'POST'])
def show_component():

    makeDir()

    session['this']  = request.args.get( 'id', None )
    session['collection'] = request.args.get( 'collection', 'chip' )
    session['code']  = request.args.get( 'code', '' )
    session['runId'] = request.args.get( 'runId', None )
    session['unit'] = 'front-end_chip' ### TODO just temporary coding

    comment_query = []
    if session.get('runId',None):
        comment_query.append({ 'runId': session['runId'] })

    # component info
    cmp_info = {}
    if session.get('this',None):
        ### this component
        query = { '_id': ObjectId(session['this']) }
        this_cmp = mongo.db[session['collection']].find_one( query )

        # component type
        cmp_type = str(this_cmp['componentType']).lower().replace(' ','_')
        session['unit'] = cmp_type.lower().replace(' ','_')

        ### check the parent
        if cmp_type == 'module':
            parent_id = session['this']
        else:
            query = { 'child': session['this'] }
            this_cpr = mongo.db.childParentRelation.find_one( query )
            if this_cpr: parent_id = this_cpr['parent']
            else: parent_id = None

        module = {}
        component_chips = []
        comment_query.append({ 'componentId': session['this'] })
        if parent_id:
            ### this module
            query = { '_id': ObjectId(parent_id) }
            this_module = mongo.db.component.find_one( query )
            comment_query.append({ 'componentId': parent_id })
            
            ### chips of module
            query = { 'parent': parent_id }
            child_entries = mongo.db.childParentRelation.find( query )
            chip_ids = []
            for child in child_entries:
                chip_ids.append(child['child'])
                comment_query.append({ 'componentId': child['child'] })
  
            ### set chip and module information
            for chip_id in chip_ids:
                query = { '_id': ObjectId(chip_id) }
                this_chip = mongo.db.component.find_one( query )
                component_chips.append({ 
                    '_id'         : chip_id,
                    'collection'  : 'component',
                    'chipId'      : this_chip.get('chipId',-1),
                    'name'        : this_chip['name'] 
                })
            module.update({ 
                '_id'       : parent_id,
                'collection': 'component',
                'name'      : this_module['name'] 
            })

        cmp_info.update({
            'name'       : this_cmp['name'],
            'module'     : module,
            'chips'      : component_chips,
            'unit'       : session['unit'].replace('_', ' '), 
            'chipType'   : this_cmp['chipType']
        })

    # comment
    comments=[]
    comment_entries = mongo.db.comments.find({ '$or':comment_query })
    for comment in comment_entries:
        comments.append(comment)
    
    # set summary 
#    summary = setSummary()

    summary={}
    # set results
    result_index = setResultIndex() 
    results = setResults()     
    roots = setRoots()    
    dcs = setDCS()

    component = { 
        '_id'        : session.get('this',None),
        'collection' : session['collection'],
        'info'       : cmp_info,
        'comments'   : comments, 
        'resultIndex': result_index,
        'results'    : results,
        'roots'      : roots,
        'dcs'        : dcs,
        'summary'    : summary,
    }

    return render_template( 'component.html', component=component, timezones=setTimezone() )

#################
### test run page
@app.route('/scan', methods=['GET', 'POST'])
def show_scans():
    
    max_num = 10
    sort_cnt = int(request.args.get('p',0))

    query = { 'dbVersion': dbv }
    run_entries = mongo.db.testRun.find(query).sort([( '$natural', -1 )] )
    run_counts = mongo.db.testRun.count_documents(query)
    run_ids = []
    for i, this_run in enumerate(run_entries):
        if i//max_num<sort_cnt: continue
        elif i//max_num==sort_cnt: run_ids.append(str(this_run['_id']))
        else: break

    cnt = []
    for i in range((run_counts//max_num)+1):
        if sort_cnt-(max_num/2)<i:
            cnt.append(i)
        if len(cnt)==max_num:
            break

    scans = {
        'run'    :[],
        'total'  : run_counts,
        'cnt'    : cnt,
        'now_cnt': sort_cnt,
        'max_cnt': (run_counts//max_num)
    }

    for run_id in run_ids:
        query = { '_id': ObjectId(run_id) }
        this_run = mongo.db.testRun.find_one (query)
        ### user
        query = { '_id': ObjectId(this_run['user_id']) }
        this_user = mongo.db.user.find_one(query)
        user_name = this_user['userName'].replace('_', ' ')
        ### site
        query = { '_id': ObjectId(this_run['address']) }
        this_site = mongo.db.institution.find_one(query)
        site_name = this_site['institution'].replace('_', ' ')
        ### component
        query = { 'testRun': run_id }
        ctr_entries = mongo.db.componentTestRun.find(query)
        components = []
        for this_ctr in ctr_entries:
            if not this_ctr['component']=='...':
                cmp_id = this_ctr['component']
                collection = 'component'
            else:
                cmp_id = this_ctr['chip']
                collection = 'chip'
            components.append({ 
                'name'      : this_ctr.get('name','NONAME'), 
                'enabled'   : this_ctr.get('enable',1)==1, 
                '_id'       : cmp_id, 
                'chip_id'   : this_ctr['chip'], 
                'collection': collection 
            })
        run_data = {
            '_id'       : run_id,
            'datetime'  : setTime(this_run['startTime']),
            'testType'  : this_run['testType'].replace('_', ' '),
            'runNumber' : this_run['runNumber'],
            'stage'     : this_run['stage'],
            'plots'     : (this_run['plots']!=[]),
            'components': components,
            'user'      : user_name,
            'site'      : site_name
        }
        scans['run'].append(run_data)

    scans['run'] = sorted(scans['run'], key=lambda x:x['datetime'], reverse=True)

    return render_template( 'scan.html', scans=scans, timezones=setTimezone() )

#### result page
#@app.route('/result', methods=['GET', 'POST'])
#def show_result():
#
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
    if session['this']==this_run['name']: cmp_type = 'Module'
    else: cmp_type = 'Front-end Chip'

    # chips and parent
    if cmp_type == 'Module': parent_id = session['this']
    else: parent_id = this_run['name']

    # this module
    module = { 
        '_id': parent_id,
        'name': 'DummyModule' 
    }

    # get comments for this module
    query = {'runId':session['runId']}
    comments=[]
    comment_entries = mongo.db.comments.find(query)
    for comment in comment_entries:
        comments.append(comment)
  

    # chips of module
    component_chips = []
    query = { 
        'testRun': session['runId'], 
        'component':{'$ne': this_run['name']} 
    }
    ctr_entries = mongo.db.componentTestRun.find(query)
    for ctr_entry in ctr_entries:
        component_chips.append({
            '_id': ctr_entry['component'],
            'geomId': ctr_entry['geomId'],
            'name': 'DummyChip{}'.format(ctr_entry['geomId'])
        })

    # set photos
    photo_display = []
    photo_index = []
    photos = {}
 
    # set results
    result_index = {}
    results      = setResults()
    roots        = setRoots()    
    dcs          = setDCS()

    component = { 
        '_id'         : session['this'],
        'name'        : '---',
        'module'      : module,
        'chips'       : component_chips,
        'unit'        : cmp_type,
        'chipType'    : '', #TODO
        'comments'    : comments,
        'photoDisplay': photo_display,
        'photoIndex'  : photo_index,
        'photos'      : photos,
        'resultIndex' : result_index,
        'results'     : results,
        'roots'       : roots,
        'dcs'         : dcs,
        'summary'     : {},
        'dummy'       : True
    }

    return render_template( 'component.html', component=component, timezones=setTimezone() )

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

## make Graph from DCS_data                                                                                                
@app.route('/make_dcsGraph', methods=['GET','POST'])
def make_dcsGraph() :
    # get from form                                                                                                        
    session['dcsplotType']  = request.form.get( 'dcsplotType' )
    if not session.get('dcsStat') :
        session['dcsStat']={}


    if session['dcsplotType']=='make' or session['dcsplotType']=='make' :
        if request.form.get('dataType') == 'iv' :
            target=[ request.form.get('key_v'), request.form.get('key_i') ]
            session['dcsStat'].update({ target[0] : { 'min' : request.form.get( 'v_min' ),
                                                      'max' : request.form.get( 'v_max' ),
                                                      'step': request.form.get( 'v_step')}
                                    })
            session['dcsStat'].update({ target[1] : { 'min' : request.form.get( 'i_min' ),
                                                      'max' : request.form.get( 'i_max' ),
                                                      'step': request.form.get( 'i_step')}
                                    })
        elif request.form.get('dataType') == 'other' :
            target=request.form.get('dcsType')
            session['dcsStat'].update({ target : { "min" : request.form.get( 'min' ),
                                                   "max" : request.form.get( 'max' ),
                                                   'step': request.form.get( 'step')}
                                    })
    if session['dcsplotType']=='make_TimeRange' :
        start_timezone = request.form.get('start_timezone')
        start_year = request.form.get('start_year')
        start_month= request.form.get('start_month')
        start_day  = request.form.get('start_day')
        start_hour = request.form.get('start_hour')
        start_min  = request.form.get('start_minute')
        start_sec  = request.form.get('start_second')

        end_timezone = request.form.get('end_timezone')
        end_year = request.form.get('end_year')
        end_month= request.form.get('end_month')
        end_day  = request.form.get('end_day')
        end_hour = request.form.get('end_hour')
        end_min  = request.form.get('end_minute')
        end_sec  = request.form.get('end_second')

        start=datetime.strptime('{0}-{1}-{2}T{3}:{4}:{5} {6}'.format(start_year,start_month,start_day,start_hour,start_min,start_sec,start_timezone),'%Y-%m-%dT%H:%M:%S %z').astimezone(pytz.timezone('UTC'))
#        start=datetime.strptime(setTime(start),'%Y/%m/%d %H:%M:%S')
        end=datetime.strptime('{0}-{1}-{2}T{3}:{4}:{5} {6}'.format(end_year,end_month,end_day,end_hour,end_min,end_sec,end_timezone),'%Y-%m-%dT%H:%M:%S %z').astimezone(pytz.timezone('UTC'))
#        end=datetime.strptime(setTime(end),'%Y/%m/%d %H:%M:%S')

        session['dcsStat'].update({ 'timeRange' : [time.mktime(start.timetuple()),
                                                   time.mktime(end.timetuple())
                                               ]
                                }
        )
    elif session['dcsplotType']=='set_defaultTimeRange' :
        session['dcsStat'].pop('timeRange',None)
     # get from args                                                                                                      \
                                                                                                                           
    componentId = request.args.get( 'id' )
    runId       = request.args.get( 'runId' )

    return redirect( url_for("show_component", id=componentId, runId=runId) )


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

    if not str(mongo.db.component.find_one( query )['componentType']).lower().replace(' ','_') == 'Module'.lower().replace(' ','_'):
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
        #str(component['componentType']).lower().replace(' ','_') = str(this_chip['componentType']).lower().replace(' ','_')
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

    return render_template( 'add_summary.html', component=component, timezones=setTimezone() )

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
@app.route('/display_data', methods=['GET'])
def display_data() :
    
    # get code of config file
    code = request.args.get('code')
    data_type = request.args.get('type')
    if data_type=='json':
        json_data = jsonify( json.loads( fs.get( ObjectId(code)).read().decode('ascii') ) )
        response = make_response( json_data )
    elif data_type=='dat':
        dat_data = fs.get( ObjectId(code)).read().decode('ascii')
        response = make_response( dat_data )
#return Response(f.read(), mimetype='text/plain')

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
        return render_template( 'error.html', txt='something error', timezones=setTimezone() )
    data_entries = mongo.db[ str(col) ].find_one( query )['attachments']
    for data in data_entries:
        if data['code'] == request.form.get( 'code' ):
            if 'display' in data:
                mongo.db[ str(col) ].update( query, { '$set': { 'attachments.{}.description'.format( data_entries.index(data) ): request.form.get('description') }})

                updateData( str(col), query )

    forUrl = 'show_component'

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/edit_comment', methods=['GET','POST'])
def edit_comment():

    thistime = datetime.datetime.utcnow()
    mongo.db.comments.insert( 
    { 
        'sys'          : { 'rev': 0,'cts': thistime,'mts': thistime}, 
        'componentId'  : request.args.get( 'id', -1 ),
        'runId'        : request.args.get( 'runId', -1 ),
        'comment'      :request.form.get('text').replace('\r\n','<br>'),
        'componentType':session['unit'],
        'collection'   :session['collection'],
        #'name'         :session['username'],
        'userId'       :session['userId'],
        'name'         :request.form.get('text2'),
        #'institution'  :session['institution'],
        'institution'  :request.form.get('text3'),
        'datetime'     :thistime 
    } 
    )
    

#    if not runid == -1:
#        query = { '_id': ObjectId(runid) }
#        this_test = mongo.db.testRun.find_one( query )
#        
#        if not this_test['dummy']:
#            forUrl = 'show_component'
#        else:
#            forUrl = 'show_dummy'
#
#        return redirect( url_for(forUrl, id=request.args.get( 'id' ), runId=request.args.get( 'runId' ) ))
#    else:
    return redirect( request.headers.get("Referer") )

@app.route('/remove_comment', methods=['GET','POST'])
def remove_comment():

    query = { '_id': ObjectId(request.form.get( 'id' ))}
    this_cmp = mongo.db.component.find_one( query )

    if str(this_cmp['componentType']).lower().replace(' ','_') == 'Module'.lower().replace(' ','_'):
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

    if args.localdbkey:
        MONGO_URL = 'mongodb://' + password[0] + ':' + password[1] + '@' + args.host + ':' + str(args.port) 
    else:
        MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo     = PyMongo(app, uri=MONGO_URL+'/'+args.userdb+'?authSource=localdb')
#    mongo     = PyMongo(app, uri=MONGO_URL+'/'+args.userdb)
    fs = gridfs.GridFS(mongo.db)

    pre_url = request.headers.get("Referer")
    pre_url_lastpass = pre_url.split('/')

    query = { 'username':request.form['username'] }
    user = mongo.db.user.find_one(query)
    query = {}
    string = mongo.db.string.find_one(query)
    if user == None:
        txt = 'This user does not exist'
        if not pre_url_lastpass[-1] == 'login':
           session['pre_url'] = pre_url 
        return render_template( 'error.html', txt=txt, timezones=setTimezone() )

    else:
        if hashlib.md5( request.form['password'].encode('utf-8') ).hexdigest() == user['password']:
            
           session['logged_in'] = True
           session['username']  = user['username']
           session['institution'] = user['institution']
           session['userId'] = str(user['_id'])
           if pre_url_lastpass[-1] == 'register_password' or pre_url_lastpass[-1] == 'login' or pre_url_lastpass[-1] == 'signup':
               return redirect( session['pre_url'])
           else:
               return redirect( pre_url )
        else:
           txt = 'This password is not correct'
           if not pre_url_lastpass[-1] == 'login':
              session['pre_url'] = pre_url 
           return render_template( 'error.html', txt=txt, timezones=setTimezone() )
            

@app.route('/logout',methods=['GET','POST'])
def logout():
    pre_url = request.headers.get("Referer")
    session['logged_in'] = False
    session['username'] = ''
    session['institution'] = ''
    session['userId'] = ''

    return redirect( pre_url )
#    return render_template( 'toppage.html', timezones=setTimezone() )

if args.localdbkey:
    users = {password[0]:password[1]}
else:
    users = {'username':hashlib.md5( 'password'.encode('utf-8') ).hexdigest()}

@auth.get_password
def get_pw(username):
    if username in users:
        return users.get(username)  
    return None

@auth.hash_password
def hash_pw(password):
    return hashlib.md5( password.encode('utf-8') ).hexdigest()


@app.route('/signup',methods=['GET','POST'])
@auth.login_required
def signup():
    if args.localdbkey:
        MONGO_URL = 'mongodb://' + password[0] + ':' + password[1] + '@' + args.host + ':' + str(args.port) 
    else:
        MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo     = PyMongo(app, uri=MONGO_URL+'/'+args.userdb+'?authSource=localdb')
#    mongo     = PyMongo(app, uri=MONGO_URL+'/'+args.userdb)
    fs = gridfs.GridFS(mongo.db)

    stage = request.form.get('stage','input')
    userinfo = request.form.getlist('userinfo')
    if userinfo==[]:
        session.pop('signup',None)     
   
    if session.get('signup',None):
#        if not userinfo[0] == args.uusername and userinfo[1] == args.upassword:
#            text = 'Admins username or password is not correct'
#            stage = 'input'
#            return render_template( 'signup.html', userInfo=userinfo, passtext=text, stage=stage, timezones=setTimezone() )
     
        username=userinfo[0].split()
        if not userinfo[4] == userinfo[5]:
            text = 'Please make sure your Email match'
            stage = 'input'
            return render_template( 'signup.html', userInfo=userinfo, passtext=text, stage=stage, timezones=setTimezone() )
        if mongo.db.user.find({'username': userinfo[0]}).count() == 1:
            text = 'This username is already in use, please select an alternative.'
            stage = 'input'
            return render_template( 'signup.html', userInfo=userinfo, nametext=text, stage=stage, timezones=setTimezone() )
        else:
            if stage == 'input':
                return render_template( 'signup.html', userInfo=userinfo, stage=stage, timezones=setTimezone() )
            if stage == 'confirm':
                return render_template( 'signup.html', userInfo=userinfo, stage=stage, timezones=setTimezone() )
            else:
                thistime = datetime.datetime.now()
                mongo.db.user.insert( 
                {    
                    'sys'          : { 'rev': 0,'cts': thistime,'mts': thistime}, 
                    'username'     :userinfo[0],
                    'name'         :userinfo[1] + ' ' + userinfo[2], 
                    'auth'         :'readWrite',
                    'institution'  :userinfo[3],
                    'Email'        :userinfo[4]
                } 
                )

                msg = Message('Register your Password',
                              sender='admin@localdb.com',
                              recipients=[userinfo[4]])
                mail_text = open("mail_text.txt","r")
                contents = mail_text.read()
                msg.html = contents.replace('USERNAME',userinfo[0]).replace('ADDRESS',userinfo[4]) 
                mail_text.close()
                mail.send(msg)
                session.pop('signup')
                return render_template( 'signup.html', userInfo=userinfo, stage=stage, timezones=setTimezone() )
        
    userinfo = ['','','','','','']
    pre_url = request.headers.get("Referer")
    session['pre_url'] = pre_url

    session['signup'] = True

    return render_template( 'signup.html', userInfo=userinfo, stage=stage, timezones=setTimezone() )

@app.route('/register_password',methods=['GET','POST'])
def register_password():

    if args.localdbkey:
        MONGO_URL = 'mongodb://' + password[0] + ':' + password[1] + '@' + args.host + ':' + str(args.port) 
    else:
        MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo     = PyMongo(app, uri=MONGO_URL+'/'+args.userdb+'?authSource=localdb')
#    mongo     = PyMongo(app, uri=MONGO_URL+'/'+args.userdb)
    fs = gridfs.GridFS(mongo.db)

    stage = request.form.get('stage','input')
    userinfo = request.form.getlist('userinfo')
    if userinfo==[]:   
        session.pop('registerpass',None)
    if session.get('registerpass',None):
        if mongo.db.user.find({'username': userinfo[0]}).count() == 0:
            text = 'This username does not exist'
            stage = 'input'
            return render_template( 'register_password.html', userInfo=userinfo, nametext=text, stage=stage, timezones=setTimezone() )
        else:
            query = { 'username' : userinfo[0] }
            userdata = mongo.db.user.find_one(query)
            if not userdata['Email'] == userinfo[1] :
                text = 'This Email is not correct'
                stage = 'input'
                return render_template( 'register_password.html', userInfo=userinfo, nametext2=text, stage=stage, timezones=setTimezone() )
            else:
                if stage == 'input':
                    return render_template( 'register_password.html', userInfo=userinfo, stage=stage, timezones=setTimezone() )
                if stage == 'confirm':
                    num = 6
                    pool  = string.digits
                    pin_number = "".join([secrets.choice(pool) for i in range(num)])
                    msg = Message('Your Pin Number',
                                  sender='admin@localdb.com',
                                  recipients=[userinfo[1]])
                    msg.html = 'Your pin number is ' + pin_number + '. ' + '(You cannot reply to this Email address.)'   
                    mail.send(msg)
                    mongo.db.user.update(query,{'$set':{'pinnumber':hashlib.md5( pin_number.encode('utf-8') ).hexdigest()}}) 
                    return render_template( 'register_password.html', userInfo=userinfo, stage=stage, timezones=setTimezone() )
                else:
                    if not userdata['pinnumber'] == hashlib.md5( userinfo[2].encode('utf-8') ).hexdigest(): 
                        text = 'This pin number is not correct'
                        stage = 'confirm'
                        return render_template( 'register_password.html', userInfo=userinfo, nametext3=text, stage=stage, timezones=setTimezone() )
                    if not userinfo[3] == userinfo[4]:
                        text = 'Please make sure your password match'
                        stage = 'confirm'
                        return render_template( 'register_password.html', userInfo=userinfo, nametext4=text, stage=stage, timezones=setTimezone() )
                    else: 
                        mongo.db.user.update(query,{'$unset':{'pinnumber':''}}) 
                        mongo.db.user.update(query,{'$set':{'password':hashlib.md5( userinfo[3].encode('utf-8') ).hexdigest()}}) 
                        session.pop('registerpass')
                        return render_template( 'register_password.html', userInfo=userinfo, stage=stage, timezones=setTimezone() )
        
    userinfo = ['','','','','']
    pre_url = request.headers.get("Referer")
    session['pre_url'] = pre_url

    session['registerpass'] = True
    return render_template( 'register_password.html', userInfo=userinfo, stage=stage, timezones=setTimezone() )
 
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
    return render_template( 'admin.html', request=request, user=user_entries, admin=admin_entries, timezones=setTimezone() )

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

@app.route('/set_time',methods=['GET','POST'])
def set_time():
    session['timezone'] = request.form.get('timezone')

    return redirect( request.headers.get("Referer") )

#--------------------
# Error handlers
#--------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    MONGO_URL = init()
    global mongo
    global fs
    mongo = PyMongo(app, uri=MONGO_URL)
    LocalDB.setMongo(mongo)
    fs = gridfs.GridFS(mongo.db)
    app.run(host=args.fhost, port=args.fport, threaded=True)

