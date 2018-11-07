try:
    import root
except:
    pass 
import bson.objectid, bson.binary 
import pymongo, json, logging, img, base64, os, func, ast, glob 
from collections import OrderedDict
import pprint
from flask import Flask, current_app, request, flash, redirect,url_for, render_template, session, abort
from flask_pymongo import PyMongo
from dateutil.parser import parse
from bson.objectid import ObjectId # Convert str to ObjectId
from bson.binary import BINARY_SUBTYPE
from werkzeug import secure_filename

scanList = { "selftrigger"   : [("OccupancyMap-0", "#Hit"),],
             "noisescan"     : [("NoiseOccupancy","NoiseOccupancy"), ("NoiseMask", "NoiseMask")],
             "totscan"       : [("MeanTotMap", "Mean[ToT]"),         ("SigmaTotMap", "Sigma[ToT]")],
             "thresholdscan" : [("ThresholdMap", "Threshold[e]"),    ("NoiseMap", "Noise[e]")],
             "digitalscan"   : [("OccupancyMap", "Occupancy"),       ("EnMask", "EnMask")],
             "analogscan"    : [("OccupancyMap", "Occupancy"),       ("EnMask", "EnMask")]}

UPLOAD_FOLDER = '/tmp/upload'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.secret_key = 'secret'
app.config["MONGO_URI"] = "mongodb://localhost:28000/yarrdb"
mongo = PyMongo(app)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def insert_data(data):
    bin_data = bson.binary.Binary(open(data, 'r').read(), BINARY_SUBTYPE)
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

    query = { "_id" : bson.objectid.ObjectId(request.args.get('id')) }
    thisModule = mongo.db.component.find_one(query)
    module.update({ "_id"          : request.args.get('id'),
                    "serialNumber" : thisModule['serialNumber'],
                    "index"        : [], 
                    "scanIndex"    : [],
                    "dataIndex"    : [] })

    query = { "parent" : module['_id'] } 
    child_entries = mongo.db.childParentRelation.find(query).sort('$natural', pymongo.ASCENDING)
    for child in child_entries:
        query = { "_id" : bson.objectid.ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one(query)
        chips.append({ "component" : child['child'] })
        module['index'].append({ "_id"           : bson.objectid.ObjectId(child['child']),
                                 "number"        : thisChip["serialNumber"].split("_")[1],
                                 "chip"          : thisChip['serialNumber'],
                                 "componentType" : thisChip['componentType'] })

    for scan in scanList:
        query = { '$or' : chips, "testType" : scan }
        run_entries = mongo.db.componentTestRun.find(query)
        runIndex = []
        for run in run_entries:
            query = { "_id" : bson.objectid.ObjectId(run['testRun']) }
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
                filename = "/tmp/" + testType + "/" + str(runNumber) + "_" + mapType[0] + "_{}.png".format(i)
                try :
                    binary_png = open(filename,'rb')
                    code_base64 = base64.b64encode(binary_png.read()).decode()
                    binary_png.close()
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
    dataPath = '/tmp/data'
    if not os.path.isdir(dataPath):
        os.mkdir(dataPath)
    else:
        r = glob.glob(dataPath+"/*")
        for i in r:
            os.remove(i)

    module_id = request.args.get('id')
    runNumber = int(request.args.get('runNumber'))

    query = { "_id" : bson.objectid.ObjectId(module_id) }
    thisModule = mongo.db.component.find_one(query)

    query = { "parent" : module_id }
    child_entries = mongo.db.childParentRelation.find(query)
    for child in child_entries:
        query = { "component" : child['child'], "runNumber" : runNumber }
        thisScan = mongo.db.componentTestRun.find_one(query)

        query = { "_id" : bson.objectid.ObjectId(thisScan['testRun']) }
        thisResult = mongo.db.testRun.find_one(query)
        testType = thisResult['testType']

        data_entries = thisResult['attachments']
        for data in data_entries:
            if data['contentType'] == 'dat':
                query = { "files_id" : bson.objectid.ObjectId(data['code']) }
                thisBinary = mongo.db.fs.chunks.find_one(query)
                f = open('/tmp/data/{0}_{1}.dat'.format(runNumber, data['filename'].split("_")[1] + "_" + data['filename'].split("_")[2]), "w")
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
    query = { "_id" : bson.objectid.ObjectId(module_id) }
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

    url = ""
    try:
        file=request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if not os.path.isdir(UPLOAD_FOLDER):
                os.mkdir(UPLOAD_FOLDER)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            fileUp = UPLOAD_FOLDER + "/" + filename 
            binary_png = open(fileUp,'rb')
            code_base64 = base64.b64encode(binary_png.read()).decode()
            binary_png.close()
            url = img.bin_to_image('png',code_base64)
    except:
        pass

    query = { "_id" : bson.objectid.ObjectId(request.args.get('id')) }
    thisChip = mongo.db.component.find_one(query)
    try    : runId = bson.objectid.ObjectId(request.args.get('runId')) 
    except : runId = ""

    chip.update({ "_id"           : request.args.get('id'), 
                  "serialNumber"  : thisChip['serialNumber'],
                  "componentType" : thisChip['componentType'],
                  "run_id"        : runId,
                  "url"           : url,
                  "scanIndex"     : [],
                  "dataIndex"     : [] }) 
    
    for scan in scanList:
        query = { "component" : chip['_id'], "testType" : scan }
        run_entries = mongo.db.componentTestRun.find(query)
        runIndex = []
        for run in run_entries:
            query = { "_id" : bson.objectid.ObjectId(run['testRun']) }
            thisRun = mongo.db.testRun.find_one(query)

            env_dict = { "hv"    : thisRun.get('environment',{"key":"value"}).get('hv',""),
                         "cool"  : thisRun.get('environment',{"key":"value"}).get('cool',""),
                         "stage" : thisRun.get('environment',{"key":"value"}).get('stage',"") }

            runIndex.append({ "_id"         : thisRun['_id'],
                              "runNumber"   : thisRun['runNumber'],
                              "datetime"    : func.setTime(thisRun['date']),
                              "institution" : thisRun['institution'],
                              "environment" : env_dict })

            if (thisRun['_id']) == chip['run_id']:
                data_entries = thisRun['attachments']
                for data in data_entries:
                    if data['contentType'] == 'pdf' or data['contentType'] == 'png':
                        query = { "files_id" : bson.objectid.ObjectId(data['code']) }
                        binary = mongo.db.fs.chunks.find_one(query)
                        byte = base64.b64encode(binary['data']).decode()
                        url = img.bin_to_image(data['contentType'],byte)
                        chip['dataIndex'].append({ "testType"    : thisRun['testType'],
                                                   "runNumber"   : thisRun['runNumber'],
                                                   "url"         : url,
                                                   "filename"    : data['filename'].split("_")[2],
                                                   "datetime"    : func.setTime(thisRun['date']),
                                                   "environment" : env_dict,
                                                   "contentType" : data['contentType'] })
    

        chip['scanIndex'].append({ "testType" : scan,
                                   "run"      : runIndex })

    if session.get('logged_in'): html='admin_chip.html'
    else                       : html='chip.html'

    return render_template(html, chip=chip)

@app.route('/login',methods=['POST'])
def login():
    if request.form['password'] == "password" and request.form['username'] == "user":
        session['logged_in'] = True
    else:
        flash('wrong password!')
    return redirect(url_for('show_modules_and_chips'))

@app.route('/logout',methods=['GET','POST'])
def logout():
    session['logged_in'] = False

    return redirect(url_for('show_modules_and_chips'))

@app.route('/test',methods=['GET','POST'])
def test_form():
    test_hidden = request.form.getlist('test_hidden')
    test = request.form.getlist('test')
    
    return redirect(url_for('show_modules_and_chips'))

@app.route('/add', methods=['GET','POST'])
def add_entry():
    mongo.db.user.insert({"name": request.form['name'], "birthday": parse(request.form['birthday'])})
    flash('New entry was successfully posted')
    return redirect(url_for('show_entry'))

@app.route('/update', methods=['GET','POST'])
def update_entry():
    mongo.db.user.insert({"name": request.form['name'], "birthday": parse(request.form['birthday'])})
    flash('New entry was successfully posted')
    return redirect(url_for('show_entry'))

@app.route('/search', methods=['POST'])
def filter_entry():
    start = parse(request.form['start'])
    end = parse(request.form['end'])
    cur = mongo.db.user.find({'birthday': {'$lt': end, '$gte': start}}).limit(10)
    results = []
    for row in cur:
        results.append({"name": row['name'], "birthday": row['birthday'].strftime("%Y/%m/%d")})

    return render_template('result.html', results=results)

@app.route('/index', methods=['POST'])
def index_entry():
    collection = request.form['col']
    collectionNames = mongo.db.collection_names()
    collections = []
    collections.append({"collection": collection})
    for col in collectionNames:
        if col != collection:
            collections.append({"collection": col})

    items = mongo.db[collection].find().sort('$natural', pymongo.DESCENDING).limit(10) #pymongo.cursor.Cursor
    index = []
    for item in items:
        datas = [k for k, v in item.items()]
        for data in datas:
            if data == '_id':
                index.append({"value": item[data]}) 

    return render_template('collection.html', collection=collection, collections=collections, index=index) 

@app.route('/index/open', methods=['POST'])
def open_entry():

    collection = request.form['col']
    document = bson.objectid.ObjectId(request.form['doc'])

    # title
    items = mongo.db[collection].find().sort('$natural', pymongo.DESCENDING).limit(10) #pymongo.cursor.Cursor
    index = []
    for item in items:
      datas = [k for k, v in item.items()]
      for data in datas:
        if data == '_id':
          index.append({"value": item[data]}) 

    return render_template('collection.html', collection=collection, index=index) 

@app.route('/index/open/document', methods=['POST'])
def open_document():

    collection = request.form['col']
    document = bson.objectid.ObjectId(request.form['doc'])

    # collection Name
    collectionNames = mongo.db.collection_names()
    collections = []
    collections.append({"collection": collection})
    for col in collectionNames:
        if col != collection:
            collections.append({"collection": col})

    # key and value
    #key = 'files_id'
    #if collection == collection_open:
    key = '_id'

    names = []
    items = mongo.db[collection].find({key: document}).limit(10)
    image = ""
    for item in items:
        if collection == 'fs.chunks':
            byte=base64.b64encode(item['data']).decode()
            #image=img.bin_to_image('png', byte)
            image=img.bin_to_image('pdf', byte)
        datas = [k for k, v in item.items()]
        for data in datas:
            names.append({"key": data, "value": item[data]})
    logging.info('info')
    
    return render_template('document.html', collection=collection, collections=collections, names=names, image=image) 

@app.route('/index/open/image', methods=['POST'])
def show_image():
    image = request.form['image']

    return render_template('pdf.html',image=image) 

if __name__ == '__main__':
    app.run(host='192.168.1.43') # change hostID
