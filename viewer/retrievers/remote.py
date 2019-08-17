from configs.imports import *

retrieve_remote_api = Blueprint('retrieve_remote_api', __name__)

@retrieve_remote_api.route('/retrieve/remote', methods=['GET'])
def retrieve_remote():
    localdb = LocalDB.getDB()

    return_json = { 'modules': [] }
    query = { 'componentType': 'Module' }
    module_entries = localdb.component.find(query)
    for component in module_entries:
        if component['serialNumber'] == '': continue
        module = {}
        module['serialNumber'] = component['serialNumber'] 
        module['componentType'] = component['componentType']
        module['chipType'] = component['chipType']
        query = { 'parent': str(component['_id']) }
        child_entries = localdb.childParentRelation.find(query)
        module['chips'] = []
        for child in child_entries:
            query = { '_id': ObjectId(child['child']) }
            this_chip = localdb.component.find_one(query)
            chip = {}
            chip['serialNumber'] = this_chip['serialNumber']
            chip['componentType'] = this_chip['componentType']
            chip['chipId'] = this_chip['chipId']
            module['chips'].append(chip)
        return_json['modules'].append(module)

    return jsonify(return_json)
