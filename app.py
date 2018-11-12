try    : import root
except : pass 

import pymongo, img, base64, func, gridfs
import os, glob, getpass, hashlib
import datetime

from flask import Flask, request, redirect, url_for, render_template, session, abort
from flask_pymongo import PyMongo
from bson.objectid import ObjectId 
from bson.binary import BINARY_SUBTYPE
from werkzeug import secure_filename
from pymongo import MongoClient

scanList = { "selftrigger"   : [("OccupancyMap-0", "#Hit"),],
             "noisescan"     : [("NoiseOccupancy","NoiseOccupancy"), ("NoiseMask", "NoiseMask")],
             "totscan"       : [("MeanTotMap", "Mean[ToT]"),         ("SigmaTotMap", "Sigma[ToT]")],
             "thresholdscan" : [("ThresholdMap", "Threshold[e]"),    ("NoiseMap", "Noise[e]")],
             "digitalscan"   : [("OccupancyMap", "Occupancy"),       ("EnMask", "EnMask")],
             "analogscan"    : [("OccupancyMap", "Occupancy"),       ("EnMask", "EnMask")]}

if not os.path.isdir('/tmp/{}'.format(os.getlogin())):
    os.mkdir('/tmp/{}'.format(os.getlogin()))

# path/to/save/directory
UPLOAD_FOLDER = '/tmp/{}/upload'.format(os.getlogin())
DATA_FOLDER = '/tmp/{}/data'.format(os.getlogin())
RESULT_FOLDER = '/tmp/{}/result'.format(os.getlogin())

# call mongodb
app = Flask(__name__)
app.secret_key = 'secret'
app.config["MONGO_URI"] = "mongodb://localhost:28000/yarrdb"
mongo = PyMongo(app)

# for user db
client = MongoClient(host='localhost', port=28000)
userdb = client['user']

# function
def clean_dir(path):
    if not os.path.isdir(path):
        os.mkdir(path)
    else:
        r = glob.glob(path+"/*")
        for i in r:
            os.remove(i)

def tell_admin(html):
    if session.get('logged_in') : return 'admin_' + html
    else                        : return html

def fill_imageIndex(thisComponent, imageIndex):
    try:
        dataPath = "./static/upload"
        data_entries = thisComponent['attachments']
        cnt = 1
        for data in data_entries:
            if data['imageType'] == "image":
                fs = gridfs.GridFS( mongo.db )
                filePath = "{0}/{1}_{2}".format(dataPath, cnt, data['filename'])
                f = open(filePath, 'wb')
                f.write(fs.get(ObjectId(data['code'])).read())
                f.close()
                imageIndex.append({ "url"      : filePath,
                                    "code"     : data['code'],
                                    "title"    : data['title'],
                                    "filename" : data['filename'] })
                cnt += 1
    except: 
        pass

def fill_displayIndex(thisComponent, displayIndex):
    try:
        dataPath = "./static/upload"
        data_entries = thisComponent['attachments']
        for scan in scanList:
            displayList = []
            for data in data_entries:
                if scan == data.get('filename',"").rsplit('_',3)[1]:
                    query = { "files_id" : ObjectId(data['code']) }
                    binary = mongo.db.fs.chunks.find_one(query)
                    byte = base64.b64encode(binary['data']).decode()
                    url = img.bin_to_image(data['contentType'],byte)
                    runNumber = data['filename'].rsplit('_',3)[0]
                    mapType   = data['filename'].rsplit('_',3)[2].rsplit('.',1)[0].rsplit('-',1)[0]
                    displayList.append({ "url"      : url,
                                         "runNumber": runNumber,
                                         "runId"    : "",
                                         "code"     : data['code'],
                                         "htmlurl"  : "remove_attachment",
                                         "filename" : mapType })
            if not displayList == []:
                displayIndex.append({ "testType" : scan,
                                      "display"  : displayList })
    except: 
        pass


