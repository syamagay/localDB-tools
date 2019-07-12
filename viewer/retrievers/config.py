from configs.imports import *

retrieve_config_api = Blueprint('retrieve_config_api', __name__)

@retrieve_config_api.route('/retrieve/config', methods=['GET'])
def retrieve_config():
    MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo = MongoClient(MONGO_URL)["localdb"]

    get_list = {}

    get_list['component'] = request.args.get('component', None)
    get_list['configType'] = request.args.get('configType', None)
    get_list['testRun'] = request.args.get('testRun', None)

    return_json = {}

    for get_key in get_list:
        if not get_list[get_key]:
            return_json = {
                'message': 'Not provide {} value'.format(get_key),
                'error': True
            }
            return jsonify(return_json)

    query = { 
        'component': get_list['component'],
        'testRun': get_list['testRun']
    }
    this_ctr = mongo.componentTestRun.find_one(query)
    if not this_ctr:
        return_json = {
            'message': 'Not found test data: component: {0}, run: {1}'.format( get_list['component'], get_list['testRun'] ),
            'error': True
        }
        return jsonify(return_json)
    if get_list['configType'] == 'ctrl' or get_list['configType'] == 'scan':
        query = { '_id': ObjectId(get_list['testRun']) }
        this_run = mongo.testRun.find_one(query)
    elif get_list['configType'] == 'after' or get_list['configType'] == 'before':
        this_run = this_ctr
    else:
        return_json = {
            'message': 'Not exist config type: {}'.format( get_list['configType'] ),
            'error': True
        }
        return jsonify(return_json)

    if this_run['{}Cfg'.format(get_list['configType'])] == '...':
        return_json.update({ 'data': 'Not found', 'write': False })
    else:
        query = { '_id': ObjectId(this_run['{}Cfg'.format(get_list['configType'])]) }
        this_cfg = mongo.config.find_one(query)
        return_json.update({ 
            'data': 'Found',
            'write': True,
            'config': json.loads(fs.get(ObjectId(this_cfg['data_id'])).read().decode('ascii')),
            'filename': this_cfg['filename'],
        }) 

    return jsonify(return_json)
