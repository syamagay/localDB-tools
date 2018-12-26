##################################
###   Import Module 
##################################
import os, pwd, glob, hashlib, datetime, shutil, sys, uuid, json
sys.path.append( os.path.dirname(os.path.abspath(__file__)) + "/scripts/src" )

# use Flask scheme
from flask import Flask, request, redirect, url_for, render_template, session, abort

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
from PIL import Image
import io

# use PyROOT
try    : 
    import root
    DOROOT = True
except : 
    DOROOT = False 
import func, listset
from arguments import *   # Pass command line arguments into app.py
# function for each fe types
from AsicTypes import fei4

app = Flask( __name__ )

####################
# add path to static
import static
app.register_blueprint(static.app)

##################
# path/to/save/dir 
USER = pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
PIC_DIR = '{}/upload'.format( USER_DIR )
DAT_DIR = '{}/dat'.format( USER_DIR )
PLOT_DIR = '{}/result'.format( USER_DIR )
THUM_DIR = '{}/result/thum'.format( USER_DIR )
THUMT_DIR = '{}/result/thum_test'.format( USER_DIR )
THUMA_DIR = '{}/thum_after'.format(  PLOT_DIR )
THUMB_DIR = '{}/thum_before'.format( PLOT_DIR )
STAT_DIR = '{}/static'.format( USER_DIR )
JSON_DIR = '{}/json'.format( USER_DIR )
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) + "/scripts"

DIRS = [ PIC_DIR, DAT_DIR, PLOT_DIR, STAT_DIR, THUM_DIR, THUMT_DIR, JSON_DIR, THUMB_DIR, THUMA_DIR ] 
if os.path.isdir( USER_DIR ) :
    shutil.rmtree( USER_DIR )
os.mkdir( USER_DIR )
for DIR in DIRS :
    os.mkdir( DIR )

############
# login list
loginlist = [ "logged_in", "user_id", "user_name", "institute", "read", "write", "edit" ]
poplist = [ "signup", "code", "runId", "stage", "this" ]

########
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
            return ["This url does not belong to the app.".encode()]

app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix='/yarrdb')

##############
# call mongodb
args = getArgs()            # Get command line arguments
if args.username is None:
    url = "mongodb://" + args.host + ":" + str(args.port) 
else:
    url = "mongodb://" + args.username + ":" + args.password + "@" + args.host + ":" + str(args.port) 
print("Connecto to mongoDB server: " + url + "/" + args.db)
mongo = PyMongo( app, uri = url + "/" + args.db )
usermongo = PyMongo( app, uri = url + "/" + args.userdb )
fs = gridfs.GridFS( mongo.db )

############
# secret_key
app.config["SECRET_KEY"] = os.urandom(24)

##########
# function
def make_dir() :
    if not os.path.isdir( USER_DIR ) :
        os.mkdir( USER_DIR )
    for DIR in DIRS :
        if not os.path.isdir( DIR ) :
            os.mkdir( DIR )

def clean_dir( dir_name ) :
    if os.path.isdir( dir_name ) : shutil.rmtree( dir_name )
    os.mkdir( dir_name )

def fill_env( thisComponentTestRun ) :
    env_list = thisComponentTestRun['environments']
    env_dict = { "list" : env_list,
                 "num"  : len(env_list) }
    return env_dict

def update_mod( collection, query ) :
    mongo.db[collection].update( query, 
                                 { '$set' : { 'sys.rev' : int( mongo.db[collection].find_one( query )['sys']['rev'] + 1 ), 
                                              'sys.mts' : datetime.datetime.utcnow() }}, 
                                   multi=True )
def count_photoNum() :
    if usermongo.db.counter.find({ "type" : "photoNumber" }).count() == 0 :
        usermongo.db.counter.insert({ "type" : "photoNumber", "num" : 1 })
    else :
        usermongo.db.counter.update({ "type" : "photoNumber" }, { '$set' : { "num" : int( usermongo.db.counter.find_one({ "type" : "photoNumber" })['num'] + 1 ) }})
    return int(usermongo.db.counter.find_one({ "type" : "photoNumber" })['num'])


