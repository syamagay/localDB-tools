from configs.imports import *

retrieve_config_api = Blueprint('retrieve_config_api', __name__)

@retrieve_config_api.route('/retrieve/config', methods=['GET'])
def retrieve_config():
    localdb = LocalDB.getMongo().db
    fs = gridfs.GridFS(localdb)

    get_list = {}

    cmp_oid = request.args['component']
    config = request.args['configType']
    run_oid = request.args['testRun']

    return_json = {}

    query = { 
        'component': cmp_oid,
        'testRun': run_oid 
    }
    this_ctr = localdb.componentTestRun.find_one(query)
    if not this_ctr:
        return_json = {
            'message': 'Not found test data: component: {0}, run: {1}'.format( cmp_oid, run_oid ),
            'error': True
        }
        return jsonify(return_json)
    if config == 'ctrl' or config == 'scan':
        query = { '_id': ObjectId(run_oid) }
        this_run = localdb.testRun.find_one(query)
    elif config == 'after' or config  == 'before':
        this_run = this_ctr
    else:
        return_json = {
            'message': 'Not exist config type: {}'.format( config ),
            'error': True
        }
        return jsonify(return_json)

    if this_run['{}Cfg'.format(config)] == '...':
        return_json.update({ 'data': 'Not found', 'write': False })
    else:
        query = { '_id': ObjectId(this_run['{}Cfg'.format(config)]) }
        this_cfg = localdb.config.find_one(query)
        return_json.update({ 
            'data': 'Found',
            'write': True,
            'config': json.loads(fs.get(ObjectId(this_cfg['data_id'])).read().decode('ascii')),
            'filename': this_cfg['filename'],
        }) 

    return jsonify(return_json)
