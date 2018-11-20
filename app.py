##################################
###   Import Module 
##################################
# use PyROOT
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
# function for each fe types
import fei4
FE = { "FE-I4B" : fei4 }

##################
# path/to/save/dir 
USER = pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) 
PIC_DIR = '{}/upload'.format( USER_DIR )
DAT_DIR = '{}/dat'.format( USER_DIR )
PLOT_DIR = '{}/result'.format( USER_DIR )
STAT_DIR = '{0}/static/{1}-upload'.format( os.path.dirname(os.path.abspath(__file__)), USER )
DIRS = [ USER_DIR, PIC_DIR, DAT_DIR, PLOT_DIR ] 
if os.path.isdir( USER_DIR ) :
    shutil.rmtree( USER_DIR )
for DIR in DIRS :
    os.mkdir( DIR )

scanList = { "selftrigger"   : [( "OccupancyMap-0", "#Hit" ),],
             "noisescan"     : [( "NoiseOccupancy","NoiseOccupancy" ), ( "NoiseMask", "NoiseMask" )],
             "totscan"       : [( "MeanTotMap", "Mean[ToT]" ),         ( "SigmaTotMap", "Sigma[ToT]" )],
             "thresholdscan" : [( "ThresholdMap", "Threshold[e]" ),    ( "NoiseMap", "Noise[e]" )],
             "digitalscan"   : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )],
             "analogscan"    : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )]}

##############
# call mongodb
app = Flask( __name__ )
app.config["MONGO_URI"] = "mongodb://localhost:28000/yarrdb"
mongo = PyMongo( app )
fs = gridfs.GridFS( mongo.db )

######
# auth
app.config["SECRET_KEY"] = os.urandom(24)
auth = HTTPDigestAuth()

#############
# for user db
client = MongoClient( host='localhost', port=28000 )
localdb = client['yarrlocal']

##########
# function
def clean_dir( path ) :
    r = glob.glob( path + "/*" )
    for i in r:
        os.remove(i)

def fill_env( thisRun ) :
    env_dict = { "hv"    : thisRun.get( 'environment', { "key" : "value" } ).get( 'hv', "" ),
                 "cool"  : thisRun.get( 'environment', { "key" : "value" } ).get( 'cool', "" ),
                 "stage" : thisRun.get( 'environment', { "key" : "value" } ).get( 'stage', "" ) }
    return env_dict

def update_mod( collection, query ) :
    mongo.db[collection].update( query, { '$set' : { 'sys.rev' : int( mongo.db[collection].find_one( query )['sys']['rev'] + 1 ), 
                                                     'sys.mts' : datetime.datetime.utcnow() }})
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
    session['signup'] = False
    clean_dir( STAT_DIR )

    query = { "componentType" : "Module" }
    component_entries = mongo.db.component.find( query )
    modules = []

    for component in component_entries :
        query = { "parent" : str(component['_id']) }
        child_entries = mongo.db.childParentRelation.find( query )
        chips = []
        for child in child_entries :
            query = { "_id" : ObjectId(child['child']) }
            thisChip = mongo.db.component.find_one( query )
            chips.append({ "_id"           : str(thisChip['_id']),
                           "serialNumber"  : thisChip['serialNumber'],
                           "componentType" : thisChip['componentType'],
                           "datetime"      : func.setTime(thisChip['sys']['cts']) }) 
        modules.append({ "_id"          : str(component['_id']),
                         "serialNumber" : component['serialNumber'],
                         "chips"        : chips })

    return render_template( "toppage.html", modules=modules )

