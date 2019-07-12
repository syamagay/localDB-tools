from configs.imports import *

retrieve_component_api = Blueprint('retrieve_component_api', __name__)

@retrieve_component_api.route('/retrieve/component', methods=['GET'])
def retrieve_component():
    localdb = LocalDB.getMongo().db
    return_json = {}

    run_oid = None
    if request.args.get('dummy',False)==True:
        query = { 'dummy': True }
        run_entry = localdb.testRun.find(query).sort([( '$natural', -1 )]).limit(1)
        if not run_entry.count()==0:
            run_oid = str(run_entry[0]['_id'])
            serialnumber = run_entry[0]['serialNumber']
    elif request.args.get('testRun',None):
        query = { 'testRun': request.args['testRun'] }
        this_run = localdb.componentTestRun.find_one(query) 
        if this_run:
            run_oid = request.args['testRun']
            query = { '_id': ObjectId(run_oid) }
            this_run = localdb.testRun.find_one(query)
            serialnumber = this_run['serialNumber']
    elif request.args.get('serialNumber',None):
        query = { 'serialNumber': request.args['serialNumber'] }
        this_cmp = localdb.component.find_one(query)
        if this_cmp:
            serialnumber = request.args['serialNumber']
            query = { 'component': str(this_cmp['_id']) }
            run_entry = localdb.componentTestRun.find(query).sort([( '$natural', -1 )]).limit(1)
            if not run_entry.count()==0:
                run_oid = run_entry[0]['testRun']
    else:
        run_entry = localdb.testRun.find({}).sort([( '$natural', -1 )]).limit(1)
        if not run_entry.count()==0:
            run_oid = str(run_entry[0]['_id'])
            serialnumber = run_entry[0]['serialNumber']

    if not run_oid:
        if serialnnumber:
            return_json = {
                'message': 'Not exist test data of the component: {}'.format(serialnumber),
                'error': True
            }
        else:
            return_json = {
                'message': 'Not exist test data',
                'error': True
            }
        return jsonify(return_json)

    query = { 'serialNumber': serialnumber }
    this_cmp = localdb.component.find_one(query)
    if this_cmp: cmp_oid = str(this_cmp['_id'])
    else:        cmp_oid = serialnumber

    query = { '_id': ObjectId(run_oid) }
    this_run = localdb.testRun.find_one(query)
    chip_data = []
    if this_run['serialNumber'] == serialnumber:
        component_type = 'Module'
        chip_type = this_run['chipType']
        query = { 'testRun': run_oid, 'component': {'$ne': cmp_oid} }
        ctr_entries = localdb.componentTestRun.find(query)
        for ctr in ctr_entries:
            chip_data.append({ 'component': ctr['component'] })
    else:
        component_type = 'Front-end Chip'
        chip_type = this_run['chipType']
        chip_data.append({ 'component': cmp_oid })

    if chip_type == 'FE-I4B': chip_type = 'FEI4B'

    query = { '_id': ObjectId(this_run['user_id']) }
    this_user = localdb.user.find_one(query)

    query = { '_id': ObjectId(this_run['address']) }
    this_site = localdb.institution.find_one(query)

    return_json = {
        'testRun':       run_oid,
        'component':     cmp_oid,
        'componentType': component_type,
        'chipType':      chip_type,
        'chips':         chip_data,
        'user':          this_user['userName'],
        'sute':          this_site['institution']
    }

    return jsonify(return_json)
