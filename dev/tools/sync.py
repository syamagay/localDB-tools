#!/usr/bin/env python3
# -*- coding: utf-8 -*
##################################
## Author1: Eunchong Kim (eunchong.kim at cern.ch)
## Copyright: Copyright 2019, ldbtools
## Date: Jul. 2019
## Project: Local Database Tools
## Description: Sync tool
##################################

from configs.imports import * # Omajinai
from configs.route import * # Omajinai

def sync():
    TOOLNAME = "[SYNCTOOL] "

    #================================================================================
    #
    #                               Private methods
    #
    #================================================================================
    # status
    def __status():
        FUNCNAME = "STATUS\t"

        commit_cnt = __pull(True)
        logging.info(TOOLNAME + FUNCNAME + "You have " + str(commit_cnt) + " commits to pull!")

        doc_cnt = __commit(True)
        logging.info(TOOLNAME + FUNCNAME + "You have " + str(doc_cnt) + " documents to commit!")

    # construct query
    def __query():
        return {"sys": {"rev": 0, "cts": current_datetime, "mts": current_datetime}}

    #================================
    # commit
    #================================
    def __commit(is_status = False):
        # Get last commit
        query = {"local_server_name": my_doc["server"]["name"]}
        commit_doc = dbs_sync["local"]["commits"].find_one(query, sort=[("sys.cts", -1)])

        # Get last commit datetime
        last_sync_datetime = last_sync_datetime_default
        if commit_doc: last_sync_datetime = commit_doc["sys"]["cts"]
        logging.info(TOOLNAME + "Last sync time is: " + str(last_sync_datetime))

        # Construct query for commit
        query = __query()
        query["local_server_name"] = my_doc["server"]["name"]
        if commit_doc: query["parent"] = commit_doc["_id"]
        else: query["parent"] = "bottausshiwasshi"
        query["description"] = "commit"

        # Add _id each collection
        is_empty = True
        doc_cnt = 0
        for collection_name in collection_names:
            if "fs.chunks" == collection_name: continue # Treat fs.chunks with fs.files

            query_key = ""
            if not "fs" in collection_name:
                query_key = "sys.mts"
            elif "fs.files" in collection_name:
                query_key = "uploadDate"
            documents = dbs["local"][collection_name].find({query_key: {"$gt": last_sync_datetime} })
            ids = []
            for document in documents: ids.append(document["_id"])

            temp_collection_name = collection_name.replace(".", "_") # key cannot contain '.'. i.e. 'fs.files' --> 'fs_files'
            query[temp_collection_name] = ids
            if len(ids) is not 0:
                is_empty = False
                doc_cnt += len(ids)

        # For status
        if is_status:
            return doc_cnt

        # Insert object
        if is_empty:
            logging.info(TOOLNAME + "Nothing to commit!")
        else:
            #pprint.PrettyPrinter(indent=4).pprint(query) ## debug
            oid = dbs_sync["local"]["commits"].insert(query)
            logging.info(TOOLNAME + "Finished commit! The oid is " + str(oid))

    # fetch
    def __fetch():
        # Download commits
        commit_docs = dbs_sync["master"]["commits"].find()
        commit_cnt = 0
        for doc in commit_docs:
            doc_dup = dbs_sync["local"]["commits"].find_one({"_id": doc["_id"]})
            if not doc_dup:
                dbs_sync["local"]["commits"].insert(doc)
                commit_cnt += 1
        logging.info(TOOLNAME + "Downloaded " + str(commit_cnt) + " commits from master server")

        # Download refs
        ref_docs = dbs_sync["master"]["refs"].find()
        ref_cnt = 0
        for doc in ref_docs:
            doc_dup = dbs_sync["local"]["refs"].find_one({"_id": doc["_id"]})
            if not doc_dup:
                dbs_sync["local"]["refs"].insert(doc)
                ref_cnt += 1
            else:
                if doc_dup != doc:
                    dbs_sync["local"]["refs"].update({"_id": doc["_id"]}, doc)
                    ref_cnt += 1
        logging.info(TOOLNAME + "Downloaded " + str(ref_cnt) + " refs from master server")

    # pull
    def __push_one_way():
        print("to be continued...")

    def __pull_of_push_from_commit(pull_or_push, commit_doc, log_doc):
        copy_from = ""
        copy_to = ""
        if pull_or_push == "pull":
            copy_from = "master"
            copy_to = "local"
        elif pull_or_push == "push":
            copy_from = "local"
            copy_to = "master"

        for collection_name in collection_names:
            if "fs.chunks" == collection_name: continue # Treat fs.chunks with fs.files

            temp_collection_name = collection_name.replace(".", "_") # key cannot contain '.'. i.e. 'fs.files' --> 'fs_files'
            missing_docs = []
            for oid in commit_doc[temp_collection_name]:
                query = {"_id": oid}
                doc = dbs[copy_from][collection_name].find_one(query)
                if doc:
                    dup_doc = dbs[copy_to][collection_name].find_one(query)
                    if dup_doc:
                        dbs[copy_to][collection_name].update(query, doc)
                    else:
                        dbs[copy_to][collection_name].insert(doc)
                        if "fs.files" in collection_name:
                            chunk_doc = dbs[copy_from]["fs.chunks"].find_one({"files_id": oid})
                            dbs[copy_to]["fs.chunks"].insert(chunk_doc)
                else:
                    missing_docs.append(oid)
            log_doc[temp_collection_name] = missing_docs
            if len(missing_docs) > 0: logging.warning(TOOLNAME + "There are missing files! Please look at log.")

    def __construct_log_doc(local_server_name, parent_id, oid, method):
        log_doc = __query()
        log_doc["local_server_name"] = local_server_name
        log_doc["parent"] = parent_id
        log_doc["id"] = oid
        log_doc["method"] = method
        return log_doc


    def __pull():
        # Get all local servers
        ref_docs = dbs_sync["local"]["refs"].find()

        if ref_docs.count() == 0:
            logging.error(TOOLNAME + "ERROR! No refs found! '--sync-opt fetch' first!")
            exit(1)

        for ref_doc in ref_docs:
            if ref_doc["local_server_name"] == my_doc["server"]["name"]: continue

            commit_cnt = 0

            # Get last sync log
            query = {"local_server_name": ref_doc["local_server_name"], "method": "pull"}
            log_doc = dbs_sync["local"]["logs"].find_one(query, sort=[("sys.cts", -1)])
            if log_doc: temp_id = log_doc["id"]
            else: temp_id = "bottausshiwasshi"

            while 1:
                # Get commit
                query = {"local_server_name": ref_doc["local_server_name"], "parent": temp_id}
                commit_doc = dbs_sync["local"]["commits"].find_one(query)

                if not commit_doc: break
                log_doc = __construct_log_doc(ref_doc["local_server_name"], temp_id, commit_doc["_id"], "pull")
                temp_id = commit_doc["_id"]

                __pull_of_push_from_commit("pull", commit_doc, log_doc)

                # Insert log
                dbs_sync["local"]["logs"].insert(log_doc)
                commit_cnt += 1

            logging.info(TOOLNAME + "Finished pull for local server name: " + ref_doc["local_server_name"] + " with " + str(commit_cnt) + " commits.")

    def __push():
        # Get last log from master
        query = {"local_server_name": my_doc["server"]["name"], "method": "push"}
        log_doc = dbs_sync["master"]["logs"].find_one(query, sort=[("sys.cts", -1)])
        if not log_doc: log_doc = dbs_sync["local"]["logs"].find_one(query, sort=[("sys.cts", 1)]) # Get first log from local

        temp_id = ""
        if log_doc: temp_id = log_doc["id"]
        else:
            commit_doc = dbs_sync["local"]["commits"].find_one({"local_server_name": my_doc["server"]["name"]}) # Find oldest commit of local server
            if not commit_doc:
                logging.error(TOOLNAME + "ERROR! No commit found on local server! Exit!")
                exit(1)
            temp_id = "bottausshiwasshi"
        commit_cnt = 0

        while 1:
            # Get commit
            query = {"local_server_name": my_doc["server"]["name"], "parent": temp_id}
            commit_doc = dbs_sync["local"]["commits"].find_one(query)

            if not commit_doc: break
            log_doc = __construct_log_doc(my_doc["server"]["name"], temp_id, commit_doc["_id"], "push")
            temp_id = commit_doc["_id"]

            __pull_of_push_from_commit("push", commit_doc, log_doc)

            # Insert new log to local and master
            dbs_sync["master"]["logs"].insert(log_doc)
            dbs_sync["local"]["logs"].insert(log_doc)

            # Insert commit to master
            dbs_sync["master"]["commits"].insert(commit_doc)

            # Update refs in master
            ref_doc = dbs_sync["master"]["refs"].find_one({"local_server_name": my_doc["server"]["name"]})
            if ref_doc:
                query = {"local_server_name": my_doc["server"]["name"]}
                newvalues = {"$set": { "sys.mts": current_datetime, "sys.rev": ref_doc["sys"]["rev"]+1, "id": commit_doc["_id"]}}
                dbs_sync["master"]["refs"].update_one(query, newvalues)
            else:
                ref_doc = __query()
                ref_doc["local_server_name"] = my_doc["server"]["name"]
                ref_doc["id"] = commit_doc["_id"]
                dbs_sync["master"]["refs"].insert(ref_doc)

            commit_cnt += 1

        logging.info(TOOLNAME + "Finished push! Uploaded " + str(commit_cnt) + " commits.")


    #================================================================================
    #
    #                               Main function
    #
    #================================================================================
    # Get username and hostname
    user = os.environ["USER"] # TODO, use from master db username?
    hostname = os.environ["HOSTNAME"] # and also password?
    mac = get_mac() # this may deleted
