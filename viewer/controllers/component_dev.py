from configs.imports import *

component_dev_api = Blueprint('component_dev_api', __name__)

# component page 
@component_dev_api.route("/component_dev", methods=['GET', 'POST'])
def show_component_dev():
    MONGO_URL = 'mongodb://' + args.host + ':' + str(args.port) 
    mongo = MongoClient(MONGO_URL)["localdb"]
    print(mongo.collection_name())

    make_dir()

    session['this']  = request.args.get( 'id' )
    session['code']  = request.args.get( 'code', '' )
    session['runId'] = request.args.get( 'runId' )

    # this component
    query = { '_id': ObjectId(session['this']) }
    thisComponent = mongo.db.component.find_one( query )
    print(thisComponent)
    componentType = thisComponent['componentType']

    # chips and parent
    if componentType == 'Module':
        ParentId = session['this']
    else:
        query = { 'child': session['this'] }
        thisCPR = mongo.db.childParentRelation.find_one( query )
        ParentId = thisCPR['parent']

    # this module
    query = { '_id': ObjectId(ParentId) }
    thisModule = mongo.db.component.find_one( query )

    # chips of module
    query = { 'parent': ParentId }
    child_entries = mongo.db.childParentRelation.find( query )

    # fill chip and module information
    component = {}
    component_chips = []
    component['chipType'] = thisComponent['chipType']
    for child in child_entries:
        query = { '_id': ObjectId(child['child']) }
        thisChip = mongo.db.component.find_one( query )
        component_chips.append({ '_id'         : child['child'],
                                 'serialNumber': thisChip['serialNumber'] })

    module = { '_id'         : ParentId,
               'serialNumber': thisModule['serialNumber'] }
    
    # fill photos
    photoDisplay = []
    photoIndex = []
    photos = {}
    #photoDisplay = fill_photoDisplay( thisComponent )            #TODO
