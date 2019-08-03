#!/usr/bin/env python3
# -*- coding: utf-8 -*
# pages/callback.py
PAGE_NAME = "CALLBACK"
from configs.imports import *

callback_api = Blueprint('callback_api', __name__)

@callback_api.route("/callback", methods=['POST'])
def callback():
    MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo = MongoClient(MONGO_URL)["localdb"]

    error_json = json.loads('{"status": 400, "message": "An error occured!"}')

    if request.form.get("collection"): collection = request.form.get("collection")
    if request.form.get("_id"): _id = request.form.get("_id")

    doc = mongo[collection].find_one({"_id": ObjectId(_id)})
    
    if doc:
        try:
            data_json = json.loads(doc["data"].decode('utf8'))
            return json.dumps(data_json, indent=4)
        except:
            return doc["data"].decode('utf8')
    else:
        return json.dumps(error_json)
