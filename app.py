import pymongo, json, bson.objectid, logging, doc, img, base64, item
from collections import OrderedDict
import pprint
from flask import Flask, current_app, request, flash,redirect,url_for,render_template
from flask_pymongo import PyMongo
from dateutil.parser import parse
from bson.objectid import ObjectId # Convert str to ObjectId

app = Flask(__name__)
app.secret_key = 'secret'
app.config["MONGO_URI"] = "mongodb://localhost:27017/yarrdb"
mongo = PyMongo(app)

@app.route('/', methods=['GET'])
def show_modules_and_chips():
    query = {"componentType": "Module"}
    component = mongo.db.component.find(query)
    modules = []
    module_entries = []
    for row in component:
        module_entries.append({"_id": row['_id'], "serialNumber": row['serialNumber'], "datetime": row['sys']['cts'].strftime("%Y/%m/%d-%H:%M:%S")})

    for module_entry in module_entries:
        query = {"parent": str(module_entry['_id'])}
        cprelation = mongo.db.childParentRelation.find(query)
        child_entries = []
        for row in cprelation:
            child_entries.append({"child": row['child'], "datetime": row['sys']['cts'].strftime("%Y/%m/%d-%H:%M:%S")})

        chips = []
        for child_entry in child_entries:
            query = {"_id": ObjectId(child_entry['child'])}
            chip_entry = mongo.db.component.find_one(query) # Find child component
            chips.append({"_id": str(chip_entry["_id"]), "serialNumber": chip_entry["serialNumber"], "componentType": chip_entry["componentType"], "datetime": chip_entry["sys"]["cts"]})

        modules.append({"_id": str(module_entry["_id"]), "serialNumber": module_entry["serialNumber"], "chips": chips})

    return render_template('toppage.html', modules=modules)

@app.route('/component', methods=['GET'])
def show_component():
    docs = mongo.db.childParentRelation.find().sort('$natural', pymongo.DESCENDING)
    contents = []
    for doc in docs:
        pId = ""
        rel = []
        if pId == doc['parent']:
            rel.append({"childId": doc['child']})
        else:
            contents.append({"mod": rel})
            rel = []
            pId = doc['parent']
            rel.append({"parentId": doc['parent'], "childId": doc['child']})

    return render_template('component.html', contents=contents)

