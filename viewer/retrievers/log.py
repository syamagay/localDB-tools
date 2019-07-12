from configs.imports import *

retrieve_log_api = Blueprint('retrieve_log_api', __name__)

@retrieve_log_api.route('/retrieve/log', methods=['GET'])
def retrieve_log():
    def setTime(date):
        zone = session.get('timezone','UTC')
        converted_time = date.replace(tzinfo=timezone.utc).astimezone(pytz.timezone(zone))
        time = converted_time.strftime('%Y/%m/%d %H:%M:%S')
        return time

    MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo = MongoClient(MONGO_URL)["localdb"]

    return_json = {}

    run_query = {}
    if 'serialNumber' in request.args: 
        query = { 'serialNumber': request.args['serialNumber'] }
        this_cmp = mongo.component.find_one( query )
        if not this_cmp:
            return_json = {
                'message': 'Not found component data: {}'.format(request.args['serialNumber']),
                'error': True
            }
            return jsonify(return_json)
        run_query.update({ 'component': str(this_cmp['_id']) })
    test_info_list = [ 'testType', 'runNumber' ]
    for test_info in test_info_list:
        if test_info in request.args:
            run_query.update({ test_info: request.args[test_info] }) 

    run_entries = mongo.componentTestRun.find( run_query )
    runids = []
    for run_entry in run_entries:
        runids.append({ '_id': ObjectId(run_entry['testRun']) })

    log_query = { '$or': runids } 

    if 'userName' in request.args:
        query = { 'userName': request.args['userName'] }
        this_user = mongo.user.find_one( query )
        if not this_user:
            return_json = {
                'message': 'Not found user data: {}'.format(request.args['userName']),
                'error': True
            }
            return jsonify(return_json)
        log_query.update({ 'user_id': str(this_user['_id']) })
    if 'site' in request.args:
        query = { 'institution': request.args['site'] }
        this_site = mongo.user.find_one( query )
        if not this_site:
            return_json = {
                'message': 'Not found site data: {}'.format(request.args['site']),
                'error': True
            }
            return jsonify(return_json)
        log_query.update({ 'address': str(this_site['_id']) })

    limit = request.args.get('limit',100)
    run_entries = mongo.testRun.find( log_query ).sort([( '$natural', -1 )] ).limit(limit)

    return_json = { 'log': [] }
    for run_entry in run_entries:
        query = { '_id': ObjectId(run_entry['user_id']) }
        this_user = mongo.user.find_one( query )
        query = { '_id': ObjectId(run_entry['address']) }
        this_site = mongo.institution.find_one( query )
        test_data = {
            'user': this_user['userName'],
            'site': this_site['institution'],
            'datetime': setTime(run_entry['startTime']),
            'runNumber': run_entry['runNumber'],
            'testType': run_entry['testType'],
            'runId': str(run_entry['_id']),
            'serialNumber': run_entry['serialNumber']
        }
        return_json['log'].append(test_data)

    return jsonify(return_json)
