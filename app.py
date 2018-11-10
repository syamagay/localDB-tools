try    : import root
except : pass 

import pymongo, json, logging, img, base64, func, ast, gridfs
import os, glob, getpass

from collections import OrderedDict
from flask import Flask, current_app, request, flash, redirect,url_for, render_template, session, abort
from flask_pymongo import PyMongo
from bson.objectid import ObjectId 
from bson.binary import BINARY_SUBTYPE
from werkzeug import secure_filename
from pymongo import MongoClient
import hashlib

scanList = { "selftrigger"   : [("OccupancyMap-0", "#Hit"),],
             "noisescan"     : [("NoiseOccupancy","NoiseOccupancy"), ("NoiseMask", "NoiseMask")],
             "totscan"       : [("MeanTotMap", "Mean[ToT]"),         ("SigmaTotMap", "Sigma[ToT]")],
             "thresholdscan" : [("ThresholdMap", "Threshold[e]"),    ("NoiseMap", "Noise[e]")],
             "digitalscan"   : [("OccupancyMap", "Occupancy"),       ("EnMask", "EnMask")],
             "analogscan"    : [("OccupancyMap", "Occupancy"),       ("EnMask", "EnMask")]}

if not os.path.isdir('/tmp/{}'.format(os.getlogin())):
    os.mkdir('/tmp/{}'.format(os.getlogin()))


UPLOAD_FOLDER = '/tmp/{}/upload'.format(os.getlogin())
DATA_FOLDER = '/tmp/{}/data'.format(os.getlogin())
RESULT_FOLDER = '/tmp/{}/result'.format(os.getlogin())

app = Flask(__name__)
app.secret_key = 'secret'
app.config["MONGO_URI"] = "mongodb://localhost:27017/yarrdb"
mongo = PyMongo(app)

client = MongoClient(host='localhost', port=28000)
userdb = client['user']

def insert_data(data):
    bin_data = BINARY_SUBTYPE(open(data, 'r').read(), BINARY_SUBTYPE)
    doc = { "_id"      :"",
            "files_id" :"",
            "n"        : 1,
            "data"     : bin_data }
    mongo.db.fs.chunks.insert(doc)

# top page
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

    if session.get('logged_in') : html = 'admin_toppage.html'
    else                        : html = 'toppage.html'

    return render_template(html, modules=modules)

