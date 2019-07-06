from configs.imports import *

retrieve_testrun_api = Blueprint('retrieve_testrun_api', __name__)

@retrieve_testrun_api.route('/retrieve/testrun', methods=['GET'])
def retrieve_testrun():
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

    run_id = request.args.get('testRun', None)

    if run_id:
        query = { 'component': str(this_cmp['_id']), 'testRun': run_id }
    else:
        query = { 'component': str(this_cmp['_id']) }
    run_entries = mongo.componentTestRun.find(query).sort([( '$natural', -1 )] )
    this_run = None
    for run in run_entries:
        this_run = run
        break
    if not this_run:
        return_json = {
            'message': 'Not exist test data of the component: {}'.format(serial_number),
            'error': True
        }
        return jsonify(return_json)
    query = { 'testRun': this_run['testRun'] }
    run_entries = mongo.componentTestRun.find(query)
    return_json = {
        'testRun': this_run['testRun'],
        'geomId': {},
        'tx': {},
        'rx': {}
    }
    for run in run_entries:
        return_json['geomId'][run['component']] = run['geomId']
        return_json['tx'][run['component']] = run['tx']
        return_json['rx'][run['component']] = run['rx']
 
    return jsonify(return_json)