#################
### page function
#################

##########
# top page
@app.route('/', methods=['GET'])
def show_modules_and_chips() :

    if session.get( 'uuid' ) :
        dat_dir = DAT_DIR + "/" + str(session.get('uuid'))
        if os.path.isdir( dat_dir ) :
            shutil.rmtree( dat_dir )
        plot_dir = PLOT_DIR+"/"+str(session.get( 'uuid' ))
        if os.path.isdir( plot_dir ) :
            shutil.rmtree( plot_dir )
    else :
        session['uuid'] = str(uuid.uuid4()) 

    make_dir()
    clean_dir( STAT_DIR )

    # pop session
    for key in poplist :
        session.pop(key,None)

    query = { "componentType" : "Module" }
    component_entries = mongo.db.component.find( query )
    modules = {}

    for component in component_entries :
        query = { "parent" : str(component['_id']) }
        child_entries = mongo.db.childParentRelation.find( query )
        chips = []
        componentType = "unknown"
        for child in child_entries :
            query = { "_id" : ObjectId(child['child']) }
            thisChip = mongo.db.component.find_one( query )
            chips.append({ "_id"           : str(thisChip['_id']),
                           "serialNumber"  : thisChip['serialNumber'],
                           "componentType" : thisChip['componentType'],
                           "datetime"      : func.setTime(thisChip['sys']['cts']) }) 
            componentType = thisChip['componentType']
        if not componentType in modules :
            modules.update({ componentType : { "modules" : [], "num" : "" } })
        modules[componentType]["modules"].append({ "_id"          : str(component['_id']),
                                                   "serialNumber" : component['serialNumber'],
                                                   "chips"        : chips })
    for componentType in modules :
        modules[componentType].update({ "num" : len(modules[componentType]["modules"]) })

    module = sorted( modules[componentType]["modules"], key=lambda x:x["serialNumber"], reverse=True)
    modules[componentType]["modules"] = module

    return render_template( "toppage.html", modules=modules )

