from configs.imports import *

retrieve_testrun_api = Blueprint('retrieve_testrun_api', __name__)

@retrieve_testrun_api.route('/retrieve/testrun', methods=['GET'])
def retrieve_testrun():
    def setTime(date):
        zone = session.get('timezone','UTC')
        converted_time = date.replace(tzinfo=timezone.utc).astimezone(pytz.timezone(zone))
        time = converted_time.strftime('%Y/%m/%d %H:%M:%S')
        return time

    localdb = LocalDB.getMongo().db

    run_id = request.args.get('testRun', None)
    return_json = {}

    query = { '_id': ObjectId(run_id) }
    this_run = localdb.testRun.find_one(query)

    query = { '_id': ObjectId(this_run['user_id']) }
    this_user = localdb.user.find_one(query)
    query = { '_id': ObjectId(this_run['address']) }
    this_site = localdb.institution.find_one(query)
    query = { 'testRun': run_id }
    run_entries = localdb.componentTestRun.find(query)
    return_json = {
        'testRun': run_id,
        'runNumber': this_run['runNumber'],
        'testType': this_run['testType'],
        'datetime': setTime(this_run['startTime']),
        'serialNumber': this_run['serialNumber'],
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
