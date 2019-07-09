from configs.imports import *

retrieve_testrun_api = Blueprint('retrieve_testrun_api', __name__)

@retrieve_testrun_api.route('/retrieve/testrun', methods=['GET'])
def retrieve_testrun():
    def setTime(date):
        zone = session.get('timezone','UTC')
        converted_time = date.replace(tzinfo=timezone.utc).astimezone(pytz.timezone(zone))
        time = converted_time.strftime('%Y/%m/%d %H:%M:%S')
        return time

    MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo = MongoClient(MONGO_URL)["localdb"]

    serial_number = request.args.get('serialNumber', None)
    run_id = request.args.get('testRun', None)
    return_json = {}
    if not serial_number and not run_id:
        return_json = {
            'message': 'Not provide serial number or test data id',
            'error': True
        }
        return jsonify(return_json)

    if run_id:
        query = { '_id': ObjectId(run_id) }
        this_run = mongo.testRun.find_one(query)
        if not this_run:
            return_json = {
                'message': 'Not found test data: {}'.format(run_id),
                'error': True
            }
            return jsonify(return_json)
     
    elif serial_number:
        query = { 'serialNumber': serial_number }
        this_cmp = mongo.component.find_one(query)
        if not this_cmp:
            return_json = {
                'message': 'Not found component data: {}'.format(serial_number),
                'error': True
            }
            return jsonify(return_json)

    if run_id:
        query = { 'testRun': run_id }
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
    query = { '_id': ObjectId(this_run['testRun']) }
    this_testrun = mongo.testRun.find_one(query)
    query = { '_id': ObjectId(this_testrun['user_id']) }
    this_user = mongo.user.find_one(query)
    query = { '_id': ObjectId(this_testrun['address']) }
    this_site = mongo.institution.find_one(query)
    query = { 'testRun': this_run['testRun'] }
    run_entries = mongo.componentTestRun.find(query)
    return_json = {
        'testRun': this_run['testRun'],
        'runNumber': this_run['runNumber'],
        'testType': this_run['testType'],
        'datetime': setTime(this_testrun['startTime']),
        'serialNumber': this_testrun['serialNumber'],
        'user': this_user['userName'],
        'site': this_site['institution'],
        'geomId': {},
        'tx': {},
        'rx': {}
    }
    for run in run_entries:
        return_json['geomId'][run['component']] = run['geomId']
        return_json['tx'][run['component']] = run['tx']
        return_json['rx'][run['component']] = run['rx']
 
    return jsonify(return_json)
