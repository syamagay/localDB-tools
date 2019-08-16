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

    def __insert_log(commit_id, message):
        log_doc = __query()
        log_doc["commit_id"] = commit_id
        log_doc["message"] = message
        insert_one_result = localdbtool_dbs["local"]["logs"].insert_one(log_doc)
        return insert_one_result.inserted_id


    #================================
    # status
    #================================
    def __status():
        logger.setFuncName("status")
        #commit_count = __pull_or_push(True)
        #logger.info("You have %d commits to pull!" % commit_count)

        doc_count = __commit(True)
        logger.info("You have %d documents to commit!" % doc_count)

    #================================
    # commit
    #================================
    def __commit(is_status = False):
        logger.setFuncName("commit")

        # Get heac ref and last commit
        local_head_ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "head"})
        if not local_head_ref_doc:
            logger.warning("No reference for local found. Create new one")
            local_head_ref_doc = __query()
            local_head_ref_doc["last_commit_id"] = ""
            local_head_ref_doc["ref_type"] = "head"
        last_commit_doc = localdbtool_dbs["local"]["commits"].find_one({"_id": local_head_ref_doc["last_commit_id"]})

        # Get last commit datetime
        if last_commit_doc: last_sync_datetime = last_commit_doc["sys"]["cts"]
        else: last_sync_datetime = last_sync_datetime_default
        logger.info("Last sync time is: " + str(last_sync_datetime))

        # Construct a new commit doc
        commit_doc = __query()
        commit_doc["local_server_config_id"] = local_server_config_id
        if last_commit_doc: commit_doc["parent"] = last_commit_doc["_id"]
        else: commit_doc["parent"] = ""
        commit_doc["commit_type"] = "commit"

        # Add _id of each collection
        is_empty = True
        doc_count = 0
        commit_doc["ids"] = []
        for collection_name in collection_names:
            # Treat fs.chunks with fs.files
            if "fs.chunks" == collection_name: continue

            if not "fs" in collection_name:
                query_key = "sys.mts"
            elif "fs.files" in collection_name:
                query_key = "uploadDate"
            documents = localdb_dbs["local"][collection_name].find({query_key: {"$gt": last_sync_datetime} })
            ids = []
            for document in documents: ids.append(document["_id"])

            # key cannot contain '.'. i.e. 'fs.files' --> 'fs_files'
            temp_collection_name = collection_name.replace(".", "_")
            commit_doc["ids"].append({temp_collection_name: ids})
            if len(ids) is not 0:
                is_empty = False
                doc_count += len(ids)

        # For status
        if is_status:
            return doc_count

        if is_empty:
            logger.info("Nothing to commit!")
        else:
            #pprint.PrettyPrinter(indent=4).pprint(commit_doc) ## debug
            # Insert commit and update ref for local
            insert_one_result = localdbtool_dbs["local"]["commits"].insert_one(commit_doc)
            __updateRef("local", "head", local_head_ref_doc, insert_one_result.inserted_id)
            #__insert_log(insert_one_result.inserted_id, "commit")
            logger.info("Finished commit! Total %d documents. The last commit id is %s." % (doc_count, str(insert_one_result.inserted_id)) )

    #================================
    # fetch
    #================================
    def __fetch():
        logger.setFuncName("fetch")

        # Download server documents
        server_docs = localdbtool_dbs["master"]["servers"].find()
        for server_doc in server_docs:
            localdbtool_dbs["local"]["servers"].replace_one({"_id": server_doc["_id"]}, server_doc, upsert=True)

        # Get head reference on master
        master_head_ref_doc = localdbtool_dbs["master"]["refs"].find_one({"ref_type": "head"})
        if not master_head_ref_doc:
            logger.warning("No head reference on master found! Push first!")
            return

        # Get remote reference on local
        local_remote_ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "remote"})
        if not local_remote_ref_doc:
            logger.warning("No remote reference on local found! Create new one.")
            local_remote_ref_doc = __query()
            local_remote_ref_doc["ref_type"] = "remote"

        # Download commits
        commit_docs = localdbtool_dbs["master"]["commits"].find()
        commit_count = 0
        for doc in commit_docs:
            update_result = localdbtool_dbs["local"]["commits"].replace_one({"_id": doc["_id"]}, doc, upsert=True)
            if update_result.matched_count == 0: commit_count += 1
        logger.info("Downloaded %d commits from master server" % commit_count)

        # Update remote ref on local
        __updateRef("local", "remote", local_remote_ref_doc, master_head_ref_doc["last_commit_id"])

    #================================
    # merge
    #================================
    def __merge():
        # Check refs
        local_head_ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "head"})
        local_remote_ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "remote"})
        master_head_ref_doc = localdbtool_dbs["master"]["refs"].find_one({"ref_type": "head"})
        if not local_head_ref_doc: return
        if master_head_ref_doc:
            # Should fetch first
            if not local_remote_ref_doc: return
            if local_remote_ref_doc["last_commit_id"] != master_head_ref_doc["last_commit_id"]: return
        else:
            master_head_ref_doc = __query()
            master_head_ref_doc["ref_type"] = "head"
            if not local_remote_ref_doc:
                local_remote_ref_doc = __query()
                local_remote_ref_doc["ref_type"] = "remote"
                local_remote_ref_doc["last_commit_id"] = ""
        # Create a merge commit and insert
        commit_doc = __query()
        commit_doc["local_server_config_id"] = local_server_config_id
        commit_doc["parent"] = local_head_ref_doc["last_commit_id"]
        commit_doc["parent_merge"] = local_remote_ref_doc["last_commit_id"]
        commit_doc["commit_type"] = "merge"
        insert_one_result = localdbtool_dbs["local"]["commits"].insert_one(commit_doc)
        commit_doc["_id"] = insert_one_result.inserted_id
        # Update refs
        __updateRef("local", "head", local_head_ref_doc, commit_doc["_id"])
        return commit_doc

    #================================
    # pull or push from a commit
    #================================
    def __pull_or_push_from_commit(pull_or_push, commit_doc):
        id_count = 0
        if pull_or_push == "pull":
            copy_from = "master"
            copy_to = "local"
        elif pull_or_push == "push":
            copy_from = "local"
            copy_to = "master"

        # Check in logs
        log_doc = localdbtool_dbs["local"]["logs"].find_one({"commit_id": commit_doc["_id"]})
        if log_doc:
            logger.warning("Commit already exists in 'logs'! Cannot %s! _id: '%s'" % (pull_or_push, commit_doc["_id"]) )
            return -1

        for ids_collection in commit_doc["ids"]:
            # Get collection names from key, no fs.chunks
            collection_name = list(ids_collection)[0]
            temp_collection_name = collection_name
            if "fs_files" == collection_name:
                # key cannot contain '.'. i.e. 'fs.files' --> 'fs_files'
                collection_name = collection_name.replace("_", ".")

            id_count += len(ids_collection[temp_collection_name])
            modified_count = 0
            modified_chunk_count = 0
            for oid in ids_collection[temp_collection_name]:
                doc = localdb_dbs[copy_from][collection_name].find_one({"_id": oid})
                if doc:
                    update_result = localdb_dbs[copy_to][collection_name].replace_one({"_id": oid}, doc, upsert=True)
                    modified_count += update_result.modified_count
                    # Treat fs.chunks with fs.files
                    if "fs.files" in collection_name:
                        chunk_doc = localdb_dbs[copy_from]["fs.chunks"].find_one({"files_id": oid})
                        if chunk_doc:
                            update_chunk_result = localdb_dbs[copy_to]["fs.chunks"].replace_one({"files_id": oid}, chunk_doc, upsert=True)
                            modified_chunk_count += update_chunk_result.modified_count
                        else:
                            logger.warning("A fs.chunks doc not found! files_id: '%s'" % oid)
                else:
                    logger.warning("A doc in '%s' collection not found! _id: '%s'" % (collection_name, oid) )
            if modified_count != 0: logger.warning("%d documents in' %s' collection were overwrotten" % (collection_name, modified_count) )
            if modified_chunk_count != 0: logger.warning("%d chunk documents in' %s' collection were overwrotten" % (collection_name, modified_chunk_count) )

        # Upload commit doc when push
        if pull_or_push == "push": update_result = localdbtool_dbs[copy_to]["commits"].replace_one({"_id": commit_doc["_id"]}, commit_doc, upsert=True)
        if update_result.modified_count != 0: logger.warning("commit doc _id '%s' was already exist!" % (str(commit_doc["_id"])) )
        #if pull_or_push == "pull": __insert_log(commit_doc["_id"], "pull")
        __insert_log(commit_doc["_id"], pull_or_push)

        return id_count

    #================================
    # Get commit tree
    # Return True if it gets end of commit tree
    # count = [0, 0]: first value for commit count, second is id count
    #================================
    def __get_commit_tree(count, pull_or_push, stopper_commit_id, commit_doc):
        logger.setFuncName("get_commit_tree")
        while True:
            #==========================
            # parent --- child
            #==========================
            if commit_doc["commit_type"] == "commit":
                if pull_or_push == "pull" or pull_or_push == "push":
                    id_count = __pull_or_push_from_commit(pull_or_push, commit_doc)
                    if id_count == -1: return False
                    else: count[1] += id_count
                count[0] += 1
            #==========================
            # parent ---------- child
            #                |
            # parent_merge ---
            #==========================
            elif commit_doc["commit_type"] == "merge":
                # Insert merge commit to master
                if pull_or_push == "push":
                    update_result = localdbtool_dbs["master"]["commits"].replace_one({"_id": commit_doc["_id"]}, commit_doc, upsert=True)
                    if update_result.modified_count != 0: logger.warning("commit document alread exist! _id: '%s'" % commit_doc["_id"])
                    else: __insert_log(commit_doc["_id"], "push")
                parent_merge_commit_doc = localdbtool_dbs["local"]["commits"].find_one({"_id": commit_doc["parent_merge"]})
                if not parent_merge_commit_doc: logger.error("Parent merge commit document not found! _id: '%s'" % commit_doc["parent_merge"])
                #if not __get_commit_tree(count, pull_or_push, stopper_commit_id, parent_merge_commit_doc): return False
                __get_commit_tree(count, pull_or_push, stopper_commit_id, parent_merge_commit_doc)

            # Get parent commit
            commit_doc = localdbtool_dbs["local"]["commits"].find_one({"_id": commit_doc["parent"]})
            if not commit_doc: break
            if commit_doc["_id"] == stopper_commit_id: return False

        return True

    #================================
    # pull or push
    #================================
    def __pull_or_push(pull_or_push):
        logger.setFuncName(pull_or_push)

        # Get reference for pull or push
        pull_or_push_ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": pull_or_push})
        if not pull_or_push_ref_doc:
            logger.warning("No reference for '%s' on local found! Create new one..." % pull_or_push)
            pull_or_push_ref_doc = __query()
            pull_or_push_ref_doc["ref_type"] = pull_or_push
            pull_or_push_ref_doc["last_commit_id"] = ""

        # Get remote reference on local
        local_remote_ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "remote"})
        if not local_remote_ref_doc:
            logger.warning("No remote reference on local found! Create new one...")
            local_remote_ref_doc = __query()
            local_remote_ref_doc["ref_type"] = "remote"
            local_remote_ref_doc["last_commit_id"] = ""

        # Check before push
        if pull_or_push == "push":
            # Get head reference on local
            local_head_ref_doc = localdbtool_dbs["local"]["refs"].find_one({"ref_type": "head"})
            if not local_head_ref_doc: logger.error("No head reference on local found! '--sync-opt commit' first!")
            last_commit_id = local_head_ref_doc["last_commit_id"]

            if local_head_ref_doc["last_commit_id"] == pull_or_push_ref_doc["last_commit_id"]:
                logger.info("Already updated for '%s'! Not thing to do!" % pull_or_push)
                return

            # Get last commit on local
            last_commit_doc = localdbtool_dbs["local"]["commits"].find_one({"_id": local_head_ref_doc["last_commit_id"]})
            if not last_commit_doc: logger.error("Last commit not found! _id: '%s'" % local_head_ref_doc["last_commit_id"])

            # Seach commit of master head reference from local commit tree
            get_commit_tree_result = __get_commit_tree([0, 0], "search", local_remote_ref_doc["last_commit_id"], last_commit_doc)
            # Check merge
            if (local_remote_ref_doc["last_commit_id"] != ""
                    and local_remote_ref_doc["last_commit_id"] != local_head_ref_doc["last_commit_id"]
                    and get_commit_tree_result):
                logger.warning("last commit of remote not found on local commit tree! merge automatically...")
                last_commit_doc = __merge()
                last_commit_id = last_commit_doc["_id"]

        # Check before pull
        if pull_or_push == "pull":
            last_commit_id = local_remote_ref_doc["last_commit_id"]
            if local_remote_ref_doc["last_commit_id"] == pull_or_push_ref_doc["last_commit_id"]:
                logger.info("Already updated for '%s'! Not thing to do!" % pull_or_push)
                return

            # Get last commit
            last_commit_doc = localdbtool_dbs["local"]["commits"].find_one({"_id": local_remote_ref_doc["last_commit_id"]})
            if not last_commit_doc: logger.error("Last commit doc not found! _id: '%s'" % local_remote_ref_doc["last_commit_id"])

        count = [0, 0]
        __get_commit_tree(count, pull_or_push, pull_or_push_ref_doc["last_commit_id"], last_commit_doc)

        # Update pull or push reference
        __updateRef("local", pull_or_push, pull_or_push_ref_doc, last_commit_id)
        # Update head reference of master
        if pull_or_push == "push":
            master_head_ref_doc = localdbtool_dbs["master"]["refs"].find_one({"ref_type": "head"})
            if not master_head_ref_doc:
                logger.warning("No head reference on master found! Create new one...")
                master_head_ref_doc = __query()
                master_head_ref_doc["ref_type"] = "head"
            __updateRef("master", "head", master_head_ref_doc, last_commit_id)

        logger.info("Finished %s with %d commits and %d documents" % (pull_or_push, count[0], count[1]) )


    def __connectMongoDB(server_name, host, port, username, keypath):
        # Development environment
        if args.is_development:
            url = "mongodb://%s:%d" % (host, port)
            logger.info("%s server url is: %s" % (server_name, url) )
            return MongoClient(url)["localdb"], MongoClient(url)["localdbtools"]

        # Production environment
        if username and keypath:
            if os.path.exists(keypath):
                key_file = open(keypath, "r")
                key = key_file.read()
            else:
                logger.error("%s API Key not exist!" % server_name, exit_code=1)
        else:
            logger.error("%s user name or API Key not given!" % server_name, exit_code=1)

        url = "mongodb://%s:%s@%s:%d" % (username, key, host, port)
        logger.info("%s server url is: %s" % (server_name, url) )
        return MongoClient(url)["localdb"], MongoClient(url)["localdbtools"]

    def __getLocalInfo():
        # Find sync config
        sync_config_doc = localdbtool_dbs["local"]["configs"].find_one({"config_type": "sync"})

        if sync_config_doc:
            local_server_config_id = sync_config_doc["_id"]
        else:
            # If no sync config, create new and insert
            logger.warning("Local server config not found! Create newn one...")
            sync_config_doc = __query()
            sync_config_doc["config_type"] = "sync"

            # Get machine host name, user name and mac address
            sync_config_doc["machine"] = {}
            sync_config_doc["machine"]["hostname"] = os.environ["HOSTNAME"]
            sync_config_doc["machine"]["user"] = os.environ["USER"]
            mac = get_mac()
            sync_config_doc["machine"]["mac"] = "".join(c + ":" if i % 2 else c for i, c in enumerate(hex(mac)[2:].zfill(12)))[:-1]

            # Get network info
            ipinfo_url = "https://ipinfo.io"
            ipinfo_request = requests.get(ipinfo_url)
            if ipinfo_request:
                ipinfo_json = json.loads(ipinfo_request.text)
                sync_config_doc["network"] = {}
                sync_config_doc["network"]["ip"] = ipinfo_json["ip"]
                sync_config_doc["network"]["hostname"] = ipinfo_json["hostname"]
                sync_config_doc["network"]["city"] = ipinfo_json["city"]
                sync_config_doc["network"]["region"] = ipinfo_json["region"]
                sync_config_doc["network"]["country"] = ipinfo_json["country"]
                sync_config_doc["network"]["loc"] = ipinfo_json["loc"]
            else:
                if not args.f:
                    logger.error("Cannot connect to network! If you want to ignore this, please use '-f' option!")

            #json_file = open("sync_config.json", "w+", encoding="utf-8")
            #json.dump(sync_config_doc, json_file, ensure_ascii=False, indent=4)
            # Insert
            insert_one_result = localdbtool_dbs["local"]["configs"].insert_one(sync_config_doc)
            local_server_config_id = insert_one_result.inserted_id
            sync_config_doc["_id"] = local_server_config_id
            # Insert to local server collection
            localdbtool_dbs["local"]["servers"].insert_one(sync_config_doc)

        # Push local server config to master if not exist
        master_server_doc = localdbtool_dbs["master"]["servers"].find_one({"_id": local_server_config_id})
        if not master_server_doc:
            localdbtool_dbs["master"]["servers"].replace_one({"_id": local_server_config_id}, sync_config_doc, upsert=True)

        logger.debug("Local server config id: %s" % local_server_config_id)

        return local_server_config_id


    #================================================================================
    #
    #                               Main function
    #
    #================================================================================

    # Get arguments
    args = getArgs()

    # Setup logging
    logger = Logger(TOOLNAME)
    if args.logfile: logger.setupLogging(logfile=args.logfile)
    else: logger.setupLogging()

    # Connect mongoDB
    server_names = ["local", "master"]
    temp_local_db_localdb, temp_local_db_localdbtools = __connectMongoDB("local", args.host, args.port, args.username, args.keypath)
    temp_master_db_localdb, temp_master_db_localdbtools = __connectMongoDB("master", args.mhost, args.mport, args.musername, args.mkeypath)

    # Debug
    from bson import SON
    c = MongoClient("mongodb://localhost:27011")
    result = c.admin.command(SON([
        ("setParameter", 1),
        ("logComponentVerbosity", {
            "storage": {
                "verbosity": 5,
                "journal": {
                    "verbosity": 1
                }
            }
        })]))

    # DBs
    localdb_dbs = {server_names[0]: temp_local_db_localdb, server_names[1]: temp_master_db_localdb}
    localdbtool_dbs = {server_names[0]: temp_local_db_localdbtools, server_names[1]: temp_master_db_localdbtools}

    # Set default time
    last_sync_datetime_default = dateutil.parser.parse("2000-7-20T1:00:00.000Z")

    # Get collection names from server
    collection_names = localdb_dbs["master"].list_collection_names()

    # Get current date time
    #current_datetime = datetime.datetime.now()
    current_datetime = datetime.datetime.utcnow()

    # Get localDB server config
    local_server_config_id = __getLocalInfo()

    # process sync option
    if args.sync_opt == "status": __status()
    elif args.sync_opt == "commit": __commit()
    elif args.sync_opt == "fetch": __fetch()
    elif args.sync_opt == "pull": __pull_or_push("pull")
    elif args.sync_opt == "push": __pull_or_push("push")
    elif args.sync_opt == "auto":
        __fetch()
        __pull_or_push("pull")
        __commit()
        __pull_or_push("push")
    else:
        logger.error("--sync-opt not given or not matched! exit!", exit_code=1)

    logger.info("All done.")


if __name__ == '__main__': sync()
