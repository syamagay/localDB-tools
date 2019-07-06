from configs.imports import *

retrieve_component_api = Blueprint('retrieve_component_api', __name__)

@retrieve_component_api.route('/retrieve/component', methods=['GET'])
def retrieve_component():
    MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo = MongoClient(MONGO_URL)["localdb"]

    serial_number = request.args.get('serialNumber', None)
    return_json = {}
    if not serial_number:
        return_json = {
            'message': 'Not provide serial number',
            'error': True
        }
        return jsonify(return_json)

    query = { 'serialNumber': serial_number }
    this_cmp = mongo.component.find_one(query)
    if not this_cmp:
        return_json = {
            'message': 'Not found component data: {}'.format(serial_number),
            'error': True
        }
        return jsonify(return_json)

    query = { 'parent': str(this_cmp['_id']) }
    children = mongo.childParentRelation.find(query)
    return_json['componentType'] = this_cmp['componentType']
    return_json['chipType'] = this_cmp['chipType']
    return_json.update({ 'chips': [] })
    if children:
        for child in children:
            query = { '_id': ObjectId(child['child']) }
            this_cmp = mongo.component.find_one(query)
            return_json['chips'].append({
                'component': child['child'],
                'chipId': child['chipId'],
                'serialNumber': this_cmp['serialNumber']
            })
    else:
        return_json['chips'].append({
            'component': str(this_cmp['_id']),
            'chipId': this_cmp['chipId'],
            'serialNumber': this_cmp['serialNumber']
        })

    return jsonify(return_json)
