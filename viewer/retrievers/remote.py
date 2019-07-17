from configs.imports import *

retrieve_remote_api = Blueprint('retrieve_remote_api', __name__)

@retrieve_remote_api.route('/retrieve/remote', methods=['GET'])
def retrieve_remote():
    localdb = LocalDB.getMongo().db

    return_json = { 'modules': [] }
    query = { 'componentType': 'Module' }
    module_entries = localdb.component.find(query)
    for module in module_entries:
        if not module['serialNumber'] == '':
            return_json['modules'].append(module['serialNumber'])

    return jsonify(return_json)