#    mac_add = "".join(c + ":" if i % 2 else c for i, c in enumerate(hex(mac)[2:].zfill(12)))[:-1]

    args = getArgs()

    # URLs
    if not args.host or not args.port or not args.mhost or not args.mport:
        logging.error(TOOLNAME+"ERROR! Local/Master host/port are not set!")
        exit(1)
    local_url = "mongodb://%s:%d" % (args.host, args.port)
    master_url = "mongodb://%s:%d" % (args.mhost, args.mport)
    logging.info(TOOLNAME + "LocalDB server is: " + local_url)
    logging.info(TOOLNAME + "Master server is: " + master_url)

    # Local or Master
    server_names = ["local", "master"]

    # DBs
    dbs = {"local": MongoClient(local_url)["localdb"], "master": MongoClient(master_url)["localdb"]}
    dbs_sync = {"local": MongoClient(local_url)["ldbtool"], "master": MongoClient(master_url)["ldbtool"]}

    # Set default time
    last_sync_datetime_default = dateutil.parser.parse("2000-7-20T1:00:00.000Z")

    # Get collection names from server
    collection_names = dbs["master"].collection_names()

    # Get current date time
    #current_datetime = datetime.datetime.now()
    current_datetime = datetime.datetime.utcnow()

    # Get my info
    my_doc = dbs_sync["local"]["my"].find_one()
    if not my_doc:
        my_doc = __query()
        my_doc["server"] = {}
        logging.info(TOOLNAME + "Hello! It seems that it is your first time to use sync_tool!")
        name = input(TOOLNAME + "Enter a server name: ")
        answer = ""
        while answer not in ("yes", "no"):
            answer = input(TOOLNAME + "The server name is " + name + ". Is it correct? ['yes' or 'no']: ")
            if answer == "yes":
                break
            elif answer == "no":
                name = input(TOOLNAME + "Enter a server name: ")
            else:
                print("Please enter 'yes' or 'no'.")

        my_doc["server"]["name"] = name
        dbs_sync["local"]["my"].insert(my_doc)


    # process sync option
    if args.sync_opt == "status": __status()
    elif args.sync_opt == "commit": __commit()
    elif args.sync_opt == "fetch": __fetch()
    elif args.sync_opt == "pull": __pull()
    elif args.sync_opt == "push": __push()
    elif args.sync_opt == "auto":
        __commit()
        __fetch()
        __pull()
        __push()
    else:
        logging.error(TOOLNAME + "--sync-opt not given or not matched! exit!")
        exit(1)