@app.route('/testRun', methods=['GET','POST'])
def show_result():
    componentId = request.args.get('id')
    runNumber=""
    testType=""
    docs = mongo.db.componentTestRun.find({"component": componentId}).sort('$natural', pymongo.DESCENDING)
    index = []
    results = []
    for doc in docs:
        testRunId = bson.objectid.ObjectId(doc['testRun'])
        doc_t = mongo.db.testRun.find({"_id": testRunId}).sort('$natural',pymongo.DESCENDING)
        for item in doc_t:
            if 'environment' in item:
                if 'hv' in item['environment']:
                    index.append({ "_id":item['_id'],
                                   "testType":item['testType'], 
                                   "runNumber":item['runNumber'], 
                                   "datetime":item['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                                   "institution":item['institution'],
                                   "environment":
                                       { "hv":item['environment']['hv'],
                                         "cool":item['environment']['cool'],
                                         "stage":item['environment']['stage'] }})
                else: 
                    index.append({ "_id":item['_id'],
                                   "testType":item['testType'], 
                                   "runNumber":item['runNumber'], 
                                   "datetime":item['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                                   "institution":item['institution'],
                                   "environment":
                                       { "hv":"",
                                         "cool":"",
                                         "stage":"" }})
            else:
                index.append({ "_id":item['_id'],
                               "testType":item['testType'], 
                               "runNumber":item['runNumber'], 
                               "datetime":item['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                               "institution":item['institution'],
                               "environment":
                                   { "hv":"",
                                     "cool":"",
                                     "stage":"" }})

    return render_template('testresult.html', index=index, results=results, runNumber=runNumber, testType=testType, componentId=componentId)
    #return render_template('kubota.html', index=index, results=results, runNumber=runNumber, testType=testType)

@app.route('/testRun_result', methods=['GET','POST'])
def show_result_item():
    componentId = request.form['componentId']
    runNumber = request.form['runNumber']
    testType = request.form['testType']
    logging.log(100,"show_result_item")
    #componentId = request.args.get('id')
    docs = mongo.db.componentTestRun.find({"component": componentId}).sort('$natural', pymongo.DESCENDING)
    index = []
    results = []
    for doc in docs:
        testRunId = bson.objectid.ObjectId(doc['testRun'])
        doc_t = mongo.db.testRun.find({"_id": testRunId}).sort('$natural',pymongo.DESCENDING)
        for item in doc_t:
            if 'environment' in item:
                if 'hv' in item['environment']:
                    index.append({ "_id":item['_id'],
                                   "testType":item['testType'], 
                                   "runNumber":item['runNumber'], 
                                   "datetime":item['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                                   "institution":item['institution'],
                                   "environment":
                                       { "hv":item['environment']['hv'],
                                         "cool":item['environment']['cool'],
                                         "stage":item['environment']['stage'] }})
                else: 
                    index.append({ "_id":item['_id'],
                                   "testType":item['testType'], 
                                   "runNumber":item['runNumber'], 
                                   "datetime":item['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                                   "institution":item['institution'],
                                   "environment":
                                       { "hv":"",
                                         "cool":"",
                                         "stage":"" }})
            else:
                index.append({ "_id":item['_id'],
                               "testType":item['testType'], 
                               "runNumber":item['runNumber'], 
                               "datetime":item['date'].strftime("%Y/%m/%d-%H:%M:%S"),
                               "institution":item['institution'],
                               "environment":
                                   { "hv":"",
                                     "cool":"",
                                     "stage":"" }})

            if int(item['runNumber']) == int(runNumber):
                logging.log(100,"hit")
                list_t = item['attachments']
                for data in list_t:
                    if data['contentType'] == 'pdf' or data['contentType'] == 'png':
                        code = bson.objectid.ObjectId(data['code'])
                        doc_b = mongo.db.fs.chunks.find({"files_id":code}).sort('$natural',pymongo.DESCENDING)
                        for data_b in doc_b:
                            byte = base64.b64encode(data_b['data']).decode()
                            url = img.bin_to_image(data['contentType'],byte)
                            results.append({ "testType":item['testType'],
                                             "url":url,
                                             "filename":data['filename'],
                                             "contentType":data['contentType'] })

    return render_template('testresult.html', index=index, results=results, runNumber=runNumber, testType=testType, componentId=componentId)

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
    app.run(host='192.168.11.140') # change hostID

#@app.route('/index/open/document', methods=['POST'])
#def open_document():
#
#    collection = request.form['col']
#    document = bson.objectid.ObjectId(request.form['doc'])
#
#    # collection Name
#    collectionNames = mongo.db.collection_names()
#    collections = []
#    collections.append({"collection": collection})
#    for col in collectionNames:
#      if col != collection:
#        collections.append({"collection": col})
#
#    # key and value
#    #key = 'files_id'
#    #if collection == collection_open:
#    key = '_id'
#
#    names = []
#    #items = mongo.db[collection_open].find({key: document}).limit(10)
#    items = mongo.db[collection].find({key: document}).limit(10)
#    image = ""
#    for item in items:
##      if collection_open == 'fs.chunck':
##        byte=base64.b64encode(item['data']).decode()
##        #image=img.bin_to_image('png', byte)
##        image=img.bin_to_image('pdf', byte)
##        logging.log(100,image)
##        #image=byte
#      datas = [k for k, v in item.items()]
#      for data in datas:
#        names.append({"key": data, "value": item[data]})
#    logging.info('info')
#    
#    return render_template('document.html', collection=collection, collections=collections, names=names, image=image) 
#
