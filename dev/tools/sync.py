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
    TOOLNAME = "[SYNCTOOL]"
    current_datetime = datetime.datetime.utcnow()

    #================================================================================
    #
    #                               Private methods
    #
    #================================================================================
    def __query(revision=0, created_time_stamp=current_datetime):
        current_datetime = datetime.datetime.utcnow()
        return {"sys": {"rev": revision, "cts": created_time_stamp, "mts": current_datetime}}

    def __updateRef(database_type, ref_type, ref_doc, last_commit_id):
        ref_doc["sys"]["rev"] += 1
        ref_doc["sys"]["mts"] = datetime.datetime.utcnow()
        ref_doc["last_commit_id"] = last_commit_id
        update_result = localdbtool_dbs[database_type]["refs"].replace_one({"ref_type": ref_type}, ref_doc, upsert=True)

    def __construct_log_doc(local_server_name, parent_id, oid, method):
        log_doc = __query()
        log_doc["local_server_name"] = local_server_name
        log_doc["parent"] = parent_id
        log_doc["id"] = oid
        log_doc["method"] = method
        return log_doc


    #================================
    # status
    #================================
    def __status():
        commit_cnt = __pull(True)
        logging.info(TOOLNAME + "You have " + str(commit_cnt) + " commits to pull!")

        doc_cnt = __commit(True)
        logging.info(TOOLNAME + "You have " + str(doc_cnt) + " documents to commit!")

    #================================
    # commit
    #================================
    def __commit(is_status = False):
        loggingInfo(toolname=TOOLNAME, message="Run commit process")

        # Get last commit
        ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "local"})
        if not ref_doc:
            loggingInfo(toolname=TOOLNAME, message="No reference for local found. Create new one")
            ref_doc = __query()
            ref_doc["last_commit_id"] = "temporaly_last_commit_id"
            ref_doc["ref_type"] = "local"
        commit_doc = localdbtool_dbs["local"]["commits"].find_one({"_id": ref_doc["last_commit_id"]})

        # Get last commit datetime
        if commit_doc: last_sync_datetime = commit_doc["sys"]["cts"]
        else: last_sync_datetime = last_sync_datetime_default
        loggingInfo(toolname=TOOLNAME, message="Last sync time is: " + str(last_sync_datetime))

        # Construct query for new commit
        query = __query()
        query["master_user"] = localInfo["master_user"]
        if commit_doc: query["parent"] = commit_doc["_id"]
        else: query["parent"] = "no_parent_commit_id"
        query["commit_type"] = "commit"

        # Add _id each collection
        is_empty = True
        doc_cnt = 0
        for collection_name in collection_names:
            # Treat fs.chunks with fs.files
            if "fs.chunks" == collection_name: continue

            query_key = ""
            if not "fs" in collection_name:
                query_key = "sys.mts"
            elif "fs.files" in collection_name:
                query_key = "uploadDate"
            documents = localdb_dbs["local"][collection_name].find({query_key: {"$gt": last_sync_datetime} })
            ids = []
            for document in documents: ids.append(document["_id"])

            # key cannot contain '.'. i.e. 'fs.files' --> 'fs_files'
            temp_collection_name = collection_name.replace(".", "_")
            query[temp_collection_name] = ids
            if len(ids) is not 0:
                is_empty = False
                doc_cnt += len(ids)

        # For status
        if is_status:
            return doc_cnt

        if is_empty:
            loggingInfo(toolname=TOOLNAME, message="Nothing to commit!")
        else:
            #pprint.PrettyPrinter(indent=4).pprint(query) ## debug
            # Insert commit and update ref for local
            insert_one_result = localdbtool_dbs["local"]["commits"].insert_one(query)
            __updateRef("local", "local", ref_doc, insert_one_result.inserted_id)
            loggingInfo(toolname=TOOLNAME, message="Finished commit! The last commit is " + str(insert_one_result.inserted_id))


    #================================
    # fetch
    #================================
    def __fetch():
        # Get reference for master
        master_ref_doc = localdbtool_dbs["master"]["refs"].find_one({"ref_type": "master"})
        if not master_ref_doc:
            loggingWarning(toolname=TOOLNAME, message="No reference for master on master found! Push first!")
            return

        local_ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "master"})
        if not local_ref_doc:
            loggingInfo(toolname=TOOLNAME, message="No reference for master on local found! Create new one.")
            local_ref_doc = __query()
            local_ref_doc["ref_type"] = "master"

        # Download commits
        commit_docs = localdbtool_dbs["master"]["commits"].find()
        commit_cnt = 0
        for doc in commit_docs:
            update_result = localdbtool_dbs["local"]["commit"].replace_one({"_id": doc["_id"]}, doc, upsert=True)
            commit_cnt += update_result.modified_count
        loggingInfo(toolname=TOOLNAME, message="Downloaded %d commits from master server" % commit_doc)

        # Update ref for master
        __updateRef("local", "master", local_ref_doc, master_ref_doc["last_commit_id"])

    #================================
    # merge
    #================================
    def __merge():
        # Create a merge commit and insert
        ref_local_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "local"})
        ref_master_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "master"})
        master_ref_doc = localdbtool_dbs["master"]["refs"].find_one({"ref_type": "master"})
        if not ref_local_doc: return
        if master_ref_doc:
            if not ref_master_doc: return
            if ref_master_doc["last_commit_id"] != master_ref_doc["last_commit_id"]: return
        else:
            ref_master_doc = __query()
            ref_master_doc["ref_type"] = "master"
            ref_master_doc["last_commit_id"] = ""
            master_ref_doc = __query()
            master_ref_doc["ref_type"] = "master"
        commit_doc = __query()
        commit_doc["parent"] = ref_local_doc["last_commit_id"]
        commit_doc["parent_master"] = ref_master_doc["last_commit_id"]
        commit_doc["commit_type"] = "merge"
        commit_doc["master_user"] = localInfo["master_user"]
        insert_one_result = localdbtool_dbs["local"]["commits"].insert_one(commit_doc)
        commit_doc["_id"] = insert_one_result.inserted_id
        localdbtool_dbs["master"]["commits"].insert_one(commit_doc)
        # Update refs
        __updateRef("local", "local", ref_local_doc, commit_doc["_id"])
        __updateRef("local", "master", ref_master_doc, commit_doc["_id"])
        __updateRef("master", "master", master_ref_doc, commit_doc["_id"])

    #================================
    # pull or push from a commit
    #================================
    def __pull_or_push_from_commit(pull_or_push, commit_doc):
        if pull_or_push == "pull":
            copy_from = "master"
            copy_to = "local"
        elif pull_or_push == "push":
            copy_from = "local"
            copy_to = "master"

        for collection_name in collection_names:
            # Treat fs.chunks with fs.files
            if "fs.chunks" == collection_name: continue
            # key cannot contain '.'. i.e. 'fs.files' --> 'fs_files'
            temp_collection_name = collection_name.replace(".", "_")

            replaced_count = 0
            replaced_chunk_count = 0
            for oid in commit_doc[temp_collection_name]:
                doc = localdb_dbs[copy_from][collection_name].find_one({"_id": oid})
                if doc:
                    update_result = localdb_dbs[copy_to][collection_name].replace_one({"_id": oid}, doc, upsert=True)
                    replaced_count += update_result.modified_count
                    if "fs.files" in collection_name:
                        chunk_doc = localdb_dbs[copy_from]["fs.chunks"].find_one({"files_id": oid})
                        if chunk_doc:
                            update_chunk_result = localdb_dbs[copy_to]["fs.chunks"].replace_one({"files_id": oid}, chunk_doc, upsert=True)
                            replaced_chunk_count += update_chunk_result.modified_count
                        else:
                            loggingWarning(message="A fs.chunks doc not fount! files_id: %s" % oid)
                else:
                    loggingWarning(message="A %s doc not fount! files_id: %s" % (collection_name, oid) )

    #================================
    # pull or push
    #================================
    def __pull_or_push(pull_or_push):
        if pull_or_push == "pull":
            ref_type = "master"
        elif pull_or_push == "push":
            ref_type = "local"

        # Get reference for master
        ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": ref_type})
        if not ref_doc:
            if pull_or_push == "pull": loggingWarning(message="No reference for %s found! '--sync-opt fetch' first!" % ref_type)
            elif pull_or_push == "push": loggingWarning(message="No reference for %s found! '--sync-opt commit' first!" % ref_type)
            return

        # Get reference for pull
        ref_pull_or_push_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": pull_or_push})
        if not ref_pull_or_push_doc:
            loggingInfo(toolname=TOOLNAME, message="No reference for %s on local found! Create new one." % pull_or_push)
            ref_pull_or_push_doc = __query()
            ref_pull_or_push_doc["ref_type"] = pull_or_push
            ref_pull_or_push_doc["last_commit_id"] = "temporaly_last_commit_id"

        if ref_doc["last_commit_id"] == ref_pull_or_push_doc["last_commit_id"]:
            loggingInfo(message="Already updated %s! Not thing to do!" % pull_or_push)
            return

        # Get last commit
        last_commit_doc = localdbtool_dbs["local"]["commits"].find_one({"_id": ref_doc["last_commit_id"]})
        if not last_commit_doc:
            loggingWarning(toolname=TOOLNAME, message="No last commit doc found!")
            return
        commit_doc = last_commit_doc
        commit_cnt = 0
        while True:
            if commit_doc["commit_type"] == "merge": continue

            __pull_or_push_from_commit(pull_or_push, commit_doc)
            commit_cnt += 1
            # Insert the commit to master
            if pull_or_push == "push": update_result = localdbtool_dbs["master"]["commits"].replace_one({"_id": commit_doc["_id"]}, commit_doc, upsert=True)

            # Get parent commit
            commit_doc = localdbtool_dbs["local"]["commits"].find_one({"_id": commit_doc["parent"]})
            if not commit_doc: break
            if commit_doc["last_commit_id"] == ref_pull_or_push_doc["last_commit_id"]: break

        # Update reference for pull or push
        __updateRef("local", pull_or_push, ref_pull_or_push_doc, ref_doc["last_commit_id"])

        # Merge
        if pull_or_push == "push": __merge()
        loggingInfo(toolname=TOOLNAME, message="Finished %s with %d commits." % (pull_or_push, commit_cnt) )

    def __connectMongoDB(server_name, host, port, username, keypath):
        # Development environment
        if args.development_flg:
            url = "mongodb://%s:%d" % (host, port)
            logging.info("%s server url is: %s" % (server_name, url) )
            return MongoClient(url)["localdb"], MongoClient(url)["localdbtools"]

        # Production environment
        if username and keypath:
            if os.path.exists(keypath):
                key_file = open(keypath, "r")
                key = key_file.read()
            else:
                loggingErrorAndExit(message="%s API Key not exist!" % server_name, exit_code=1)
        else:
            loggingErrorAndExit(message="%s user name or API Key not given!" % server_name, exit_code=1)

        url = "mongodb://%s:%s@%s:%d" % (username, key, host, port)
        logging.info("%s server url is: %s" % (server_name, url) )
        return MongoClient(url)["localdb"], MongoClient(url)["localdbtools"]

    def __getLocalInfo():
        # Get machine host name, user name and mac address
        myInfo = {}
        myInfo["local_machine_hostname"] = os.environ["HOSTNAME"]
        myInfo["local_machine_user"] = os.environ["USER"]
        mac = get_mac()
        myInfo["local_machine_mac"] = "".join(c + ":" if i % 2 else c for i, c in enumerate(hex(mac)[2:].zfill(12)))[:-1]

        # Attach user name on master server
        myInfo["master_user"] = args.musername

        # Get network info
        ipinfo_url = "https://ipinfo.io"
        ipinfo_request = requests.get(ipinfo_url)
        ipinfo_json = json.loads(ipinfo_request.text)
        myInfo["local_network_ip"] = ipinfo_json["ip"]
        myInfo["local_network_loc"] = ipinfo_json["loc"]
        myInfo["local_network_hostname"] = ipinfo_json["hostname"]
        return myInfo

    def __log(level, message):
        query = {
                "datetime": datetime.datetime.utcnow(),
                "level": level,
                "message": message
            }
        localdbtool_dbs["local"]["log"].insert_one(query)
        localdbtool_dbs["master"]["log"].insert_one(query)


    #================================================================================
    #
    #                               Main function
    #
    #================================================================================

    # Get arguments
    args = getArgs()

    # Setup logging
    setupLogging(args.logfile)

    # Connect mongoDB
    server_names = ["local", "master"]
    temp_local_db_localdb, temp_local_db_localdbtools = __connectMongoDB("local", args.host, args.port, args.username, args.keypath)
    temp_master_db_localdb, temp_master_db_localdbtools = __connectMongoDB("master", args.mhost, args.mport, args.musername, args.mkeypath)

    # DBs
    localdb_dbs = {server_names[0]: temp_local_db_localdb, server_names[1]: temp_master_db_localdb}
    localdbtool_dbs = {server_names[0]: temp_local_db_localdbtools, server_names[1]: temp_master_db_localdbtools}

    # Set default time
    last_sync_datetime_default = dateutil.parser.parse("2000-7-20T1:00:00.000Z")

    # Get collection names from server
    collection_names = localdb_dbs["master"].collection_names()

    # Get current date time
    #current_datetime = datetime.datetime.now()
    current_datetime = datetime.datetime.utcnow()

    # Get localDB server config
    localInfo = __getLocalInfo()


    # process sync option
    if args.sync_opt == "status": __status()
    elif args.sync_opt == "commit": __commit()
    elif args.sync_opt == "fetch": __fetch()
    elif args.sync_opt == "pull": __pull_or_push("pull")
    elif args.sync_opt == "push": __pull_or_push("push")
    elif args.sync_opt == "auto":
        __commit()
        __fetch()
        __pull_or_push("pull")
        __pull_or_push("push")
    else:
        logging.error(TOOLNAME + "--sync-opt not given or not matched! exit!")
        exit(1)


if __name__ == '__main__': sync()