################
# component page
@app.route('/component', methods=['GET', 'POST'])
def show_component() :

    make_dir()
    session.pop("summaryList",None)

    if not session.get( 'this' ) == request.args.get( 'id' ) : session.pop( 'stage', None )

    session['this']  = request.args.get( 'id' )
    session['code']  = request.args.get( 'code', "" )
    session['runId'] = request.args.get( 'runId' )

    # this component
    query = { "_id" : ObjectId(session['this']) }
    thisComponent = mongo.db.component.find_one( query )

    if thisComponent['componentType'] == "Module" : unit = "module"
    else :                                          unit = "chip"

    # chips and parent
    chips = []
    query = [{ "parent" : session['this'] },{ "child" : session['this'] }]
    child_entries = mongo.db.childParentRelation.find({ '$or' : query })
    for child in child_entries :
        chips.append({ "component" : child['child'] })
        ParentId = child['parent']

    # this module
    query = { "_id" : ObjectId(ParentId) }
    thisModule = mongo.db.component.find_one( query )

    # chips of module
    query = { "parent" : ParentId }
    child_entries = mongo.db.childParentRelation.find( query )

    # fill chip and module information
    component = {}
    component_chips = []
    for child in child_entries :
        query = { "_id" : ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        component['componentType'] = thisChip['componentType']
        component_chips.append({ "_id"          : child['child'],
                                 "serialNumber" : thisChip["serialNumber"] })

    module = { "_id"           : ParentId,
               "serialNumber"  : thisModule["serialNumber"] }
    
    # fill photos
    photoDisplay = fei4.fill_photoDisplay( thisComponent )
    photoIndex   = fei4.fill_photoIndex( thisComponent )
    photos       = fei4.fill_photos( thisComponent, session['code'] )

    # fill results
    resultIndex  = fei4.fill_resultIndex() 
    results      = fei4.fill_results()
    roots        = fei4.fill_roots()

    # fill summary 
    query = { '$or' : chips }
    run_entries = mongo.db.componentTestRun.find( query )
    stages = []
    for run in run_entries :
        stages.append( run.get('stage') )
    stages = list(set(stages))
    summary = fei4.fill_summary( thisComponent, stages )

    component.update({ "_id"           : session['this'],
                       "serialNumber"  : thisComponent['serialNumber'],
                       "module"        : module,
                       "chips"         : component_chips,
                       "unit"          : unit, 
                       "photoDisplay"  : photoDisplay,
                       "photoIndex"    : photoIndex,
                       "photos"        : photos,
                       "resultIndex"   : resultIndex,
                       "results"       : results,
                       "roots"         : roots,
                       "summary"       : summary })

    return render_template( "component.html", component=component )

@app.route('/makehisto', methods=['GET','POST'])
def makehisto() :
    # get from form
    session['rootType']  = request.form.get( 'root' )
    session['mapType']   = request.form.get( 'mapType' )
    session['parameter'] = { "min" : request.form.get('min'), 
                             "max" : request.form.get('max'), 
                             "bin" : request.form.get('bin'), 
                             "log" : request.form.get('log',False) }

    # get from args
    componentId = request.args.get( 'id' )
    runId       = request.args.get( 'runId' )

    return redirect( url_for("show_component", id=componentId, runId=runId) )

############
# tag method
@app.route('/tag', methods=['GET'])
def tag() :
    query = { "_id" : ObjectId(session.get('tagid')) }
    collection = str(session.get('collection'))

    data_entries = mongo.db[collection].find_one( query )['attachments']
    for data in data_entries :
        if data['code'] == request.args.get( 'code' ) :
            if session.get('tag') == "tag" :
                 mongo.db[collection].update( query, { '$set' : { 'attachments.{}.display'.format( data_entries.index(data) ) : True }})
                 update_mod( collection, query )
            elif session.get('tag') == "untag" :
                 mongo.db[collection].update( query, { '$unset' : { 'attachments.{}.display'.format( data_entries.index(data) ) : True }})
                 mongo.db[collection].update( query, { '$set'   : { 'attachments.{}.description'.format( data_entries.index(data) ) : "" }})
                 update_mod( collection, query )
            else :
                 print("can't get tag session")

    forUrl = "show_component"

    session.pop('collection')
    session.pop('tagid')
    session.pop('tag')

    return redirect( url_for(forUrl, id=request.args.get( 'id' )) )

@app.route('/tag_image', methods=['GET','POST'])
def tag_image() :
    session['tagid'] = request.form.get( 'id' )
    session['collection'] = "component"
    session['tag'] = str(request.form.get( 'tag' ))

    return redirect( url_for("tag", id=request.form.get( 'id' ), code=request.form.get( 'code' )) )

@app.route('/tag_result', methods=['GET','POST'])
def tag_result() :
    #if session['component'] == "module" :
    #    session['tagid'] = request.form.get('id')
    #    session['collection'] = "component"
    #if session['component'] == "chip" :
    #    session['tagid'] = request.form.get('runId')
    #    session['collection'] = "testRun"
    session['tag'] = str(request.form.get('tag'))

    return redirect( url_for("tag", id=request.form.get( 'id' ), code=request.form.get('code')) )

##################
# add attachment ? 
@app.route('/add_attachment_result', methods=['GET','POST'])
def add_attachment_result() :
    fileResult = request.form.get( 'path' ) 
    binary_image = open( fileResult, 'rb' )
    runNumber = fileResult.rsplit( '/', 4 )[4].rsplit( '_', 2 )[0]
    mapType = fileResult.rsplit( '/', 4 )[4].rsplit( '_', 2 )[1]
    testType = fileResult.rsplit( '/', 4 )[3]
    filename = "{0}_{1}_{2}.png".format( runNumber, testType, mapType )
    image = fs.put( binary_image.read(), filename=filename )
    binary_image.close()
    
    chips = []
    query = { "parent" : request.form.get( 'id' ) } 
    child_entries = mongo.db.childParentRelation.find( query )
    for child in child_entries :
        chips.append( { "component" : child['child'] } )
    query = { '$or' : chips, "runNumber" : int( runNumber ) }
    query = { "_id" : ObjectId(mongo.db.componentTestRun.find_one( query )['testRun']) }
    thisRun = mongo.db.testRun.find_one( query )
    thisComponentTestRun = mongo.db.componentTestRun.find_one({ "testRun" : str(thisRun['_id']) })
    env_dict = fill_env( thisComponentTestRun )
 
    query = { "_id" : image }
    date = mongo.db.fs.files.find_one( query )['uploadDate']
    query = { "_id" : ObjectId(request.form.get('id')) }
    mongo.db.component.update( query, { '$push' : { "attachments" : { "code"        : str(image),
                                                                      "dateTime"    : date,
                                                                      "title"       : "",
                                                                      "description" : "",
                                                                      "display"     : True,
                                                                      "imageType"   : "result",
                                                                      "contentType" : filename.rsplit( '.', 1 )[1],
                                                                      "filename"    : filename,
                                                                      "environment" : env_dict }}})
    update_mod( "component", query )

    forUrl = "show_component"

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/add_summary_test', methods=['GET','POST'])
def add_summary_test() :

    session.pop( "runId", None )
    session.pop( "code", None )
    session.pop( "stage", None )
    session.pop( "plotList", None )
   
    # get from args
    session['this']  = request.args.get( 'id' ) 

    # get from form
    if not request.form.get( 'stage' ) == session.get( 'stage' ) :
        session['summaryList'] = { "after"  : {},
                                   "before" : {} }
    session['stage'] = request.form.get( 'stage' )

    #if request.form.get('testType') :
        #session['summaryList']['after'].update({ request.form.get('testType') : request.form.get('runId') })

    # chips and parent
    chips = []
    query = [{ "parent" : session['this'] },{ "child" : session['this'] }]
    child_entries = mongo.db.childParentRelation.find({ '$or' : query })
    for child in child_entries :
        chips.append({ "component" : child['child'] })
        ParentId = child['parent']

    # this component
    query = { "_id" : ObjectId(session['this']) }
    thisComponent = mongo.db.component.find_one( query )

    if thisComponent['componentType'] == "Module" : unit = "module"
    else :                                          unit = "chip"

    # this module
    query = { "_id" : ObjectId(ParentId) }
    thisModule = mongo.db.component.find_one( query )

    # chips of module
    query = { "parent" : ParentId }
    child_entries = mongo.db.childParentRelation.find( query )

    # fill chip and module information
    component = {}
    component_chips = []
    for child in child_entries :
        query = { "_id" : ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        component['componentType'] = thisChip['componentType']
        component_chips.append({ "_id"          : child['child'],
                                 "serialNumber" : thisChip["serialNumber"] })
    module = { "_id"           : ParentId,
               "serialNumber"  : thisModule["serialNumber"] }

    query = { '$or' : chips }
    run_entries = mongo.db.componentTestRun.find( query )
    stages = []
    for run in run_entries :
        stages.append( run.get('stage') )
    stages = list(set(stages))

    # fill summary 
    summary = fei4.fill_summary_test( )

    # fill result index 
    resultIndex = fei4.fill_resultIndex()

    component.update({ "_id"           : session['this'],
                       "serialNumber"  : thisComponent['serialNumber'],
                       "module"        : module,
                       "chips"         : component_chips,
                       "unit"          : unit,
                       "summary"       : summary,
                       "stages"        : stages,
                       "resultIndex"   : resultIndex,
                       "stage"         : session['stage'] })

    return render_template( "add_summary.html", component=component )

@app.route('/add_summary', methods=['GET', 'POST'])
def add_summary() :
    componentId = request.args.get( 'id' )
    RunId = session.get( 'runId' )

    if not DOROOT :
        forUrl = "show_component"
        return redirect( url_for(forUrl, id=componentId) )
    
    # serialNumber
    query = { "_id" : ObjectId(componentId) }
    serialNumber = mongo.db.component.find_one( query )['serialNumber']
    # stage
    query = { "testRun" : RunId }
    stage = mongo.db.componentTestRun.find_one( query )['stage']
    # is first creation componentTestRun and TestRun for module
    query = { "component" : componentId, "testRun" : RunId }
    if mongo.db.componentTestRun.find( query ).count() == 0 :
        query = { "_id" : ObjectId(RunId) }
        docs = { "_id"         : 0,
                 "sys"         : 0 }
        moduleTestRun = mongo.db.testRun.find_one( query, docs )
        moduleTestRun.update({ "attachments" : [] })
        moduleTestRun.update({ "sys" : { "rev" : 0,
                                         "cts" : datetime.datetime.utcnow(),
                                         "mts" : datetime.datetime.utcnow() }})
        RunId = str(mongo.db.testRun.insert( moduleTestRun ))
        moduleComponentTestRun = { "component"   : componentId,
                                   "testType"    : moduleTestRun['testType'],
                                   "testRun"     : RunId,
                                   "stage"       : stage,
                                   "runNumber"   : moduleTestRun['runNumber'],
                                   "sys"         : { "rev" : 0,
                                                     "cts" : datetime.datetime.utcnow(),
                                                     "mts" : datetime.datetime.utcnow() }} 
        moduleComponentRunId = mongo.db.componentTestRun.insert( moduleComponentTestRun )
    # add attachments into module TestRun
    query = { "component" : componentId, "testRun" : RunId }
    thisComponentTestRun = mongo.db.componentTestRun.find_one( query )
    query = { "_id" : ObjectId(RunId) }
    thisRun = mongo.db.testRun.find_one( query )
    for mapType in listset.scan[thisRun['testType']] :
        for i in [ "1", "2" ] :
            if i == "1" :
                filename = "{0}_{1}_Dist".format( serialNumber, mapType[0] )
            if i == "2" :
                filename = "{0}_{1}".format( serialNumber, mapType[0] )
            for attachment in mongo.db.testRun.find_one( query )['attachments'] :
                if filename == attachment.get('filename') :
                    fs.delete( ObjectId(attachment.get('code')) )
                    mongo.db.testRun.update( query, { '$pull' : { "attachments" : { "code" : attachment.get('code') }}}) 
            filepath = PLOT_DIR + "/" + thisRun['testType'] + "/" + str(thisRun['runNumber']) + "_" + mapType[0] + "_{}.png".format(i)
            binary_image = open( filepath, 'rb' )
            image = fs.put( binary_image.read(), filename=filename )
            binary_image.close()
            mongo.db.testRun.update( query, { '$push' : { "attachments" : { "code" : str(image),
                                                                            "dateTime" : datetime.datetime.utcnow(),
                                                                            "title" : "title",
                                                                            "description" : "describe",
                                                                            "contentType" : "png",
                                                                            "filename" : filename }}}) 

    # change display bool
    components = [{ "component" : componentId }]
    query = { "parent" : componentId }
    for child in mongo.db.childParentRelation.find( query ) :
        components.append({ "component" : child['child'] })
    query = { '$or' : components, "testType" : thisComponentTestRun['testType'], "stage" : thisComponentTestRun['stage'] }
    runIds = []
    for run in mongo.db.componentTestRun.find( query ) :
        runIds.append({ "_id" : ObjectId(run['testRun']) })
    query = { '$or' : runIds, "display" : True }
    if not mongo.db.testRun.find( query ).count() == 0 :
        update_mod( "testRun", query ) 
        mongo.db.testRun.update( query, { '$set' : { "display" : False }}, multi=True )
    query.pop("display",None)
    query.update({ "runNumber" : thisRun['runNumber'], "institution" : thisRun['institution'], "userIdentity" : thisRun['userIdentity'] })
    update_mod( "testRun", query ) 
    mongo.db.testRun.update( query, { '$set' : { "display" : True }}, multi=True )

    forUrl = "show_component"

    return redirect( url_for(forUrl, id=componentId) )

@app.route('/show_summary', methods=['GET'])
def show_summary() :
    # get from args
    code = request.args.get('code')
    scan = request.args.get('scan')
    stage = request.args.get('stage')

    query = { "_id" : ObjectId(code) }
    data = mongo.db.fs.files.find_one( query )
    if not "png" in data['filename'] : 
        filePath = "{0}/{1}_{2}_{3}.png".format( PLOT_DIR, stage, scan, data['filename'] )
    else :
        filePath = "{0}/{1}_{2}_{3}".format( PLOT_DIR, stage, scan, data['filename'] )
    binary = fs.get(ObjectId(code)).read()
    image_bin = io.BytesIO( binary )
    image = Image.open( image_bin )
    image.save( filePath )
    if not "png" in data['filename'] : 
        url = url_for( 'result.static', filename='{0}_{1}_{2}.png'.format( stage, scan, data['filename'] ))
    else :
        url = url_for( 'result.static', filename='{0}_{1}_{2}'.format( stage, scan, data['filename'] ))
 
    return redirect( url )

@app.route('/show_summary_test', methods=['GET'])
def show_summary_test() :
    # get from args
    runId = request.args.get( 'runId' )
    histo = request.args.get( 'histo' )
    mapType = request.args.get( 'mapType' )

    query = { "_id" : ObjectId(runId) }
    thisRun = mongo.db.testRun.find_one( query )

    fei4.make_plot( runId )

    url = url_for( 'result.static', filename='{0}/{1}_{2}_{3}.png'.format( session.get('uuid'), str(thisRun['testType']), mapType, histo ))
 
    return redirect( url )

@app.route('/edit_description', methods=['GET','POST'])
def edit_description() :

    col = request.form.get('collection')
    if col == "testRun" : 
        query = { "_id" : ObjectId(request.form.get('runId')) }
    elif col == "component" :
        query = { "_id" : ObjectId(request.form.get('id')) }
    else :
        return render_template( "error.html", txt="something error" )
    data_entries = mongo.db[ str(col) ].find_one( query )['attachments']
    for data in data_entries :
        if data['code'] == request.form.get( 'code' ) :
            if 'display' in data :
                mongo.db[ str(col) ].update( query, { '$set' : { 'attachments.{}.description'.format( data_entries.index(data) ) : request.form.get('description') }})

                update_mod( str(col), query )

    forUrl = "show_component"

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/edit_comment', methods=['GET','POST'])
def edit_comment() :

    query = { "_id" : ObjectId(request.form.get( 'id' ))}
    thisComponent = mongo.db.component.find_one( query )

    if thisComponent['componentType'] == "Module" :
        query = { "parent" : request.form.get('id') }
    else :
        query = { "child" : request.form.get('id') }
        parentId = mongo.db.childParentRelation.find_one( query )['parent']
        query = { "parent" : parentId }

    child_entries = mongo.db.childParentRelation.find( query )
    component_chips = []
    for child in child_entries :
        component_chips.append({ "component" : child['child'] })

    query = { '$or' : component_chips, "runNumber" : int(request.form.get( 'runNumber' )) }
    run_entries = mongo.db.componentTestRun.find( query )
    for run in run_entries :
        query = { "_id" : ObjectId(run['testRun']) }
        comment_entries = mongo.db.testRun.find_one( query )['comments']
        if session['user_name'] in [ comment.get('user') for comment in comment_entries ] :
            mongo.db.testRun.update( query, { '$set' : { 'comments.{}.comment'.format( comment_entries.index(comment) ) : request.form.get('text') } } )
            mongo.db.testRun.update( query, { '$set' : { 'comments.{}.datetime'.format( comment_entries.index(comment) ) : datetime.datetime.utcnow() } } )
        elif comment_entries == {} :
            mongo.db.testRun.update( query, { '$set' : { 'comments' : [{ "user"      : session['user_name'],
                                                                         "userid"    : session['user_id'],
                                                                         "comment"   : request.form.get('text'), 
                                                                         "datetime"  : datetime.datetime.utcnow(), 
                                                                         "institute" : session['institute'] }] }} )
        else :
            mongo.db.testRun.update( query, { '$push' : { 'comments' : { "user"      : session['user_name'],
                                                                         "userid"    : session['user_id'],
                                                                         "comment"   : request.form.get('text'), 
                                                                         "datetime"  : datetime.datetime.utcnow(), 
                                                                         "institute" : session['institute'] } }} )
        update_mod( "testRun", query )
        #userquery = { "userName" : session['user_name'] }
        #usermongo.db.user.update( userquery , { '$push' : { 'commentTestRun' : query }})
 
    forUrl = "show_component"

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), runNumber=request.form.get( 'runNumber' )) )

