#################
### Import Module 
#################
# use PyROOT
try    : import root
except : pass 

import os, pwd, glob, hashlib, datetime

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
import img # binary to dataURI

# other function
import func

##################
# path/to/save/dir 
USER=pwd.getpwuid( os.geteuid() ).pw_name
if not os.path.isdir( '/tmp/{}'.format( USER )) :
    os.mkdir( '/tmp/{}'.format( USER ))
UPLOAD_DIR = '/tmp/{}/upload'.format( USER )
DATA_DIR = '/tmp/{}/data'.format( USER )
RESULT_DIR = '/tmp/{}/result'.format( USER )
STATIC_DIR = '{0}/static/{1}-upload'.format( os.path.dirname(os.path.abspath(__file__)), USER )

scanList = { "selftrigger"   : [( "OccupancyMap-0", "#Hit" ),],
             "noisescan"     : [( "NoiseOccupancy","NoiseOccupancy" ), ( "NoiseMask", "NoiseMask" )],
             "totscan"       : [( "MeanTotMap", "Mean[ToT]" ),         ( "SigmaTotMap", "Sigma[ToT]" )],
             "thresholdscan" : [( "ThresholdMap", "Threshold[e]" ),    ( "NoiseMap", "Noise[e]" )],
             "digitalscan"   : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )],
             "analogscan"    : [( "OccupancyMap", "Occupancy" ),       ( "EnMask", "EnMask" )]}

##############
# call mongodb
app = Flask( __name__ )
app.secret_key = 'secret'
app.config["MONGO_URI"] = "mongodb://localhost:28000/yarrdb"
mongo = PyMongo( app )
fs = gridfs.GridFS( mongo.db )

#############
# for user db
client = MongoClient( host='localhost', port=28000 )
userdb = client['user']

##########
# function
def clean_dir( path ) :
    if not os.path.isdir( path ) :
        os.mkdir( path )
    else:
        r = glob.glob( path + "/*" )
        for i in r:
            os.remove(i)

def fill_imageIndex( thisComponent, imageIndex ) :
    try :
        data_entries = thisComponent['attachments']
        cnt = 1
        for data in data_entries :
            if data['imageType'] == "image" :
                filePath = "{0}/{1}_{2}".format( STATIC_DIR, cnt, data['filename'] )
                f = open( filePath, 'wb' )
                f.write( fs.get(ObjectId(data['code'])).read() )
                f.close()
                url = url_for( 'static', filename='{0}-upload/{1}_{2}'.format( USER, cnt, data['filename'] ))
                imageIndex.append({ "url"      : url,
                                    "code"     : data['code'],
                                    "title"    : data['title'],
                                    "filename" : data['filename'] })
                cnt += 1
    except : 
        pass

def fill_displayIndex( thisComponent, displayIndex ) :
    try :
        data_entries = thisComponent['attachments']
        for scan in scanList :
            displayList = []
            for data in data_entries :
                if scan == data.get( 'filename', "" ).rsplit( '_', 3 )[1]:
                    binary = base64.b64encode( fs.get(ObjectId(data['code'])).read() ).decode()
                    url = img.bin_to_image( data['contentType'], binary )
                    runNumber = data['filename'].rsplit( '_', 3 )[0]
                    mapType   = data['filename'].rsplit( '_', 3 )[2].rsplit( '.', 1 )[0].rsplit( '-', 1 )[0]
                    env_dict = { "hv"    : data.get( 'environment', { "key" : "value" } ).get( 'hv', "" ),
                                 "cool"  : data.get( 'environment', { "key" : "value" } ).get( 'cool', "" ),
                                 "stage" : data.get( 'environment', { "key" : "value" } ).get( 'stage', "" ) }
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
                displayIndex.append({ "testType" : scan,
                                      "display"  : displayList })
    except : 
        pass

def fill_runIndex( thisRun, runIndex=[] ) :
    if not thisRun['runNumber'] in [ runItem.get( 'runNumber', "" ) for runItem in runIndex ] :
        env_dict = { "hv"    : thisRun.get( 'environment', { "key" : "value" } ).get( 'hv', "" ),
                     "cool"  : thisRun.get( 'environment', { "key" : "value" } ).get( 'cool', "" ),
                     "stage" : thisRun.get( 'environment', { "key" : "value" } ).get( 'stage', "" ) }
        runIndex.append({ "_id"         : thisRun['_id'],
                          "runNumber"   : thisRun['runNumber'],
                          "datetime"    : func.setTime(thisRun['date']),
                          "institution" : thisRun['institution'],
                          "environment" : env_dict })
    else:
        env_dict = ""
    return env_dict

