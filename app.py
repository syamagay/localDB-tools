##################################
###   Import Module 
##################################
# usersetting
import listset

# use PyROOT
try    : 
    import root
    DOROOT = True
except : 
    DOROOT = False 

import os, pwd, glob, hashlib, datetime, shutil

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

# other function
import func, userfunc, listset
# function for each fe types
import fei4
FE = { "default" : fei4, "FE-I4B" : fei4, "RD53A" : fei4 }

##################
# path/to/save/dir 
USER = pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
PIC_DIR = '{}/upload'.format( USER_DIR )
DAT_DIR = '{}/dat'.format( USER_DIR )
PLOT_DIR = '{}/result'.format( USER_DIR )
THUM_DIR = '{}/result/thum'.format( USER_DIR )
STAT_DIR = '{}/static'.format( USER_DIR )
DIRS = [ USER_DIR, PIC_DIR, DAT_DIR, PLOT_DIR, STAT_DIR, THUM_DIR ] 
if os.path.isdir( USER_DIR ) :
    shutil.rmtree( USER_DIR )
for DIR in DIRS :
    os.mkdir( DIR )
############
# login list
loginlist = [ "logged_in", "user_id", "user_name", "institute", "read", "write", "edit" ]
poplist = [ "signup", "component", "parentId", "code", "runNumber", "runId", "reanalysis", "mapType", "log", "max", "doroot" ]

##############
# call mongodb
app = Flask( __name__ )
app.config["MONGO_URI"] = "mongodb://localhost:"+str(listset.PORT)+"/yarrdb"
mongo = PyMongo( app )
fs = gridfs.GridFS( mongo.db )

######
# auth
app.config["SECRET_KEY"] = os.urandom(24)

####################
# add path to static
import static
app.register_blueprint(static.app)

#############
# for user db
client = MongoClient( host='localhost', port=listset.PORT )
localdb = client['yarrlocal']

##########
# function
def make_dir() :
    if not os.path.isdir( USER_DIR ) :
        for DIR in DIRS :
            os.mkdir( DIR )

def clean_dir( path ) :
    r = glob.glob( path + "/*" )
    for i in r:
        os.remove(i)

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
    if localdb.counter.find({ "type" : "photoNumber" }).count() == 0 :
        localdb.counter.insert({ "type" : "photoNumber", "num" : 1 })
    else :
        localdb.counter.update({ "type" : "photoNumber" }, { '$set' : { "num" : int( localdb.counter.find_one({ "type" : "photoNumber" })['num'] + 1 ) }})
    return int(localdb.counter.find_one({ "type" : "photoNumber" })['num'])

#################
### page function
#################

##########
# top page
@app.route('/', methods=['GET'])
def show_modules_and_chips() :
    make_dir()

    # pop session
    for key in poplist :
        session.pop(key,None)

    clean_dir( STAT_DIR )

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

    return render_template( "toppage.html", modules=modules )

################
# component page
@app.route('/component', methods=['GET', 'POST'])
def show_component() :

    component = {}
    # get from session
    Component = session.get( 'component' )
    ComponentId = request.args.get( 'id' )
    ParentId = session.get( 'parentId' )
    Code = session.get('code')
    #RunNumber = session.get('runNumber')
    RunId = session.get('runId')
    doroot = session.get('doroot', False)

    # this component
    query = { "_id" : ObjectId(ComponentId) }
    thisComponent = mongo.db.component.find_one( query )
    # this module
    query = { "_id" : ObjectId(ParentId) }
    thisModule = mongo.db.component.find_one( query )
    # chips of module
    query = { "parent" : ParentId }
    child_entries = mongo.db.childParentRelation.find( query )

    # fill chip and module information
    components = {}
    components.update({ "this" : ComponentId })
    components.update({ "chips" : [] })
    chips = []
    for child in child_entries :
        if Component == "module" :
            components['chips'].append({ "component" : child['child'] })

        query = { "_id" : ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        component['componentType'] = thisChip['componentType']
        chips.append({ "_id"          : child['child'],
                       "serialNumber" : thisChip["serialNumber"] })
    module = { "_id"           : ParentId,
               "serialNumber"  : thisModule["serialNumber"] }
    
    if component['componentType'] in FE.keys() :
        asic = str(component['componentType'])
    else :
        asic = "default"

    # fill photo display
    photoDisplay = FE[asic].fill_photoDisplay( thisComponent )
    # fill photo index
    photoIndex = FE[asic].fill_photoIndex( thisComponent )
    # show photo
    photos = FE[asic].fill_photos( thisComponent, Code )

    # fill result index
    resultIndex = FE[asic].fill_resultIndex( components ) 
    # fill results 
    results = FE[asic].fill_results( components, RunId )
    # fill roots
    roots = FE[asic].fill_roots( components, RunId, doroot )
    # fill summary ( module )
    summary = FE[asic].fill_summary( thisComponent )

    component.update({ "_id"           : ComponentId,
                       "serialNumber"  : thisComponent['serialNumber'],
                       "module"        : module,
                       "chips"         : chips,
                       "url"           : "show_{}".format(Component),
                       "photoDisplay"  : photoDisplay,
                       "photoIndex"    : photoIndex,
                       "photos"        : photos,
                       "resultIndex"   : resultIndex,
                       "results"       : results,
                       "roots"         : roots,
                       "summary"       : summary })

    return render_template( "component.html", component=component )

#############
# module page
@app.route('/module', methods=['GET','POST'])
def show_module() :
    if not session.get('runId') == request.args.get( 'runId' ) :
        for key in poplist :
            session.pop(key,None)
    session['component'] = "module"

    # get from args
    componentId = request.args.get( 'id' )
    session['parentId'] = request.args.get( 'id' )

    session['code'] = request.args.get( 'code', "" )
    session['runId'] = request.args.get( 'runId' )

    # get from form
    session['reanalysis'] = request.form.get( 'reanalysis', False )
    session['mapType'] = request.form.get( 'mapType' )
    session['log'] = request.form.get('log',False)
    session['max'] = request.form.get('max',0) 

    return redirect( url_for("show_component", id=componentId) )

@app.route('/doroot', methods=['GET', 'POST'])
def doroot() :
    session['doroot'] = request.form.get('doroot',False)

    return redirect( url_for("show_component", id=request.args.get('id')) )

###########
# chip page
@app.route('/chip', methods=['GET', 'POST'])
def show_chip() :
    if not session.get('runId') == request.args.get( 'runId' ) :
        for key in poplist :
            session.pop(key,None)
    session['component'] = "chip"

    # get from args
    componentId = request.args.get( 'id' )
    session['code'] = request.args.get( 'code', "" )
    session['runId'] = request.args.get( 'runId' )

    query = { "child" : componentId }
    session['parentId'] = mongo.db.childParentRelation.find_one( query )['parent']

    return redirect( url_for("show_component", id=componentId) )

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

    forUrl = "show_{}".format( session['component'] )

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
    if session['component'] == "module" :
        session['tagid'] = request.form.get('id')
        session['collection'] = "component"
    if session['component'] == "chip" :
        session['tagid'] = request.form.get('runId')
        session['collection'] = "testRun"
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

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/add_summary', methods=['GET', 'POST'])
def add_summary() :
    componentId = request.args.get( 'id' )
    RunId = session.get( 'runId' )

    if not DOROOT :
        forUrl = "show_{}".format( session['component'] )
        return redirect( url_for(forUrl, id=componentId) )

    session.pop('doroot',None)
    
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

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=componentId) )