@app.route('/remove_comment', methods=['GET','POST'])
def remove_comment() :

    query = { "_id" : ObjectId(request.form.get( 'id' ))}
    thisComponent = mongo.db.component.find_one( query )

    if thisComponent['componentType'] == "Module" :
        query = { "parent" : request.form.get('id') }
    else :
        query = { "child" : request.form.get('id') }
        parentId = mongo.db.childParentRelation.find_one( query )['parent']
        query = { "parent" : parentId }

    child_entries = mongo.db.childParentRelation.find( query )
    component_chips = []
    for child in child_entries :
        component_chips.append({ "component" : child['child'] })

    query = { '$or' : component_chips, "runNumber" : int(request.form.get( 'runNumber' )) }

    run_entries = mongo.db.componentTestRun.find( query )
    for run in run_entries :
        query = { "_id" : ObjectId(run['testRun']) }
        mongo.db.testRun.update( query, { '$pull' : { 'comments' : { "user" : request.form.get( 'user' ) }}} )
        update_mod( "testRun", query )
        #userquery = { "userName" : request.form.get('user') }
        #usermongo.db.user.update( userquery , { '$pull' : { 'commentTestRun' : query }})

    forUrl = "show_component"

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), runNumber=request.form.get( 'runNumber' )) )

@app.route('/add_attachment', methods=['GET','POST'])
def add_attachment() :

    file = request.files.get( 'file' )
    if file and func.allowed_file( file.filename ) :
        filename = secure_filename( file.filename )
        if not os.path.isdir( PIC_DIR ) :
            os.mkdir( PIC_DIR )
        file.save( os.path.join(PIC_DIR, filename) )

        fileUp = "{0}/{1}".format( PIC_DIR, filename )
        binary_image = open( fileUp, 'rb' )
        description = request.form.get( 'description' )
        stage = request.form.get( 'stage' )
        image = fs.put( binary_image.read(), filename=filename )
        binary_image.close()
        
        query = { "_id" : image }
        date = mongo.db.fs.files.find_one( query )['uploadDate']
        query = { "_id" : ObjectId(request.form.get('id')) }
        mongo.db.component.update( query, { '$push' : { "attachments" : { "code"        : str(image),
                                                                          "dateTime"    : date,
                                                                          "title"       : "title",
                                                                          "description" : description,
                                                                          "imageType"   : "image",
                                                                          "stage"       : stage,
                                                                          "photoNumber" : count_photoNum(),
                                                                          "contentType" : filename.rsplit( '.', 1 )[1],
                                                                          "filename"    : filename }}})
        update_mod( "component", query )

    forUrl = "show_component"

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/remove_attachment',methods=['GET','POST'])
def remove_attachment() :
    code = request.form.get( 'code' )
    
    fs.delete( ObjectId(code) )
    query = { "_id" : ObjectId(request.form.get('id')) }
    mongo.db.component.update( query, { '$pull' : { "attachments" : { "code" : code }}}) 
    update_mod( "component", query )

    forUrl = "show_component"

    return redirect( url_for(forUrl, id=request.form.get('id')) )