def fill_runIndex(thisRun, runIndex):
    if not thisRun['runNumber'] in [runItem.get('runNumber') for runItem in runIndex]:
        env_dict = { "hv"    : thisRun.get('environment',{"key":"value"}).get('hv',""),
                     "cool"  : thisRun.get('environment',{"key":"value"}).get('cool',""),
                     "stage" : thisRun.get('environment',{"key":"value"}).get('stage',"") }
        runIndex.append({ "_id"         : thisRun['_id'],
                          "runNumber"   : thisRun['runNumber'],
                          "datetime"    : func.setTime(thisRun['date']),
                          "institution" : thisRun['institution'],
                          "environment" : env_dict })
    else:
        env_dict = ""
    return env_dict

### top page
@app.route('/', methods=['GET'])
def show_modules_and_chips():
    query = { "componentType" : "Module" }
    component = mongo.db.component.find(query)
    modules = []
    module_entries = []
    for row in component:
        module_entries.append({ "_id"          : row['_id'],
                                "serialNumber" : row['serialNumber'], 
                                "datetime"     : func.setTime(row['sys']['cts']) })

    for module_entry in module_entries:
        query = {"parent": str(module_entry['_id'])}
        cprelation = mongo.db.childParentRelation.find(query)
        child_entries = []
        for row in cprelation:
            child_entries.append({ "child"    : row['child'],
                                   "datetime" : func.setTime(row['sys']['cts']) })

        chips = []
        for child_entry in child_entries:
            query = {"_id": ObjectId(child_entry['child'])}
            chip_entry = mongo.db.component.find_one(query) # Find child component
            chips.append({ "_id"           : str(chip_entry["_id"]),
                           "serialNumber"  : chip_entry["serialNumber"],
                           "number"        : chip_entry["serialNumber"].split("_")[1],
                           "componentType" : chip_entry["componentType"],
                           "datetime"      : func.setTime(chip_entry['sys']['cts']) })

        modules.append({ "_id"          : str(module_entry["_id"]),
                         "serialNumber" : module_entry["serialNumber"],
                         "chips"        : chips })

    html = tell_admin("toppage.html")
    return render_template(html, modules=modules)

