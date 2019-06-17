#!/usr/bin/env python3
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Verify integrity of data in DB
#################################

from imports.imports import * # Omajinai

def verify():
    # Get username and hostname
    user = os.environ["USER"]
    hostname = os.environ["HOSTNAME"]
    mac = get_mac()
#    mac_add = "".join(c + ":" if i % 2 else c for i, c in enumerate(hex(mac)[2:].zfill(12)))[:-1]

    args = getArgs()

    # DB
    local_url = "mongodb://localhost"
    if args.username is None:
        local_url = "mongodb://" + args.host + ":" + str(args.port)
    else:
        local_url = "mongodb://" + args.username + ":" + args.password + "@" + args.host + ":" + str(args.port) + "/localdb"
    print(local_url)
    client = MongoClient(local_url)
    db = client["olddb"]

    ##
    # Get modules info
    query = {"componentType": "Module"}
    modules = db.component.find(query)
    nmodules = modules.count()
    print("Found " + str(nmodules) + " modules!")#count of the module number
    
    module_cnt = 1
    for module in modules:
        print("Verifying for module " + module["serialNumber"] + " (" + str(module_cnt) + "/" + str(nmodules) + ") ...")
        # Get child chips
        query = {"parent": str(module['_id'])}
        cprelations = db.childParentRelation.find(query)
        total_scans = 0
        for cprelation in cprelations:
            # Get child chips info
            query = {"_id": ObjectId(cprelation['child'])}
            chip = db.component.find_one(query) # Find child component

            # Get testRun links
            query = {"component": str(chip['_id'])}
            componentTestRuns = db.componentTestRun.find(query)
            # Get # of testRuns
            total_scans += componentTestRuns.count()

        query = {"parent": str(module['_id'])}
        cprelations = db.childParentRelation.find(query)
        scan_cnt_offset = 0
        defects = []
        for cprelation in cprelations:
            # Get child chips info
            query = {"_id": ObjectId(cprelation['child'])}
            chip = db.component.find_one(query) # Find child component

            # Get testRun links
            query = {"component": str(chip['_id'])}
            componentTestRuns = db.componentTestRun.find(query)
            scan_cnt = 0
            for componentTestRun in componentTestRuns:
                # Get testRun info
                query = {"_id": ObjectId(componentTestRun['testRun'])}
                testRun = db.testRun.find_one(query) # Find one test run

                for attachment in testRun["attachments"]:
                    query = {"_id" : ObjectId(attachment["code"])}
                    fsfile = db.fs.files.find_one(query)
                    if not fsfile:
                        defects.append({"collection": "fs.files", "_id": attachment["code"]})
                        #print("No fs file found! '_id': " + attachment["code"] + attachment["filename"] + attachment["contentType"])
                    query = {"files_id" : ObjectId(attachment["code"])}
                    fschunk = db.fs.chunks.find_one(query)
                    if not fschunk:
                        defects.append({"collection": "fs.chunks", "files_id": attachment["code"]})
                        #print("No fs file found! '_id': " + attachment["code"] + attachment["filename"] + attachment["contentType"])

                scan_cnt += 1
                printProgressBar(scan_cnt_offset+scan_cnt, total_scans, prefix = 'Progress verify data', suffix = 'Complete')

            scan_cnt_offset += scan_cnt

        module_cnt += 1

        if len(defects) != 0:
            print("\tFound defects!")
            print(defects)

        ## End of modules loop

if __name__ == '__main__': verify()