@app.route('/login',methods=['POST'])
def login() :

    query = { "userName" : request.form['username'] }
    userName = usermongo.db.user.find_one( query )
    try :
        if hashlib.md5( request.form['password'].encode("utf-8") ).hexdigest() == userName['passWord'] :
            session['logged_in'] = True
            session['user_id'] = str(userName['_id'])
            session['user_name'] = userName['userName']
            session['institute'] = userName['institute']
            session['read'] = userName['authority']%2
            session['write'] = int(userName['authority']/2)%2
            session['edit'] = int(userName['authority']/4)%2
        else :
            txt = "not match password"
            return render_template( "error.html", txt=txt )
    except :
        txt = "not found user"
        return render_template( "error.html", txt=txt )
    return redirect( url_for('show_modules_and_chips') )

@app.route('/logout',methods=['GET','POST'])
def logout() :
    session['logged_in'] = False
    session['user_id'] = ""
    session['user_name'] = ""
    session['institute'] = "" 
    session['read'] = 1
    session['write'] = 0
    session['edit'] = 0

    return redirect( url_for('show_modules_and_chips') )

@app.route('/signup',methods=['GET','POST'])
def signup() :
    stage = request.form.get('stage', "input")
    if session['signup'] :
        userinfo = request.form.getlist('userinfo')
        if not userinfo[5] == userinfo[6] :
            text = "Please make sure your passwords match"
            stage = "input"
            return render_template( "signup.html", userInfo=userinfo, passtext=text, stage=stage )
        if usermongo.db.user.find({ "userName" : userinfo[0] }).count() == 1 or usermongo.db.request.find({ "userName" : userinfo[0] }).count() == 1 :
            text = "The username you entered is already in use, please select an alternative."
            stage = "input"
            return render_template( "signup.html", userInfo=userinfo, nametext=text, stage=stage )
        else :
            if stage == "request" :
                func.add_request(userinfo)        
                userinfo = ["","","","","","",""]
                session['signup'] = False
                return render_template( "signup.html", userInfo=userinfo, stage=stage )
            else :
                return render_template( "signup.html", userInfo=userinfo, stage=stage )
        
    userinfo = ["","","","","","",""]
    #stage = "input"
    session['signup'] = True
    return render_template( "signup.html", userInfo=userinfo, stage=stage )