# module page
@app.route('/module', methods=['GET','POST'])
def show_module():
    module = {}
    chips = []
    url = []

    query = { "_id" : ObjectId(request.args.get('id')) }
    thisModule = mongo.db.component.find_one(query)

    try :
        dataPath = "./static/upload"
        if not os.path.isdir(dataPath):
            os.mkdir(dataPath)
        else:
            r = glob.glob(dataPath+"/*")
            for i in r:
                os.remove(i)
        data_entries = thisModule['attachments']
        for data in data_entries:
            if data['contentType'] == 'png' or data['contentType'] == 'jpg':
                fs = gridfs.GridFS( mongo.db )
                filePath = "{0}/{1}".format(dataPath, data['filename'])
                f = open(filePath, 'wb')
                f.write(fs.get(ObjectId(data['code'])).read())
                f.close()
                url.append({ "url"      : filePath,
                             "code"     : data['code'],
                             "title"    : data['title'],
                             "filename" : data['filename'] })
    except :
        pass

    module.update({ "_id"          : request.args.get('id'),
                    "serialNumber" : thisModule['serialNumber'],
                    "index"        : [], 
                    "data"         : url,
                    "scanIndex"    : [],
                    "dataIndex"    : [] })

    query = { "parent" : module['_id'] } 
    child_entries = mongo.db.childParentRelation.find(query).sort('$natural', pymongo.ASCENDING)
    for child in child_entries:
        query = { "_id" : ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one(query)
        chips.append({ "component" : child['child'] })
        module['index'].append({ "_id"           : ObjectId(child['child']),
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
            env_dict = { "hv"    : thisRun.get('environment',{"key":"value"}).get('hv',""),
                         "cool"  : thisRun.get('environment',{"key":"value"}).get('cool',""),
                         "stage" : thisRun.get('environment',{"key":"value"}).get('stage',"") }
            runIndex.append({ "_id"         : thisRun['_id'],
                              "runNumber"   : thisRun['runNumber'],
                              "datetime"    : func.setTime(thisRun['date']),
                              "institution" : thisRun['institution'],
                              "environment" : env_dict })

        module['scanIndex'].append({ "testType"  : scan, 
                                     "run"       : runIndex, 
                                     "url"       : "" })

    # redirect from analysis_root
    try:
        runNumber = int(request.args.get('run'))
        query = { '$or' : chips , "runNumber" : runNumber }
        thisRun = mongo.db.componentTestRun.find_one(query)
        testType = thisRun['testType']
        cnt = 0
        for mapType in scanList[testType]:
            for i in [ "1", "2" ]:
                max_value = func.readJson("parameter.json") 
                module['dataIndex'].append({ "testType"  : testType, 
                                             "mapType"   : mapType[0], 
                                             "runNumber" : runNumber, 
                                             "comment"   : "No Root Software",
                                             "url"       : "", 
                                             "setLog"    : max_value[testType][mapType[0]][1], 
                                             "maxValue"  : max_value[testType][mapType[0]][0] })
                filename = RESULT_FOLDER + "/" + testType + "/" + str(runNumber) + "_" + mapType[0] + "_{}.png".format(i)
                try :
                    binary_image = open(filename,'rb')
                    code_base64 = base64.b64encode(binary_image.read()).decode()
                    binary_image.close()
                    url = img.bin_to_image('png',code_base64)              
                    module['dataIndex'][cnt]['url'] = url
                    cnt += 1
                except :
                    pass
    except:
        module['dataIndex'].append({"test":"test"})

    if session.get('logged_in') : html = 'admin_module.html'
    else                        : html = 'module.html'

    return render_template(html, module=module)

@app.route('/analysis', methods=['GET','POST'])
def analysis_root():
    dataPath = DATA_FOLDER 
    if not os.path.isdir(dataPath):
        os.mkdir(dataPath)
    else:
        r = glob.glob(dataPath+"/*")
        for i in r:
            os.remove(i)

    module_id = request.args.get('id')
    runNumber = int(request.args.get('runNumber'))

    query = { "_id" : ObjectId(module_id) }
    thisModule = mongo.db.component.find_one(query)

    query = { "parent" : module_id }
    child_entries = mongo.db.childParentRelation.find(query)
    for child in child_entries:
        query = { "component" : child['child'], "runNumber" : runNumber }
        thisScan = mongo.db.componentTestRun.find_one(query)

        query = { "_id" : ObjectId(thisScan['testRun']) }
        thisResult = mongo.db.testRun.find_one(query)
        testType = thisResult['testType']

        data_entries = thisResult['attachments']
        for data in data_entries:
            if data['contentType'] == 'dat':
                query = { "files_id" : ObjectId(data['code']) }
                thisBinary = mongo.db.fs.chunks.find_one(query)
                f = open('{0}/{1}_{2}.dat'.format(DATA_FOLDER, runNumber, data['filename'].split("_")[1] + "_" + data['filename'].split("_")[2]), "wb")
                #f.write(thisBinary['data'])
                f.write(thisBinary['data'])
                f.close()

    mapList = {}
    for mapType in scanList[testType]:
        mapList.update({ mapType[0] : True })
    try    : root.drawScan(thisModule['serialNumber'], testType, str(runNumber), False, "", mapList)
    except : pass

    return redirect(url_for('show_module', id=module_id, run=runNumber))

@app.route('/reanalysis', methods=['POST'])
def reanalysis_root():
    module_id = request.form['id']
    runNumber = request.form['runNumber']
    query = { "_id" : ObjectId(module_id) }
    thisModule = mongo.db.component.find_one(query)
    
    mapList = {}
    for mapType in scanList[request.form['testType']]:
        if mapType[0] == request.form['mapType']:
            mapList.update({ mapType[0] : True })
        else:
            mapList.update({ mapType[0] : False })

    try    : root.drawScan(thisModule['serialNumber'], str(request.form['testType']), str(runNumber), bool(request.form.get('log', False)), int(request.form.get('max',1000)), mapList)
    except : pass

    return redirect(url_for('show_module', id=module_id, run=runNumber))

# chip page
@app.route('/chip_result', methods=['GET','POST'])
def show_chip():
    chip = {}
    url = []

    query = { "_id" : ObjectId(request.args.get('id')) }
    thisChip = mongo.db.component.find_one(query)
    try    : runId = ObjectId(request.args.get('runId')) 
    except : runId = ""

    try :
        dataPath = "./static/upload"
        if not os.path.isdir(dataPath):
            os.mkdir(dataPath)
        else:
            r = glob.glob(dataPath+"/*")
            for i in r:
                os.remove(i)
        data_entries = thisChip['attachments']
        for data in data_entries:
            if data['contentType'] == 'png' or data['contentType'] == 'jpg':
                fs = gridfs.GridFS( mongo.db )
                filePath = "{0}/{1}".format(dataPath, data['filename'])
                f = open(filePath, 'wb')
                f.write(fs.get(ObjectId(data['code'])).read())
                f.close()
                url.append({ "url"      : filePath,
                             "code"     : data['code'],
                             "title"    : data['title'],
                             "filename" : data['filename'] })
    except :
        pass

    chip.update({ "_id"           : request.args.get('id'), 
                  "serialNumber"  : thisChip['serialNumber'],
                  "componentType" : thisChip['componentType'],
                  "run_id"        : runId,
                  "data"          : url,
                  "displayIndex"  : [],
                  "scanIndex"     : [],
                  "dataIndex"     : [] }) 
   
    for scan in scanList:
        query = { "component" : chip['_id'], "testType" : scan }
        run_entries = mongo.db.componentTestRun.find(query)
        displayIndex = []
        runIndex = []
        for run in run_entries:
            query = { "_id" : ObjectId(run['testRun']) }
            thisRun = mongo.db.testRun.find_one(query)

            env_dict = { "hv"    : thisRun.get('environment',{"key":"value"}).get('hv',""),
                         "cool"  : thisRun.get('environment',{"key":"value"}).get('cool',""),
                         "stage" : thisRun.get('environment',{"key":"value"}).get('stage',"") }

            runIndex.append({ "_id"         : thisRun['_id'],
                              "runNumber"   : thisRun['runNumber'],
                              "datetime"    : func.setTime(thisRun['date']),
                              "institution" : thisRun['institution'],
                              "environment" : env_dict })

            display_entries = thisRun['attachments']
            for display in display_entries:
                try:
                    if display['display'] == 'True':
                        query = { "files_id" : ObjectId(display['code']) }
                        binary = mongo.db.fs.chunks.find_one(query)
                        byte = base64.b64encode(binary['data']).decode()
                        url = img.bin_to_image(display['contentType'],byte)
                        displayIndex.append({ "runNumber"   : thisRun['runNumber'],
                                              "filename"    : display['filename'].split("_")[2],
                                              "url"         : url })
                except:
                    pass

            if (thisRun['_id']) == chip['run_id']:
                data_entries = thisRun['attachments']
                for data in data_entries:
                    if data['contentType'] == 'pdf' or data['contentType'] == 'png':
                        query = { "files_id" : ObjectId(data['code']) }
                        binary = mongo.db.fs.chunks.find_one(query)
                        byte = base64.b64encode(binary['data']).decode()
                        url = img.bin_to_image(data['contentType'],byte)
                        chip['dataIndex'].append({ "testType"    : thisRun['testType'],
                                                   "runNumber"   : thisRun['runNumber'],
                                                   "runId"       : thisRun['_id'],
                                                   "code"        : data['code'],
                                                   "url"         : url,
                                                   "filename"    : data['filename'].split("_")[2],
                                                   "datetime"    : func.setTime(thisRun['date']),
                                                   "environment" : env_dict,
                                                   "display"     : data.get('display',"false"),
                                                   "contentType" : data['contentType'] })
    
        if not runIndex == []:
            chip['scanIndex'].append({ "testType" : scan,
                                       "run"      : runIndex })
        if not displayIndex == []:
            chip['displayIndex'].append({ "testType" : scan,
                                          "display"  : displayIndex })


    if session.get('logged_in'): html='admin_chip.html'
    else                       : html='chip.html'

    return render_template(html, chip=chip)

@app.route('/tag_image', methods=['GET','POST'])
def tag_image():
    
    query = { "_id" : ObjectId(request.form.get('runId')) }
    thisRun = mongo.db.testRun.find_one(query)
    data_entries = thisRun['attachments']
    for data in data_entries:
        if data['code'] == request.form.get('code'):
            if not 'display' in data:
                mongo.db.testRun.update( query, {'$set': {'attachments.{}.display'.format( data_entries.index(data) ) : "True" }})

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

    forUrl = "show_{}".format(request.form.get('type'))

    return redirect(url_for(forUrl, id=request.form.get('id'), runId=request.form.get('runId')))


@app.route('/add_attachment', methods=['GET','POST'])
def add_attachment():

    file=request.files['file']
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
                                                                          "contentType" : filename.rsplit('.',1)[1],
                                                                          "filename"    : filename }}})

    forUrl = "show_{}".format(request.form.get('type'))

    return redirect(url_for(forUrl, id=request.form.get('id')))

@app.route('/remove_attachment',methods=['GET','POST'])
def remove_attachment():
    code = request.form.get('code')
    thisId = request.form.get('id')
    
    mongo.db.fs.files.remove({ "_id" : ObjectId(code) }) 
    mongo.db.fs.chunks.remove({ "files_id" : ObjectId(code) }) 
    mongo.db.component.update({ "_id" : ObjectId(thisId) }, { '$pull' : { "attachments" : { "code" : code }}}) 

    forUrl = "show_{}".format(request.form.get('type'))
    return redirect(url_for(forUrl, id=thisId))

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
    app.run(host='127.0.0.1') # change hostID
