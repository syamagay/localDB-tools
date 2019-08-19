from configs.imports import *

retrieve_testrun_api = Blueprint('retrieve_testrun_api', __name__)

@retrieve_testrun_api.route('/retrieve/testrun', methods=['GET'])
def retrieve_testrun():
    def setTime(date):
        zone = session.get('timezone','UTC')
        converted_time = date.replace(tzinfo=timezone.utc).astimezone(pytz.timezone(zone))
        time = converted_time.strftime('%Y/%m/%d %H:%M:%S')
        return time

    localdb = LocalDB.getDB()

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
        'chips': {
            'serialNumber': {},
            'chipId': {},
            'geomId': {},
            'tx': {},
            'rx': {}
        }
    }
    for i, run in enumerate(run_entries):
        try:
            query = { '_id': ObjectId(run['component']) }
            this_cmp = localdb.component.find_one(query)
            ch_serial_number = this_cmp['serialNumber']
            ch_id = this_cmp['chipId']
        except:
            ch_serial_number = run['component']
            ch_id = run.get('chipId',-1)

        return_json['chips']['serialNumber'][run['component']] = ch_serial_number
        return_json['chips']['chipId'][run['component']] = ch_id
        return_json['chips']['geomId'][run['component']] = run.get('geomId', i+1)
        return_json['chips']['tx'][run['component']] = run['tx']
        return_json['chips']['rx'][run['component']] = run['rx']
 
    return jsonify(return_json)