###########################################
############### module page ###############
###########################################
@app.route('/module', methods=['GET','POST'])
def show_module():
    component = {}

    query = { "_id" : ObjectId(request.args.get('id')) }
    thisComponent = mongo.db.component.find_one(query)

    dataPath = "./static/upload"
    clean_dir(dataPath)

    imageIndex = []
    fill_imageIndex(thisComponent, imageIndex)
    displayIndex = []
    fill_displayIndex(thisComponent, displayIndex)

    component.update({ "_id"          : request.args.get('id'),
                       "serialNumber" : thisComponent['serialNumber'],
                       "url"          : "analysis_root",
                       "imageIndex"   : imageIndex,
                       "type"         : "module",
                       "chipIndex"    : [], 
                       "displayIndex" : displayIndex,
                       "scanIndex"    : [],
                       "dataIndex"    : [] })

    chips = []
    query = { "parent" : component['_id'] } 
    child_entries = mongo.db.childParentRelation.find(query).sort('$natural', pymongo.ASCENDING)
    for child in child_entries:
        query = { "_id" : ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one(query)
        chips.append({ "component" : child['child'] })
        component['chipIndex'].append({ "_id"           : ObjectId(child['child']),
                                        "number"        : thisChip["serialNumber"].split("_")[1],
                                        "chip"          : thisChip['serialNumber'],
                                        "componentType" : thisChip['componentType'] })

    for scan in scanList:
        query = { '$or' : chips, "testType" : scan }
        run_entries = mongo.db.componentTestRun.find(query)
        runIndex = []
        for run in run_entries:
            query = { "_id" : ObjectId(run['testRun']) }
            thisRun = mongo.db.testRun.find_one(query)
            env_dict = fill_runIndex(thisRun, runIndex)
        
        if not runIndex == []:
            component['scanIndex'].append({ "testType" : scan,
                                            "run"      : runIndex })
   
    # redirect from analysis_root
    try:
        runNumber = int(request.args.get('run') or 0)
        query = { '$or' : chips , "runNumber" : runNumber }
        thisRun = mongo.db.componentTestRun.find_one(query)
        testType = thisRun.get('testType')
        for mapType in scanList[testType]:
            for i in [ "1", "2" ]:
                max_value = func.readJson("parameter.json") 
                filename = RESULT_FOLDER + "/" + testType + "/" + str(runNumber) + "_" + mapType[0] + "_{}.png".format(i)
                print(filename)
                url = "" 
                if os.path.isfile(filename):
                    binary_image = open(filename,'rb')
                    code_base64 = base64.b64encode(binary_image.read()).decode()
                    binary_image.close()
                    url = img.bin_to_image('png',code_base64)              
                component['dataIndex'].append({ "testType"  : testType, 
                                                "mapType"   : mapType[0], 
                                                "runNumber" : runNumber, 
                                                "comment"   : "No Root Software",
                                                "path"      : filename, 
                                                "url"       : url, 
                                                "setLog"    : max_value[testType][mapType[0]][1], 
                                                "maxValue"  : max_value[testType][mapType[0]][0] })
    except: 
        component['dataIndex'].append({"test":"test"})

    html = tell_admin("module.html")
    return render_template(html, component=component)

###########################################
######### analysis using PyROOT ###########
###########################################
@app.route('/analysis', methods=['GET','POST'])
def analysis_root():
    reanalysis = request.form.get('reanalysis',"False")
    module_id = request.args.get('id')
    runNumber = int(request.args.get('runNumber') or 0)

    if not reanalysis == "True":
        clean_dir(DATA_FOLDER)

    query = { "_id" : ObjectId(module_id) }
    thisComponent = mongo.db.component.find_one(query)
    query = { "parent" : module_id }
    child_entries = mongo.db.childParentRelation.find(query)
    for child in child_entries:
        query = { "component" : child['child'], "runNumber" : runNumber }
        thisScan = mongo.db.componentTestRun.find_one(query)
        query = { "_id" : ObjectId(thisScan['testRun']) }
        thisResult = mongo.db.testRun.find_one(query)
        testType = thisResult['testType']
        if not reanalysis == "True":
            data_entries = thisResult['attachments']
            for data in data_entries:
                if data['contentType'] == 'dat':
                    fs = gridfs.GridFS( mongo.db )
                    f = open('{0}/{1}_{2}.dat'.format(DATA_FOLDER, runNumber, data['filename'].split("_")[1] + "_" + data['filename'].split("_")[2]), "wb")
                    f.write(fs.get(ObjectId(data['code'])).read())
                    f.close()

    mapList = {}
    for mapType in scanList[testType]:
        if reanalysis == "True" and not mapType[0] == request.form.get('mapType'):
            mapList.update({ mapType[0] : False })
        else:
            mapList.update({ mapType[0] : True })

    try    : root.drawScan(thisComponent['serialNumber'], testType, str(runNumber), bool(request.form.get('log', False)), int(request.form.get('max') or 0), mapList)
    except : print("undo root process")

    return redirect(url_for('show_module', id=module_id, run=runNumber))

# chip page
@app.route('/chip_result', methods=['GET','POST'])
def show_chip():
    component = {}
    imageIndex = []

    query = { "_id" : ObjectId(request.args.get('id')) }
    thisComponent = mongo.db.component.find_one(query)
    fill_imageIndex(thisComponent, imageIndex)

    component.update({ "_id"           : request.args.get('id'), 
                       "serialNumber"  : thisComponent['serialNumber'],
                       "componentType" : thisComponent['componentType'],
                       "url"           : "show_chip",
                       "type"          : "chip",
                       "imageIndex"    : imageIndex,
                       "displayIndex"  : [],
                       "scanIndex"     : [],
                       "dataIndex"     : [] }) 
   
    for scan in scanList:
        query = { "component" : component['_id'], "testType" : scan }
        run_entries = mongo.db.componentTestRun.find(query)
        runIndex = []
        displayIndex = []
        for run in run_entries:
            query = { "_id" : ObjectId(run['testRun']) }
            thisRun = mongo.db.testRun.find_one(query)
            env_dict = fill_runIndex(thisRun, runIndex)

            if thisRun['runNumber'] == int(request.args.get('runNumber') or 0):
                data_entries = thisRun['attachments']
                for data in data_entries:
                    if data['contentType'] == 'pdf' or data['contentType'] == 'png':
                        query = { "files_id" : ObjectId(data['code']) }
                        binary = mongo.db.fs.chunks.find_one(query)
                        byte = base64.b64encode(binary['data']).decode()
                        url = img.bin_to_image(data['contentType'],byte)
                        component['dataIndex'].append({ "testType"    : thisRun['testType'],
                                                        "runNumber"   : thisRun['runNumber'],
                                                        "runId"       : thisRun['_id'],
                                                        "code"        : data['code'],
                                                        "url"         : url,
                                                        "filename"    : data['filename'].split("_")[2],
                                                        "environment" : env_dict,
                                                        "display"     : data.get('display',"false") })
            display_entries = thisRun['attachments']
            for data in display_entries:
                if data.get('display') == 'True':
                    query = { "files_id" : ObjectId(data['code']) }
                    binary = mongo.db.fs.chunks.find_one(query)
                    byte = base64.b64encode(binary['data']).decode()
                    url = img.bin_to_image(data['contentType'],byte)

                    displayIndex.append({ "runNumber"   : thisRun['runNumber'],
                                          "runId"       : thisRun['_id'],
                                          "code"        : data['code'],
                                          "htmlurl"     : "untag_image",
                                          "filename"    : data['filename'].split("_")[2],
                                          "url"         : url })

        if not runIndex == []:
           component['scanIndex'].append({ "testType" : scan,
                                            "run"      : runIndex })
        if not displayIndex == []:
            component['displayIndex'].append({ "testType" : scan,
                                               "display"  : displayIndex })


    html = tell_admin("chip.html")
    return render_template(html, component=component)

@app.route('/tag_image', methods=['GET','POST'])
def tag_image():
    
    query = { "_id" : ObjectId(request.form.get('runId')) }
    thisRun = mongo.db.testRun.find_one(query)
    data_entries = thisRun['attachments']
    for data in data_entries:
        if data['code'] == request.form.get('code'):
            if not 'display' in data:
                mongo.db.testRun.update( query, { '$set' : {'attachments.{}.display'.format( data_entries.index(data) ) : "True" }})
                mongo.db.testRun.update( query, { '$set' : { 'sys.rev' : int(mongo.db.testRun.find_one( query )['sys']['rev']+1), 
                                                             'sys.mts' : datetime.datetime.utcnow() }})

    forUrl = "show_{}".format(request.form.get('type'))

    return redirect(url_for(forUrl, id=request.form.get('id'), runId=request.form.get('runId')))

@app.route('/untag_image', methods=['GET','POST'])
def untag_image():
    
    query = { "_id" : ObjectId(request.form.get('runId')) }
    thisRun = mongo.db.testRun.find_one(query)
    data_entries = thisRun['attachments']
    for data in data_entries:
        if data['code'] == request.form.get('code'):
            if 'display' in data:
                mongo.db.testRun.update( query, {'$unset': {'attachments.{}.display'.format( data_entries.index(data) ) : "True" }})
                mongo.db.testRun.update( query, { '$set' : { 'sys.rev' : int(mongo.db.testRun.find_one( query )['sys']['rev']+1), 
                                                             'sys.mts' : datetime.datetime.utcnow() }})

    forUrl = "show_{}".format(request.form.get('type'))

    return redirect(url_for(forUrl, id=request.form.get('id'), runId=request.form.get('runId')))

@app.route('/add_attachment_result', methods=['GET','POST'])
def add_attachment_result():
    fs = gridfs.GridFS(mongo.db)
    fileResult = request.form.get('path') 
    print(fileResult)
    binary_image = open(fileResult,'rb')
    runNumber = fileResult.rsplit('/',4)[4].rsplit('_',2)[0]
    mapType = fileResult.rsplit('/',4)[4].rsplit('_',2)[1]
    testType = fileResult.rsplit('/',4)[3]
    filename = "{0}_{1}_{2}.png".format(runNumber,testType,mapType)
    image = fs.put(binary_image.read(), filename=filename)
    binary_image.close()
    
    thisImage = mongo.db.fs.files.find_one({"_id":image})
    date = thisImage['uploadDate']
    query = { "_id" : ObjectId(request.form.get('id'))}
    mongo.db.component.update( query, { '$push' : { "attachments" : { "code"        : str(image),
                                                                      "dateTime"    : date,
                                                                      "title"       : "",
                                                                      "description" : "",
                                                                      "display"     : "True",
                                                                      "imageType"   : "result",
                                                                      "contentType" : filename.rsplit('.',1)[1],
                                                                      "filename"    : filename }}})
    mongo.db.component.update( query, { '$set' : { 'sys.rev' : int(mongo.db.component.find_one( query )['sys']['rev']+1), 
                                                   'sys.mts' : datetime.datetime.utcnow() }})

    forUrl = "show_{}".format(request.form.get('type'))

    return redirect(url_for(forUrl, id=request.form.get('id')))

@app.route('/add_attachment', methods=['GET','POST'])
def add_attachment():

    file=request.files.get('file')
    if file and func.allowed_file(file.filename):
        filename = secure_filename(file.filename)
        if not os.path.isdir(UPLOAD_FOLDER):
            os.mkdir(UPLOAD_FOLDER)
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        fs = gridfs.GridFS(mongo.db)
        fileUp = "{0}/{1}".format(UPLOAD_FOLDER,filename)
        binary_image = open(fileUp,'rb')
        title = request.form.get('title')
        description = request.form.get('description')
        if title == "": title = filename.rsplit('.',1)[0]
        image = fs.put(binary_image.read(), filename=filename)
        binary_image.close()
        
        thisImage = mongo.db.fs.files.find_one({"_id":image})
        date = thisImage['uploadDate']
        query = { "_id" : ObjectId(request.form.get('id'))}
        mongo.db.component.update( query, { '$push' : { "attachments" : { "code"        : str(image),
                                                                          "dateTime"    : date,
                                                                          "title"       : title,
                                                                          "description" : description,
                                                                          "imageType"   : "image",
                                                                          "contentType" : filename.rsplit('.',1)[1],
                                                                          "filename"    : filename }}})
        mongo.db.component.update( query, { '$set' : { 'sys.rev' : int(mongo.db.component.find_one( query )['sys']['rev']+1), 
                                                       'sys.mts' : datetime.datetime.utcnow() }})

    forUrl = "show_{}".format(request.form.get('type'))

    return redirect(url_for(forUrl, id=request.form.get('id')))

@app.route('/remove_attachment',methods=['GET','POST'])
def remove_attachment():
    code = request.form.get('code')
    
    mongo.db.fs.files.remove({ "_id" : ObjectId(code) }) 
    mongo.db.fs.chunks.remove({ "files_id" : ObjectId(code) }) 
    query = { "_id" : ObjectId(request.form.get('id'))}
    mongo.db.component.update( query, { '$pull' : { "attachments" : { "code" : code }}}) 
    mongo.db.component.update( query, { '$set' : { 'sys.rev' : int(mongo.db.component.find_one( query )['sys']['rev']+1), 
                                                   'sys.mts' : datetime.datetime.utcnow() }})

    forUrl = "show_{}".format(request.form.get('type'))
    return redirect(url_for(forUrl, id=request.form.get('id')))

@app.route('/login',methods=['POST'])
def login():
    userName = userdb.user.find_one({"userName":request.form['username']})
    try:
        if hashlib.md5(request.form['password'].encode("utf-8")).hexdigest() == userName['passWord']:
            session['logged_in'] = True
        else:
            txt = "not match password"
            return render_template("error.html", txt=txt)
    except:
        txt = "not found user"
        return render_template("error.html", txt=txt)
    return redirect(url_for('show_modules_and_chips'))

@app.route('/logout',methods=['GET','POST'])
def logout():
    session['logged_in'] = False

    return redirect(url_for('show_modules_and_chips'))

if __name__ == '__main__':
    app.run(host='192.168.1.43') # change hostID