def update_mod( collection, query ) :
    mongo.db[collection].update( query, { '$set' : { 'sys.rev' : int( mongo.db[collection].find_one( query )['sys']['rev'] + 1 ), 
                                                     'sys.mts' : datetime.datetime.utcnow() }})

#################
### page function
#################

##########
# top page
@app.route('/', methods=['GET'])
def show_modules_and_chips() :
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

    html = "toppage.html"
    return render_template( html, modules=modules )

#############
# module page
@app.route('/module', methods=['GET','POST'])
def show_module() :
    session['component'] = "module"

    component = {}

    query = { "_id" : ObjectId(request.args.get( 'id' )) }
    thisComponent = mongo.db.component.find_one( query )

    clean_dir( STATIC_DIR )

    imageIndex = []
    fill_imageIndex( thisComponent, imageIndex )
    displayIndex = []
    fill_displayIndex( thisComponent, displayIndex )

    component.update({ "_id"          : request.args.get( 'id' ),
                       "serialNumber" : thisComponent['serialNumber'],
                       "url"          : "analysis_root",
                       "imageIndex"   : imageIndex,
                       "chipIndex"    : [], 
                       "displayIndex" : displayIndex,
                       "scanIndex"    : [],
                       "dataIndex"    : [] })

    chips = []
    query = { "parent" : component['_id'] } 
    child_entries = mongo.db.childParentRelation.find( query ).sort( '$natural', pymongo.ASCENDING )
    for child in child_entries :
        query = { "_id" : ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        chips.append( { "component" : child['child'] } )
        componentType = thisChip['componentType']
        component['chipIndex'].append({ "_id"          : child['child'],
                                        "serialNumber" : thisChip["serialNumber"] })
    module = { "_id"           : request.args.get( 'id' ),
               "serialNumber"  : thisComponent["serialNumber"] }
    component['moduleIndex'] = module
    component['componentType'] = componentType

    for scan in scanList :
        query = { '$or' : chips, "testType" : scan }
        run_entries = mongo.db.componentTestRun.find( query )
        runIndex = []
        for run in run_entries :
            query = { "_id" : ObjectId(run['testRun']) }
            thisRun = mongo.db.testRun.find_one( query )
            env_dict = fill_runIndex( thisRun, runIndex )
        
        if not runIndex == [] :
            component['scanIndex'].append({ "testType" : scan,
                                            "run"      : runIndex })
   
    # redirect from analysis_root
    try :
        runNumber = int( request.args.get( 'run' ) or 0 )
        query = { '$or' : chips , "runNumber" : runNumber }
        thisRun = mongo.db.componentTestRun.find_one( query )
        testType = thisRun.get( 'testType' )
        for mapType in scanList[testType] :
            for i in [ "1", "2" ] :
                max_value = func.readJson( "parameter.json" ) 
                filename = RESULT_DIR + "/" + testType + "/" + str(runNumber) + "_" + mapType[0] + "_{}.png".format(i)
                url = "" 
                if os.path.isfile(filename) :
                    binary_image = open( filename, 'rb' )
                    code_base64 = base64.b64encode(binary_image.read()).decode()
                    binary_image.close()
                    url = img.bin_to_image( 'png', code_base64 ) 
                component['dataIndex'].append({ "testType"  : testType, 
                                                "mapType"   : mapType[0], 
                                                "runNumber" : runNumber, 
                                                "comment"   : "No Root Software",
                                                "path"      : filename, 
                                                "url"       : url, 
                                                "setLog"    : max_value[testType][mapType[0]][1], 
                                                "maxValue"  : max_value[testType][mapType[0]][0] })
    except : 
        pass

    html = "component.html"
    return render_template( html, component=component )

#######################
# analysis using PyROOT 
@app.route('/analysis', methods=['GET','POST'])
def analysis_root() :
    reanalysis = request.form.get( 'reanalysis', "False" )
    module_id = request.args.get( 'id' )
    runNumber = int( request.args.get( 'runNumber' ) or 0 )

    if not reanalysis == "True" :
        clean_dir( DATA_DIR )

    query = { "_id" : ObjectId(module_id) }
    thisComponent = mongo.db.component.find_one( query )
    query = { "parent" : module_id }
    child_entries = mongo.db.childParentRelation.find( query )
    for child in child_entries :
        query = { "component" : child['child'], "runNumber" : runNumber }
        thisScan = mongo.db.componentTestRun.find_one( query )
        query = { "_id" : ObjectId(thisScan['testRun']) }
        thisResult = mongo.db.testRun.find_one( query )
        testType = thisResult['testType']
        if not reanalysis == "True" :
            data_entries = thisResult['attachments']
            for data in data_entries :
                if data['contentType'] == 'dat' :
                    f = open( '{0}/{1}_{2}.dat'.format( DATA_DIR, runNumber, data['filename'].split("_")[1] + "_" + data['filename'].split("_")[2] ), "wb" )
                    f.write( fs.get(ObjectId(data['code']) ).read())
                    f.close()

    mapList = {}
    for mapType in scanList[testType] :
        if reanalysis == "True" and not mapType[0] == request.form.get( 'mapType' ) :
            mapList.update({ mapType[0] : False })
        else :
            mapList.update({ mapType[0] : True })

    try    : root.drawScan( thisComponent['serialNumber'], testType, str(runNumber), bool(request.form.get( 'log', False )), int( request.form.get( 'max' ) or 0 ), mapList )
    except : print( "undo root process" )

    return redirect( url_for( 'show_module', id=module_id, run=runNumber ) )

###########
# chip page
@app.route('/chip_result', methods=['GET','POST'])
def show_chip() :
    session['component'] = "chip"

    component = {}

    query = { "_id" : ObjectId(request.args.get('id')) }
    thisComponent = mongo.db.component.find_one( query )

    imageIndex = []
    fill_imageIndex( thisComponent, imageIndex )

    component.update({ "_id"           : request.args.get( 'id' ), 
                       "serialNumber"  : thisComponent['serialNumber'],
                       "componentType" : thisComponent['componentType'],
                       "url"           : "show_chip",
                       "imageIndex"    : imageIndex,
                       "displayIndex"  : [],
                       "chipIndex"     : [],
                       "scanIndex"     : [],
                       "dataIndex"     : [] }) 

    query = { "child" : component['_id'] }
    parent = mongo.db.childParentRelation.find_one( query )

    chips = []
    query = { "parent" : parent['parent'] } 
    child_entries = mongo.db.childParentRelation.find( query ).sort( '$natural', pymongo.ASCENDING )
    for child in child_entries :
        query = { "_id" : ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        chips.append( { "component" : child['child'] } )
        component['chipIndex'].append({ "_id"           : child['child'],
                                        "serialNumber"  : thisChip["serialNumber"] })
    query = { "_id" : ObjectId(parent['parent']) }
    thisModule = mongo.db.component.find_one( query )
    module = { "_id"           : parent['parent'],
               "serialNumber"  : thisModule["serialNumber"] }
    component['moduleIndex'] = module

    for scan in scanList :
        query = { "component" : component['_id'], "testType" : scan }
        run_entries = mongo.db.componentTestRun.find( query )
        runIndex = []
        displayIndex = []
        for run in run_entries :
            query = { "_id" : ObjectId(run['testRun']) }
            thisRun = mongo.db.testRun.find_one( query )
            env_dict = fill_runIndex( thisRun, runIndex )

            if thisRun['runNumber'] == int( request.args.get( 'runNumber' ) or 0 ) :
                data_entries = thisRun['attachments']
                for data in data_entries :
                    if data['contentType'] == 'pdf' or data['contentType'] == 'png' :
                        binary = base64.b64encode( fs.get( ObjectId(data['code']) ).read() ).decode()
                        url = img.bin_to_image( data['contentType'], binary )
                        component['dataIndex'].append({ "testType"    : thisRun['testType'],
                                                        "runNumber"   : thisRun['runNumber'],
                                                        "runId"       : thisRun['_id'],
                                                        "code"        : data['code'],
                                                        "url"         : url,
                                                        "filename"    : data['filename'].split("_")[2],
                                                        "environment" : env_dict,
                                                        "display"     : data.get('display',"false") })
            display_entries = thisRun['attachments']
            for data in display_entries :
                if data.get( 'display' ) == 'True' :
                    binary = base64.b64encode( fs.get( ObjectId(data['code']) ).read() ).decode()
                    url = img.bin_to_image( data['contentType'], binary )

                    displayIndex.append({ "runNumber"   : thisRun['runNumber'],
                                          "runId"       : thisRun['_id'],
                                          "code"        : data['code'],
                                          "htmlurl"     : "untag_image",
                                          "environment" : env_dict,
                                          "description" : data['description'],
                                          "collection"  : "testRun",
                                          "filename"    : data['filename'].split("_")[2],
                                          "url"         : url })

        if not runIndex == [] :
           component['scanIndex'].append({ "testType" : scan,
                                            "run"      : runIndex })
        if not displayIndex == [] :
            component['displayIndex'].append({ "testType" : scan,
                                               "display"  : displayIndex })


    html = "component.html"
    return render_template( html, component=component )

@app.route('/tag_image', methods=['GET','POST'])
def tag_image() :
    
    query = { "_id" : ObjectId(request.form.get('runId')) }
    data_entries = mongo.db.testRun.find_one( query )['attachments']
    for data in data_entries :
        if data['code'] == request.form.get( 'code' ) :
            if not 'display' in data :
                mongo.db.testRun.update( query, { '$set' : { 'attachments.{}.display'.format( data_entries.index(data) ) : "True" }})
                #update_mod( "testRun", query )
#                mongo.db.testRun.update( query, { '$set' : { 'sys.rev' : int( mongo.db.testRun.find_one( query )['sys']['rev'] + 1 ), 
#                                                             'sys.mts' : datetime.datetime.utcnow() }})

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' ), runId=request.form.get( 'runId' )) )

@app.route('/untag_image', methods=['GET','POST'])
def untag_image() :
    
    query = { "_id" : ObjectId(request.form.get('runId')) }
    data_entries = mongo.db.testRun.find_one( query )['attachments']
    for data in data_entries :
        if data['code'] == request.form.get( 'code' ):
            if 'display' in data :
                mongo.db.testRun.update( query, { '$unset': { 'attachments.{}.display'.format( data_entries.index(data) ) : "True" }})
                #update_mod( "testRun", query )
#                mongo.db.testRun.update( query, { '$set' : { 'sys.rev' : int( mongo.db.testRun.find_one( query )['sys']['rev'] + 1 ), 
#                                                             'sys.mts' : datetime.datetime.utcnow() }})

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
    env_dict = fill_runIndex( thisRun )
 
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
    #update_mod( "component", query )
#    mongo.db.component.update( query, { '$set' : { 'sys.rev' : int( mongo.db.component.find_one( query )['sys']['rev'] + 1 ), 
#                                                   'sys.mts' : datetime.datetime.utcnow() }})
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

        #update_mod( str(col), query )
#        mongo.db.component.update( query, { '$set' : { 'sys.rev' : int( mongo.db.component.find_one( query )['sys']['rev'] + 1 ), 
#                                                       'sys.mts' : datetime.datetime.utcnow() }})

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )


@app.route('/add_attachment', methods=['GET','POST'])
def add_attachment() :

    file = request.files.get( 'file' )
    if file and func.allowed_file( file.filename ) :
        filename = secure_filename( file.filename )
        if not os.path.isdir( UPLOAD_DIR ) :
            os.mkdir( UPLOAD_DIR )
        file.save( os.path.join(UPLOAD_DIR, filename) )

        fileUp = "{0}/{1}".format( UPLOAD_DIR, filename )
        binary_image = open( fileUp, 'rb' )
        title = request.form.get( 'title' )
        description = request.form.get( 'description' )
        if title == "" : title = filename.rsplit( '.', 1 )[0]
        image = fs.put( binary_image.read(), filename=filename )
        binary_image.close()
        
        query = { "_id" : image }
        date = mongo.db.fs.files.find_one( query )['uploadDate']
        query = { "_id" : ObjectId(request.form.get('id')) }
        mongo.db.component.update( query, { '$push' : { "attachments" : { "code"        : str(image),
                                                                          "dateTime"    : date,
                                                                          "title"       : title,
                                                                          "description" : description,
                                                                          "imageType"   : "image",
                                                                          "contentType" : filename.rsplit( '.', 1 )[1],
                                                                          "filename"    : filename }}})
        #update_mod( "component", query )
#        mongo.db.component.update( query, { '$set' : { 'sys.rev' : int( mongo.db.component.find_one( query )['sys']['rev'] + 1 ), 
#                                                       'sys.mts' : datetime.datetime.utcnow() }})

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get( 'id' )) )

@app.route('/remove_attachment',methods=['GET','POST'])
def remove_attachment() :
    code = request.form.get( 'code' )
    
    fs.delete( ObjectId(code) )
    query = { "_id" : ObjectId(request.form.get('id')) }
    mongo.db.component.update( query, { '$pull' : { "attachments" : { "code" : code }}}) 
    #update_mod( "component", query )
#    mongo.db.component.update( query, { '$set' : { 'sys.rev' : int( mongo.db.component.find_one( query )['sys']['rev'] + 1 ), 
#                                                   'sys.mts' : datetime.datetime.utcnow() }})

    forUrl = "show_{}".format( session['component'] )

    return redirect( url_for(forUrl, id=request.form.get('id')) )

@app.route('/login',methods=['POST'])
def login() :

    query = { "userName" : request.form['username'] }
    userName = userdb.user.find_one( query )
    try :
        if hashlib.md5( request.form['password'].encode("utf-8") ).hexdigest() == userName['passWord'] :
            session['logged_in'] = True
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

    return redirect( url_for('show_modules_and_chips') )

if __name__ == '__main__':
    app.run(host='192.168.1.43') # change hostID
