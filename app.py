import pymongo, json, bson.objectid, logging, img, base64
from collections import OrderedDict
import pprint
from flask import Flask, current_app, request, flash,redirect,url_for,render_template
from flask_pymongo import PyMongo
from dateutil.parser import parse
from bson.objectid import ObjectId # Convert str to ObjectId

app = Flask(__name__)
app.secret_key = 'secret'
#app.config["MONGO_URI"] = "mongodb://localhost:27017/yarrdb"
app.config["MONGO_URI"] = "mongodb://localhost:27000/yarrdb"
#app.config["MONGO_URI"] = "mongodb://localhost:28000/yarrdb"
mongo = PyMongo(app)

scanList = [ "selftrigger",
             "noisescan",
             "totscan",
             "thresholdscan",
             "digitalscan",
             "analogscan" ]

@app.route('/', methods=['GET'])
def show_modules_and_chips():
    query = {"componentType": "Module"}
    component = mongo.db.component.find(query)
    modules = []
    module_entries = []
    for row in component:
        module_entries.append({ "_id": row['_id'],
                                "serialNumber": row['serialNumber'], 
                                "datetime": row['sys']['cts'].strftime("%Y/%m/%d-%H:%M:%S") })

    for module_entry in module_entries:
        query = {"parent": str(module_entry['_id'])}
        cprelation = mongo.db.childParentRelation.find(query)
        child_entries = []
        for row in cprelation:
            child_entries.append({ "child": row['child'],
                                   "datetime": row['sys']['cts'].strftime("%Y/%m/%d-%H:%M:%S") })

        chips = []
        for child_entry in child_entries:
            query = {"_id": ObjectId(child_entry['child'])}
            chip_entry = mongo.db.component.find_one(query) # Find child component
            chips.append({ "_id": str(chip_entry["_id"]),
                           "serialNumber": chip_entry["serialNumber"],
                           "componentType": chip_entry["componentType"],
                           "datetime": chip_entry["sys"]["cts"].strftime("%Y-%m-%d %H:%M:%S") })

        modules.append({ "_id": str(module_entry["_id"]),
                         "serialNumber": module_entry["serialNumber"],
                         "chips": chips })

    return render_template('toppage.html', modules=modules)

@app.route('/module', methods=['GET','POST'])
def show_module():
    index = []
    figures = []
    module = []
    module.append({ "_id": request.args.get('id'),
                    "serialNumber": request.args.get('serialNumber') })

    query = { "parent": module[0]['_id'] } 
    child_entries = mongo.db.childParentRelation.find(query).sort('$natural', pymongo.ASCENDING)
    for child in child_entries:
        query = { "_id": bson.objectid.ObjectId(child['child']) }
        chip = mongo.db.component.find_one(query)
        index.append({ "_id": bson.objectid.ObjectId(child['child']),
                       "chip": chip['serialNumber'],
                       "componentType": chip['componentType'] })

        query = {"component": child['child'], "testType": "selftrigger"}
        for scan in scanList:
            figures.append({"url": scan})
#        scan_entries = mongo.db.componentTestRun.find(query)
#        for scan in scan_entries:
#            query = {"_id":bson.objectid.ObjectId(scan['testRun'])}
#            result = mongo.db.testRun.find_one(query)
#            data_entries = result['attachments']
#            for data in data_entries:
#                if data['contentType'] == 'png':
#                    query = { "files_id": bson.objectid.ObjectId(data['code']) }
#                    binary = mongo.db.fs.chunks.find_one(query)
#                    byte = base64.b64encode(binary['data']).decode()
#                    url = img.bin_to_image(data['contentType'],byte)
#                    figures.append({ "url": url })

    return render_template('module.html', index=index, module=module, figures=figures)

@app.route('/analysis', methods=['GET','POST'])
def analysis_root():
    chip = []
    dat = []
    query = { "parent": request.args.get('id') }
    child_entries = mongo.db.childParentRelation.find(query)
    if child_entries.count() != 4:
        return render_template('error.html', dat=dat)
    for child in child_entries:
        chip.append({ "component": child['child'] })

    query = { '$or': chip, "testType": request.args.get('scan') }
    scan_entries = mongo.db.componentTestRun.find(query).sort('runNumber',pymongo.DESCENDING)
    i = 0
    j = 0
    data_dat = {}
    for scan in scan_entries:
        if i != 4:
            query = { "_id": bson.objectid.ObjectId(scan['testRun']) }
            result = mongo.db.testRun.find_one(query)
            data_entries = result['attachments']
            for data in data_entries:
                if data['contentType'] == 'dat':
                    query = {"files_id": bson.objectid.ObjectId(data['code'])}
                    binary = mongo.db.fs.chunks.find_one(query)
                    data_dat.update({'chip{}'.format(i): str(binary)})
            i += 1
        else:
            dat.append(data_dat)
            i = 0
            j += 1
                
    return render_template('error.html', dat=dat)

    #return redirect(url_for('show_summary'))
    #return 0 

