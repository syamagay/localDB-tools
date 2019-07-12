from configs.imports import *

retrieve_log_api = Blueprint('retrieve_log_api', __name__)

@retrieve_log_api.route('/retrieve/log', methods=['GET'])
def retrieve_log():
    def setTime(date):
        zone = session.get('timezone','UTC')
        converted_time = date.replace(tzinfo=timezone.utc).astimezone(pytz.timezone(zone))
        time = converted_time.strftime('%Y/%m/%d %H:%M:%S')
        return time

    localdb = LocalDB.getMongo().db
    return_json = {}

    run_query = {}
    log_query = {}
    if request.args['dummy'] == True:
        log_query.update({'dummy': True})
    elif request.args.get('serialNumber',None): 
        query = { 'serialNumber': request.args['serialNumber'] }
        this_cmp = localdb.component.find_one( query )
        if not this_cmp:
            return_json = {
                'message': 'Not found component data: {}'.format(request.args['serialNumber']),
                'error': True
            }
            return jsonify(return_json)
        run_query.update({ 'component': str(this_cmp['_id']) })

    if not run_query == {}:
        run_entries = localdb.componentTestRun.find(run_query)
        run_oids = []
        for run_entry in run_entries:
            run_oids.append({ '_id': ObjectId(run_entry['testRun']) })
        log_query.update({ '$or': run_oids })

    if request.args.get('user',None):
        query = { 'userName': request.args['user'] }
        this_user = localdb.user.find_one( query )
        if not this_user:
            return_json = {
                'message': 'Not found user data: {}'.format(request.args['user']),
                'error': True
            }
            return jsonify(return_json)
        log_query.update({ 'user_id': str(this_user['_id']) })

    if request.args.get('site',None):
        query = { 'institution': request.args['site'] }
        this_site = localdb.user.find_one( query )
        if not this_site:
            return_json = {
                'message': 'Not found site data: {}'.format(request.args['site']),
                'error': True
            }
            return jsonify(return_json)
        log_query.update({ 'address': str(this_site['_id']) })

    run_entries = localdb.testRun.find( log_query ).sort([( '$natural', -1 )])

    return_json = { 'log': [] }
    for run_entry in run_entries:
        query = { '_id': ObjectId(run_entry['user_id']) }
        this_user = localdb.user.find_one( query )
        query = { '_id': ObjectId(run_entry['address']) }
        this_site = localdb.institution.find_one( query )
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
