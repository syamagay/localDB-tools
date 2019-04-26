#!/usr/bin/env python3
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Sync servers
#   The config file path: /etc/mongo.d/mongosync.conf
#################################

from imports import * # Omajinai

def sync():
    # Get username and hostname
    user = os.environ["USER"]
    hostname = os.environ["HOSTNAME"]
    mac = get_mac()
#    mac_add = "".join(c + ":" if i % 2 else c for i, c in enumerate(hex(mac)[2:].zfill(12)))[:-1]

    args = getArgs()

    # URLs
    if not args.host or not args.port or not args.mhost or not args.mport:
        print(TOOLNAME+"ERROR! Local/Master host/port are not set!")
        exit(1)
    local_url = "mongodb://" + args.host + ":" + str(args.port)
    master_url = "mongodb://" + args.mhost + ":" + str(args.mport)
    print(TOOLNAME+"LocalDB server is: " + local_url)
    print(TOOLNAME+"Master server is: " + master_url)

    # Local or Master
    server_names = ["Local", "Master"]

    # Clients and DBs
    clients = [MongoClient(local_url), MongoClient(master_url)]
    dbs = [clients[0]["yarrdb"], clients[1]["yarrdb"]]
    dbs_sync = [clients[0]["ldbtool"], clients[1]["ldbtool"]]

    # Set default time
    last_time_default = dateutil.parser.parse("2000-7-20T1:00:00.000Z")

    # Get collection names from master server
    collection_names = dbs[1].collection_names()

    # Get sync data from master
    query = {"mac": mac} # TODO, This key will be changed
    sync_doc = dbs_sync[1]["sync"].find_one(query, sort=[("datetime", -1)])

    # Sync
    datetimes = []
    for collection_name in collection_names:
        if "fs.chunks" == collection_name: continue # Treat fs.chunks with fs.files

        print(TOOLNAME+"Collection: " + collection_name)

        # Get last sync datetime
        last_time = last_time_default
        if sync_doc:
            last_time = sync_doc[collection_name]["datetime"]
            print("\tLast sync time is: " + str(last_time))

        # Set key of datetime
        query_key = ""
        if not "fs" in collection_name:
            query_key = "sys.mts"
        elif "fs.files" in collection_name:
            query_key = "uploadDate"

        # Get lastest datetime from data
        temp_datetimes = []
        for i in range(2):
            doc_last = dbs[i][collection_name].find_one(sort=[(query_key, -1)])
            if doc_last:
                if not "fs" in collection_name:
                    temp_datetimes.append(doc_last["sys"]["mts"])
                elif "fs.files" in collection_name:
                    temp_datetimes.append(doc_last["uploadDate"])
        if temp_datetimes[0] < temp_datetimes[1]:
            datetimes.append(temp_datetimes[1])
        else:
            datetimes.append(temp_datetimes[0])

        # Get doc _id to be copy to Master(Local) from Local(Master)
        documents = []
        totals = []
        for i in range(2):
            documents.append(dbs[i][collection_name].find({query_key: {"$gt": last_time} }))
            totals.append(documents[i].count())
            print("\t" + server_names[i] + " has " + str(totals[i]) + " documents ahead")


        if not args.y: continue

        # Sync
        x = [0, 1]
        y = [1, 0]
        for i in range(2): # Copy from local first, then copy from Master
            if totals[x[i]] == 0: continue

            dup_count = 0
            count = 0
            # Copy docs to
            for document in documents[x[i]]:
                doc_dup = dbs[y[i]][collection_name].find_one({"_id": document["_id"]})
                if doc_dup:
                    if not doc_dup == document:
                        if i == 1: # Copy from Master
#                            dbs[y[i]][collection_name].update({"_id": document["_id"]}, document) # Overwrite
                            dup_count += 1
                else:
#                    dbs[y[i]][collection_name].insert(document)
                    if "fs.files" in collection_name:
                        chunks_doc = dbs[x[i]]["fs.chunks"].find_one({"files_id": document["_id"]}) # Find linked doc in fs.chunks
#                        if chunks_doc: dbs[y[i]]["fs.chunks"].insert(chunks_doc)
                count += 1
                printProgressBar(count, totals[x[i]], prefix = '        Progress copy from ' + server_names[x[i]], suffix = 'Complete')

            if dup_count != 0:
                print("\t\tFound " + str(dup_count) + " dup docs")

    # Last
    if not args.y: return

    # Finish
    query = {"user": user, "hostname": hostname, "mac": mac, "sys": {"rev": 0, "cts": datetime.datetime.now(), "mts": datetime.datetime.now()}}
    index = 0
    for collection_name in collection_names:
        if "fs.chunks" == collection_name:
            index = index - 1
            continue # Treat fs.chunks with fs.files
        query[collection_name] = {"datetime": datetimes[index]}
    pprint.PrettyPrinter(indent=4).pprint(query)
#    for i in range(2):
#        dbs_sync[x[i]]["sync"].insert_one(query)

if __name__ == '__main__': sync()