#            print(TOOLNAME + "Collection: " + collection_name)
#
#            documents = []
#            totals = []
#            for i in range(2):
#                documents.append(dbs[i][collection_name].find({query_key: {"$gt": last_time} }))
#                totals.append(documents[i].count())
#                sync_cnt[sync_action[i]][collection_name] = totals[i]
#                print("\t" + server_names[i] + " has " + str(totals[i]) + " documents ahead")
#
#
#            if not args.y: continue
#
#            # Start to synchronize
#            x = [0, 1]
#            y = [1, 0]
#            for i in range(2): # Copy from local first, then copy from Master
#                if totals[x[i]] == 0: continue
#
#                dup_count = 0
#                count = 0
#                # Copy docs to
#                for document in documents[x[i]]:
#                    doc_dup = dbs[y[i]][collection_name].find_one({"_id": document["_id"]})
#                    if doc_dup:
#                        if not doc_dup == document:
#                            if i == 1: # Copy from Master
##                                dbs[y[i]][collection_name].update({"_id": document["_id"]}, document) # Overwrite
#                                dup_count += 1
#                    else:
##                        dbs[y[i]][collection_name].insert(document)
#                        if "fs.files" in collection_name:
#                            chunks_doc = dbs[x[i]]["fs.chunks"].find_one({"files_id": document["_id"]}) # Find linked doc in fs.chunks
##                            if chunks_doc: dbs[y[i]]["fs.chunks"].insert(chunks_doc)
#                    count += 1
#                    printProgressBar(count, totals[x[i]], prefix = '        Progress copy from ' + server_names[x[i]], suffix = 'Complete')
#
#                sync_dup_cnt[sync_action[i]][collection_name] = dup_count
#                if dup_count != 0:
#                    print("\t\tFound " + str(dup_count) + " dup docs")
#
#
#
#    # Sync
#    datetimes = {}
#    sync_mts = {}
#    sync_cnt = {}
#    sync_dup_cnt = {}
#    sync_action = ["push", "pull"]
#    for i in range(2):
#        sync_mts[sync_action[i]] = {}
#        sync_cnt[sync_action[i]] = {}
#        sync_dup_cnt[sync_action[i]] = {}
#
#
#    # pull and push
#    if args.sync_opt is null:
#        print(TOOLNAME + "ERROR! Need synchronization option! e.g.) --sync-opt pull/push")
#        exit(1)
#
#    if args.sync_opt == "pull":
#        server_from = "master"
#        server_to = "local"
#    elif args.sync_doc == "push":
#        server_from = "local"
#        server_to = "master"
#    else:
#        print(TOOLNAME + "ERROR! Need synchronization option! e.g.) --sync-opt pull/push")
#        exit(1)
#
#
#    # Last
#    if not args.y:
#        print("")
#        print("Set'-y' option with your command to execute synchronization!")
#        return
#
#    # Finish
#    query = {"user": user, "hostname": hostname, "mac": mac, "datetime": datetime.datetime.now()}
#    index = 0
#    for i in range(2):
#        query[sync_action[i]] = {}
#    for collection_name in collection_names:
#        if "fs.chunks" == collection_name: continue # Treat fs.chunks with fs.files
#        query[collection_name] = datetimes[collection_name]
#        for i in range(2):
#            if collection_name in sync_mts[sync_action[i]]:
#                query[sync_action[i]][collection_name] = {"mts": sync_mts[sync_action[i]][collection_name],
#                        "cnt": sync_cnt[sync_action[i]][collection_name], "dup_cnt": sync_dup_cnt[sync_action[i]][collection_name]}
#    pprint.PrettyPrinter(indent=4).pprint(query)
##    for i in range(2):
##        dbs_sync[x[i]]["sync"].insert_one(query)

if __name__ == '__main__': sync()