@app.route('/show_summary', methods=['GET'])
def show_summary() :
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

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/edit_comment', methods=['GET','POST'])
def edit_comment() :

    if session['component'] == "module" :
        query = { "parent" : request.form.get('id') }
    elif session['component'] == "chip" :
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
        #localdb.user.update( userquery , { '$push' : { 'commentTestRun' : query }})
 
    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), runNumber=request.form.get( 'runNumber' )) )

@app.route('/remove_comment', methods=['GET','POST'])
def remove_comment() :

    if session['component'] == "module" :
        query = { "parent" : request.form.get('id') }
    elif session['component'] == "chip" :
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
        #localdb.user.update( userquery , { '$pull' : { 'commentTestRun' : query }})

    forUrl = "show_{}".format( session['component'] )

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

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/remove_attachment',methods=['GET','POST'])
def remove_attachment() :
    code = request.form.get( 'code' )
    
    fs.delete( ObjectId(code) )
    query = { "_id" : ObjectId(request.form.get('id')) }
    mongo.db.component.update( query, { '$pull' : { "attachments" : { "code" : code }}}) 
    update_mod( "component", query )

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get('id')) )

@app.route('/login',methods=['POST'])
def login() :

    query = { "userName" : request.form['username'] }
    userName = localdb.user.find_one( query )
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
        if localdb.user.find({ "userName" : userinfo[0] }).count() == 1 or localdb.request.find({ "userName" : userinfo[0] }).count() == 1 :
            text = "The username you entered is already in use, please select an alternative."
            stage = "input"
            return render_template( "signup.html", userInfo=userinfo, nametext=text, stage=stage )
        else :
            if stage == "request" :
                userfunc.add_request(userinfo)        
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
    request_entries = localdb.request.find({}, { "userName" : 0, "password" : 0 })
    user_entries = localdb.user.find({ "type" : "user" }, { "userName" : 0, "password" : 0 })
    admin_entries = localdb.user.find({ "type" : "administrator" }, { "userName" : 0, "password" : 0 })
    request = []
    for req in request_entries :
        req.update({ "authority" : 3,
                     "approval"  : "" }) 
        request.append(req) 
    return render_template( "admin.html", request=request, user=user_entries, admin=admin_entries )

@app.route('/remove_user',methods=['GET','POST'])
def remove_user() :
    userid=request.form.get('id')
    userfunc.remove_user( userid )

    return redirect( url_for('admin_page') ) 

@app.route('/add_user',methods=['GET','POST'])
def add_user() :
    user_entries=request.form.getlist('id')
    authority=request.form.getlist('authority')
    approval=request.form.getlist('approval')
    for user in user_entries :
        if approval[user_entries.index( user )] == "approve" :
            query = { "_id" : ObjectId( user ) }
            userinfo = localdb.request.find_one( query )
            userinfo.update({ "authority" : authority[user_entries.index( user )] })
            userfunc.add_user( userinfo ) 
            userfunc.remove_request( user )
        elif approval[user_entries.index(user)] == "deny" :
            userfunc.remove_request( user )

    return redirect( url_for('admin_page') ) 

if __name__ == '__main__':
    app.run(host=listset.IPADDRESS) # change hostID