#############
# module page
@app.route('/module', methods=['GET','POST'])
def show_module() :
    session['component'] = "module"

    component = {}

    query = { "_id" : ObjectId(request.args.get( 'id' )) }
    thisComponent = mongo.db.component.find_one( query )

    # fill chip and module information
    component_chips = []
    chips = []
    query = { "parent" : str(thisComponent['_id']) } 
    child_entries = mongo.db.childParentRelation.find( query )
    for child in child_entries :
        component_chips.append({ "component" : child['child'] })

        query = { "_id" : ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        component['componentType'] = thisChip['componentType']
        chips.append({ "_id"          : child['child'],
                       "serialNumber" : thisChip["serialNumber"] })
    module = { "_id"           : request.args.get( 'id' ),
               "serialNumber"  : thisComponent["serialNumber"] }

    # fill photo display
    photoDisplay = FE[str(component['componentType'])].fill_photoDisplay( thisComponent )
    # fill photo index
    photoIndex = FE[str(component['componentType'])].fill_photoIndex( thisComponent )
    # show photo
    photos = FE[str(component['componentType'])].fill_photos( thisComponent, request.args.get('code',"") )

    # fill result display 
    resultDisplay = FE[str(component['componentType'])].fill_resultDisplay( thisComponent )
    # fill result index
    resultIndex = FE[str(component['componentType'])].fill_resultIndex( component_chips ) 
    # fill results 
    results = FE[str(component['componentType'])].fill_results( component_chips, int(request.args.get('runNumber') or 0) )

    component.update({ "_id"           : request.args.get( 'id' ),
                       "serialNumber"  : thisComponent['serialNumber'],
                       "module"        : module,
                       "chips"         : chips,
                       "url"           : "show_module",
                       "photoDisplay"  : photoDisplay,
                       "photoIndex"    : photoIndex,
                       "photos"        : photos,
                       "resultDisplay" : resultDisplay,
                       "resultIndex"   : resultIndex,
                       "results"       : results })

    return render_template( "component.html", component=component )

###########
# chip page
@app.route('/chip_result', methods=['GET','POST'])
def show_chip() :
    session['component'] = "chip"

    component = {}

    query = { "_id" : ObjectId(request.args.get('id')) }
    thisComponent = mongo.db.component.find_one( query )

    # fill chip and module information
    query = { "child" : request.args.get('id') }
    parent = mongo.db.childParentRelation.find_one( query )
    query = { "parent" : parent['parent'] } 
    child_entries = mongo.db.childParentRelation.find( query )
    component_chips = []
    chips = []
    for child in child_entries :
        component_chips.append({ "component" : child['child'] })

        query = { "_id" : ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        component['componentType'] = thisChip['componentType']
        chips.append({ "_id"          : child['child'],
                       "serialNumber" : thisChip["serialNumber"] })
    query = { "_id" : ObjectId(parent['parent']) }
    thisModule = mongo.db.component.find_one( query )
    module = { "_id"           : parent['parent'],
               "serialNumber"  : thisModule["serialNumber"] }

    # fill photo display
    photoDisplay = FE[str(component['componentType'])].fill_photoDisplay( thisComponent )
    # fill photo index
    photoIndex = FE[str(component['componentType'])].fill_photoIndex( thisComponent )
    # show photo
    photos = FE[str(component['componentType'])].fill_photos( thisComponent, request.args.get('code',"") )

    # fill result display 
    resultDisplay = FE[str(component['componentType'])].fill_resultDisplay( thisComponent )
    # fill result index
    resultIndex = FE[str(component['componentType'])].fill_resultIndex( request.args.get( 'id' ) ) 
    # fill results
    results = FE[str(component['componentType'])].fill_results( request.args.get( 'id' ), int(request.args.get('runNumber') or 0) )

    component.update({ "_id"           : request.args.get( 'id' ),
                       "serialNumber"  : thisComponent['serialNumber'],
                       "componentType" : thisComponent['componentType'],
                       "module"        : module,
                       "chips"         : chips,
                       "url"           : "show_chip",
                       "photoDisplay"  : photoDisplay,
                       "photoIndex"    : photoIndex,
                       "photos"        : photos,
                       "resultDisplay" : resultDisplay,
                       "resultIndex"   : resultIndex,
                       "results"       : results })

    return render_template( "component.html", component=component )

@app.route('/tag_image', methods=['GET','POST'])
def tag_image() :
    query = { "_id" : ObjectId(request.form.get('id')) }
    data_entries = mongo.db.component.find_one( query )['attachments']
    for data in data_entries :
        if data['code'] == request.form.get( 'code' ) :
            if not 'display' in data :
                mongo.db.component.update( query, { '$set' : { 'attachments.{}.display'.format( data_entries.index(data) ) : "True" }})
                update_mod( "component", query )

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), code=request.form.get( 'code' )) )

@app.route('/untag_image', methods=['GET','POST'])
def untag_image() :
    
    query = { "_id" : ObjectId(request.form.get('id')) }
    data_entries = mongo.db.component.find_one( query )['attachments']
    for data in data_entries :
        if data['code'] == request.form.get( 'code' ):
            if 'display' in data :
                mongo.db.component.update( query, { '$unset': { 'attachments.{}.display'.format( data_entries.index(data) ) : "True" }})
                mongo.db.component.update( query, { '$set': { 'attachments.{}.description'.format( data_entries.index(data) ) : "" }})
                update_mod( "component", query )

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), code=request.form.get( 'code' )) )

@app.route('/tag_result', methods=['GET','POST'])
def tag_result() :
    
    query = { "_id" : ObjectId(request.form.get('runId')) }
    data_entries = mongo.db.testRun.find_one( query )['attachments']
    for data in data_entries :
        if data['code'] == request.form.get( 'code' ) :
            if not 'display' in data :
                mongo.db.testRun.update( query, { '$set' : { 'attachments.{}.display'.format( data_entries.index(data) ) : "True" }})
                update_mod( "testRun", query )

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), runId=request.form.get( 'runId' )) )

@app.route('/untag_result', methods=['GET','POST'])
def untag_result() :
    
    query = { "_id" : ObjectId(request.form.get('runId')) }
    data_entries = mongo.db.testRun.find_one( query )['attachments']
    for data in data_entries :
        if data['code'] == request.form.get( 'code' ):
            if 'display' in data :
                mongo.db.testRun.update( query, { '$unset': { 'attachments.{}.display'.format( data_entries.index(data) ) : "True" }})
                mongo.db.testRun.update( query, { '$set': { 'attachments.{}.description'.format( data_entries.index(data) ) : "" }})
                update_mod( "testRun", query )

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), runId=request.form.get( 'runId' )) )

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
    env_dict = fill_env( thisRun )
 
    query = { "_id" : image }
    date = mongo.db.fs.files.find_one( query )['uploadDate']
    query = { "_id" : ObjectId(request.form.get('id')) }
    mongo.db.component.update( query, { '$push' : { "attachments" : { "code"        : str(image),
                                                                      "dateTime"    : date,
                                                                      "title"       : "",
                                                                      "description" : "",
                                                                      "display"     : "True",
                                                                      "imageType"   : "result",
                                                                      "contentType" : filename.rsplit( '.', 1 )[1],
                                                                      "filename"    : filename,
                                                                      "environment" : env_dict }}})
    update_mod( "component", query )

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

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
            session['user_name'] = userName['userName']
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
    session['user_name'] = ""
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

@auth.get_password
def get_pw(username) :
    users = { "admin" : "tEstpAss" } 
    if username in users :
        return users.get(username)
    return redirect( url_for('show_modules_and_chips') ) 

@app.route('/admin',methods=['GET','POST'])
@auth.login_required
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
    app.run(host='192.168.1.43') # change hostID
