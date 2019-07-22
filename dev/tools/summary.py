#!/usr/bin/env python3
# -*- coding: utf-8 -*
##################################
## Author1: Eunchong Kim (eunchong.kim at cern.ch)
## Copyright: Copyright 2019, ldbtools
## Date: Jul. 2019
## Project: Local Database Tools
## Description: Summary tool
##################################

from configs.imports import * # Omajinai
from configs.route import * # Omajinai
TOOLNAME = "[SUMMARYTOOL] "

def summary():
    args = getArgs()
    logging.info(args.dbVersion)

    mongo = MongoClient("mongodb://%s:%d" % (args.host, args.port) )
    db = mongo['localdb']

    # Basic info
    logging.info("[LocalDB] DB summary")
    table = PrettyTable(["Collection name", "# of documents"])
    collection_names = db.collection_names()
    for collection_name in collection_names:
        cnt = db[collection_name].find().count()
        table.add_row([collection_name, cnt])
    print(table)

    # Get modules info
    logging.info("[LocalDB] Each module summary")
    table_module = PrettyTable(["# of modules", "# of tests"])
    table_all = PrettyTable(["Module S/N", "Chip type", "Chip S/N", "# of Tests", "# of files"])
    query = {"componentType": "Module"}
    modules = db.component.find(query)
    for module in modules:
        first_add_row = True
        # Get child chips
        query = {"parent": str(module['_id'])}
        cprelations = db.childParentRelation.find(query)
        for cprelation in cprelations:
            # Get child chips info
            query = {"_id": ObjectId(cprelation['child'])}
            chip = db.component.find_one(query) # Find child component

            # Get testRun links
            query = {"component": str(chip['_id'])}
            componentTestRuns = db.componentTestRun.find(query)
            attachments_cnt = 0
            for componentTestRun in componentTestRuns:
                # Get testRun info
                query = {"_id": ObjectId(componentTestRun['testRun'])}
                testRun = db.testRun.find_one(query) # Find one test run
                attachments_cnt += len(testRun["attachments"])

            if first_add_row:
                table_all.add_row([module["serialNumber"], chip["componentType"], chip["serialNumber"], componentTestRuns.count(), attachments_cnt])
                first_add_row = False
            else:
                table_all.add_row(["", chip["componentType"], chip["serialNumber"], componentTestRuns.count(), attachments_cnt])
        table_all.add_row(["", "", "", "", ""])
    print(table_all)
#                #print("\t\t"+testRun_entry['testType'].ljust(32)+testRun_entry['sys']['cts'].strftime("%Y/%m/%d-%H:%M:%S")+' '+str(testRun_entry['runNumber']).ljust(8))
#
#                j = testRun_entry["runNumber"]
#                # if duplicated
#                if i == j:
#                    print("duplicated run#: "+str(i))
#                    # find attachment and delete
#                    for attachment in testRun_entry['attachments']:
#                        query = {"files_id": ObjectId(attachment['code'])}
#                        chunk = db.fs.chunks.find_one(query)
#                        query = {"_id": ObjectId(attachment['code'])}
#                        file = db.fs.files.find_one(query)
#
#                    # delete duplicated testRun and componentTestRun
#                    query = {"_id": ObjectId(ctr_entry['testRun'])}
#                    query = {"testRun": ctr_entry['testRun']}
#
#                i=j

if __name__ == '__main__': summary()
