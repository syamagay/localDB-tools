import pymongo, json, bson.objectid, logging
from collections import OrderedDict
import pprint
from flask import Flask, current_app, request, flash,redirect,url_for,render_template
from flask_pymongo import PyMongo
from dateutil.parser import parse

app = Flask(__name__)
app.secret_key = 'secret'
app.config["MONGO_URI"] = "mongodb://localhost:27017/testdb"
mongo = PyMongo(app)

@app.route('/', methods=['GET'])
def show_entry():
    cols = mongo.db.collection_names()
    collections = []
    for col in cols:
      collections.append({"collection": col})

    users = mongo.db.user.find().sort('$natural', pymongo.DESCENDING)
    entries = []
    for row in users:
        entries.append({"name": row['name'], "birthday": row['birthday'].strftime("%Y/%m/%d")})
  
    return render_template('toppage.html', entries=entries, collections=collections)

@app.route('/add', methods=['POST'])
def add_entry():
    mongo.db.user.insert({"name": request.form['name'], "birthday": parse(request.form['birthday'])})
    flash('New entry was successfully posted')
    return redirect(url_for('show_entry'))

@app.route('/search', methods=['POST'])
def filter_entry():
    start = parse(request.form['start'])
    end = parse(request.form['end'])
    cur = mongo.db.user.find({'birthday': {'$lt': end, '$gte': start}})
    results = []
    for row in cur:
        results.append({"name": row['name'], "birthday": row['birthday'].strftime("%Y/%m/%d")})

    return render_template('result.html', results=results)

@app.route('/index', methods=['POST'])
def index_entry():
    collection = request.form['col']
    cols = mongo.db.collection_names()
    collections = []
    collections.append({"collection": collection})
    for col in cols:
      if col != collection:
        collections.append({"collection": col})

    items = mongo.db[collection].find().sort('$natural', pymongo.DESCENDING) #pymongo.cursor.Cursor
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
    cols = mongo.db.collection_names()
    collections = []
    collections.append({"collection": collection})
    for col in cols:
      if col != collection:
        collections.append({"collection": col})

    items = mongo.db[collection].find().sort('$natural', pymongo.DESCENDING) #pymongo.cursor.Cursor
    index = []
    for item in items:
      datas = [k for k, v in item.items()]
      for data in datas:
        if data == '_id':
          index.append({"value": item[data]}) 

    collection_open = request.form['col_open']
    key = 'code'
    if collection == collection_open:
      key = '_id'
    logging.log(100,collection)
    logging.log(100,collection_open)
    logging.log(100,key)

    document = bson.objectid.ObjectId(request.form['doc'])
    names = []
    items = mongo.db[collection_open].find({key: document})
    for item in items:
      datas = [k for k, v in item.items()]
      for data in datas:
        names.append({"key": data, "value": item[data]})
    logging.info('info')

    return render_template('collection.html', collection=collection, collections=collections, index=index, names=names) 

if __name__ == '__main__':
    app.run(host='127.0.0.1') # change hostID