@app.route('/chip', methods=['GET','POST'])
def show_result():
    index = []
    results = []
    chip = []
    chip.append({"component": request.args.get('id'), "serialNumber": request.args.get('serialNumber'), "_id": ""})
    
    query = {"component": chip[0]['component']} 
    scan_entries = mongo.db.componentTestRun.find(query).sort('runNumber',pymongo.DESCENDING)
    for scan in scan_entries:
        result = mongo.db.testRun.find_one({"_id": bson.objectid.ObjectId(scan['testRun'])})
        if 'environment' in result:
            if 'hv' in result['environment']:
                index.append({ "_id":result['_id'],
                               "testType":result['testType'],
                               "runNumber":result['runNumber'],
                               "datetime":result['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                               "institution":result['institution'],
                               "environment":
                                   { "hv":result['environment']['hv'],
                                     "cool":result['environment']['cool'],
                                     "stage":result['environment']['stage'] }})
            else: 
                index.append({ "_id":result['_id'],
                               "testType":result['testType'],
                               "runNumber":result['runNumber'],
                               "datetime":result['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                               "institution":result['institution'],
                               "environment":
                                   { "hv":"",
                                     "cool":"",
                                     "stage":"" }}) 
        else:
            index.append({ "_id":result['_id'],
                           "testType":result['testType'],
                           "runNumber":result['runNumber'],
                           "datetime":result['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                           "institution":result['institution'],
                           "environment":
                               { "hv":"",
                                 "cool":"",
                                 "stage":"" }}) 

    return render_template('chip.html', index=index, results=results, chip=chip)

@app.route('/chip_result', methods=['GET','POST'])
def show_result_item():
    index = []
    results = []
    chip = []
    chip.append({"component": request.args.get('componentId'), "serialNumber": request.args.get('serialNumber'), "_id": bson.objectid.ObjectId(request.args.get('Id'))})
    
    query = {"component": chip[0]['component']} 
    scan_entries = mongo.db.componentTestRun.find(query).sort('runNumber',pymongo.DESCENDING)
    for scan in scan_entries:
        query = {"_id": bson.objectid.ObjectId(scan['testRun'])}
        result = mongo.db.testRun.find_one(query)
        if 'environment' in result:
            if 'hv' in result['environment']:
                index.append({ "_id":result['_id'],
                               "testType":result['testType'], 
                               "runNumber":result['runNumber'], 
                               "datetime":result['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                               "institution":result['institution'],
                               "environment":
                                   { "hv":result['environment']['hv'],
                                     "cool":result['environment']['cool'],
                                     "stage":result['environment']['stage'] }})
            else: 
                index.append({ "_id":result['_id'],
                               "testType":result['testType'], 
                               "runNumber":result['runNumber'], 
                               "datetime":result['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                               "institution":result['institution'],
                               "environment":
                                   { "hv":"",
                                     "cool":"",
                                     "stage":"" }})
        else:
            index.append({ "_id":result['_id'],
                           "testType":result['testType'], 
                           "runNumber":result['runNumber'], 
                           "datetime":result['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                           "institution":result['institution'],
                           "environment":
                               { "hv":"",
                                 "cool":"",
                                 "stage":"" }})

        if (result['_id']) == chip[0]['_id']:
            data_entries = result['attachments']
            for data in data_entries:
                if data['contentType'] == 'pdf' or data['contentType'] == 'png':
                    query = {"files_id": bson.objectid.ObjectId(data['code'])}
                    binary = mongo.db.fs.chunks.find_one(query)
                    byte = base64.b64encode(binary['data']).decode()
                    url = img.bin_to_image(data['contentType'],byte)
                    results.append({ "testType":result['testType'],
                                     "url":url,
                                     "filename":data['filename'],
                                     "contentType":data['contentType'] })

    return render_template('chip.html', index=index, results=results, chip=chip)

@app.route('/add', methods=['GET','POST'])
def add_entry():
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
    #app.run(host='127.0.0.1') # change hostID
    app.run(host='192.168.1.43') # change hostID
