from configs.imports import *

retrieve_remote_api = Blueprint('retrieve_remote_api', __name__)

@retrieve_remote_api.route('/retrieve/remote', methods=['GET'])
def retrieve_remote():
    MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo = MongoClient(MONGO_URL)["localdb"]

    return_json = { 'modules': [] }
    query = { 'componentType': 'Module' }
    module_entries = mongo.component.find(query)
    for module in module_entries:
        if not module['serialNumber'] == '':
            return_json['modules'].append(module['serialNumber'])

    return jsonify(return_json)