@app.route('/admin',methods=['GET','POST'])
def admin_page() :
    request_entries = usermongo.db.request.find({}, { "userName" : 0, "password" : 0 })
    user_entries = usermongo.db.user.find({ "type" : "user" }, { "userName" : 0, "password" : 0 })
    admin_entries = usermongo.db.user.find({ "type" : "administrator" }, { "userName" : 0, "password" : 0 })
    request = []
    for req in request_entries :
        req.update({ "authority" : 3,
                     "approval"  : "" }) 
        request.append(req) 
    return render_template( "admin.html", request=request, user=user_entries, admin=admin_entries )

@app.route('/remove_user',methods=['GET','POST'])
def remove_user() :
    userid=request.form.get('id')
    func.remove_user( userid )

    return redirect( url_for('admin_page') ) 

@app.route('/add_user',methods=['GET','POST'])
def add_user() :
    user_entries=request.form.getlist('id')
    authority=request.form.getlist('authority')
    approval=request.form.getlist('approval')
    for user in user_entries :
        if approval[user_entries.index( user )] == "approve" :
            query = { "_id" : ObjectId( user ) }
            userinfo = usermongo.db.request.find_one( query )
            userinfo.update({ "authority" : authority[user_entries.index( user )] })
            func.add_user( userinfo ) 
            func.remove_request( user )
        elif approval[user_entries.index(user)] == "deny" :
            func.remove_request( user )

    return redirect( url_for('admin_page') ) 

if __name__ == '__main__':
    app.run(host=args.fhost, port=args.fport)
