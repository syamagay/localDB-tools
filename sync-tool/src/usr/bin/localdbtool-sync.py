#!/usr/bin/env python3
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
#################################

# Common
import os, sys
# Pymongo and Bson
from bson.objectid import ObjectId
from pymongo import MongoClient
import pymongo

# getArgs
import yaml, argparse

# Summary
from prettytable import PrettyTable

# Sync
from uuid import getnode as get_mac # Get MAC adress
import dateutil.parser
import datetime
import pprint

# Sticky
#sys.path.append(os.getcwd())


TOOLNAME = "[LocalDB Tool] "


menus=["summary", "verify", "sync"]

def readConfig(conf_path):
    f = open(conf_path, "r")
    conf = yaml.load(f)
    return conf

def getArgs():
    menus_str = ""
    for menu in menus:  menus_str += menu + ", "

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-y", help="Yes to confirmation", action="store_true")
    parser.add_argument("--config", "-f", help="Config file path", type=str)
    parser.add_argument("--host", help="LocalDB Server Host", type=str, default="localhost")
    parser.add_argument("--port", help="LocalDB Server Port", type=str, default="27017")
    parser.add_argument("--username", "-u", help="LocalDB Server User Name", type=str)
    parser.add_argument("--password", "-p", help="LocalDB Server User Password", type=str)
    parser.add_argument("--mhost", help="Master Server Host", type=str)
    parser.add_argument("--mport", help="Master Server Port", type=str)
    parser.add_argument("--musername", help="Master Server User Name", type=str)
    parser.add_argument("--mpassword", help="Master Server User Password", type=str)
    parser.add_argument("--dbVersion", "-d", help="DB Version", type=float, default="1.")
    parser.add_argument("--sync-opt", help="Synchronization option", type=str)
    args = parser.parse_args()


    if args.config is not None:
        conf = readConfig(args.config)    # Read from config file
        if "local" in conf:
            if "host" in conf["local"]:         args.host = conf["local"]["host"]
            if "port" in conf["local"]:         args.port = conf["local"]["port"]
            if "username" in conf["local"]:     args.username = conf["local"]["username"]
            if "password" in conf["local"]:     args.password = conf["local"]["password"]
        if "master" in conf:
            if "host" in conf["master"]:        args.mhost = conf["master"]["host"]
            if "port" in conf["master"]:        args.mport = conf["master"]["port"]
            if "username" in conf["master"]:    args.musername = conf["master"]["username"]
            if "password" in conf["master"]:    args.mpassword = conf["master"]["password"]
        if "dbVersion" in conf:                 args.dbVersion = conf["dbVersion"]

    return args







TOOLNAME = "[LocalDB Tool] "


def printProgressBar(iteration, total, prefix = '', suffix = '', decimals = 1, fill = '*'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        fill        - Optional  : bar fill character (Str)
    """
    rows, columns = os.popen('stty size', 'r').read().split() # Get terminal width
    length = int(columns) - len(prefix) - len(suffix) - 11
    if total == 0:
        percent = ("{0:." + str(decimals) + "f}").format(100)
        filledLength = int(length * 1)
    else:
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = "\r")
    if iteration == total: 
        print()


def queryYesNo(question, default="no"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower() # python 3 
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def sync():

    def __query():
        return {"sys": {"rev": 0, "cts": current_datetime, "mts": current_datetime}}

    def __commit():
        query = {"local_server_name": my_doc["server"]["name"]}
        commit_doc = dbs_sync["local"]["commits"].find_one(query, sort=[("sys.cts", -1)])

        last_sync_datetime = last_sync_datetime_default
        if commit_doc: last_sync_datetime = commit_doc["sys"]["cts"]
        print(TOOLNAME + "Last sync time is: " + str(last_sync_datetime))


        query = __query()
        query["local_server_name"] = my_doc["server"]["name"]
        if commit_doc: query["parent"] = commit_doc["_id"]
        else: query["parent"] = "bottausshiwasshi"
        query["description"] = "commit"

        is_empty = True
        for collection_name in collection_names:
            if "fs.chunks" == collection_name: continue # Treat fs.chunks with fs.files

            query_key = ""
            if not "fs" in collection_name:
                query_key = "sys.mts"
            elif "fs.files" in collection_name:
                query_key = "uploadDate"
            documents = dbs["local"][collection_name].find({query_key: {"$gt": last_sync_datetime} })
            ids = []
            for document in documents:
                ids.append(document["_id"])

            temp_collection_name = collection_name.replace(".", "_") # key cannot contain '.'. i.e. 'fs.files' --> 'fs_files'
            query[temp_collection_name] = ids
            if len(ids) is not 0: is_empty = False

        if is_empty:
            print(TOOLNAME + "Nothing to commit!")
        else:
            oid = dbs_sync["local"]["commits"].insert(query)
            print(TOOLNAME + "Finished commit! The oid is " + str(oid))

    def __fetch():
        commit_docs = dbs_sync["master"]["commits"].find()
        commit_cnt = 0
        for doc in commit_docs:
            doc_dup = dbs_sync["local"]["commits"].find_one({"_id": doc["_id"]})
            if not doc_dup:
                dbs_sync["local"]["commits"].insert(doc)
                commit_cnt += 1
        print(TOOLNAME + "Downloaded " + str(commit_cnt) + " commits from master server")

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
        print(TOOLNAME + "Downloaded " + str(ref_cnt) + " refs from master server")

    def __status():
        print("to be continued...")

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
            if len(missing_docs) > 0: print(TOOLNAME + "There are missing files! Please look at log.")

    def __construct_log_doc(local_server_name, parent_id, oid, method):
        log_doc = __query()
        log_doc["local_server_name"] = local_server_name
        log_doc["parent"] = parent_id
        log_doc["id"] = oid
        log_doc["method"] = method
        return log_doc


    def __pull():
        ref_docs = dbs_sync["local"]["refs"].find()

        if ref_docs.count() == 0:
            print(TOOLNAME + "ERROR! No refs found! '--sync-opt fetch' first!")
            exit(1)

        for ref_doc in ref_docs:
            if ref_doc["local_server_name"] == my_doc["server"]["name"]: continue

            commit_cnt = 0

            query = {"local_server_name": ref_doc["local_server_name"], "method": "pull"}
            log_doc = dbs_sync["local"]["logs"].find_one(query, sort=[("sys.cts", -1)])
            if log_doc: temp_id = log_doc["id"]
            else: temp_id = "bottausshiwasshi"

            while 1:
                query = {"local_server_name": ref_doc["local_server_name"], "parent": temp_id}
                commit_doc = dbs_sync["local"]["commits"].find_one(query)

                if not commit_doc: break
                log_doc = __construct_log_doc(ref_doc["local_server_name"], temp_id, commit_doc["_id"], "pull")
                temp_id = commit_doc["_id"]

                __pull_of_push_from_commit("pull", commit_doc, log_doc)

                dbs_sync["local"]["logs"].insert(log_doc)
                commit_cnt += 1

            print(TOOLNAME + "Finished pull for local server name: " + ref_doc["local_server_name"] + " with " + str(commit_cnt) + " commits.")

    def __push():
        query = {"local_server_name": my_doc["server"]["name"], "method": "push"}
        log_doc = dbs_sync["master"]["logs"].find_one(query, sort=[("sys.cts", -1)])
        if not log_doc: log_doc = dbs_sync["local"]["logs"].find_one(query, sort=[("sys.cts", 1)]) # Get first log from local

        temp_id = ""
        if log_doc: temp_id = log_doc["id"]
        else:
            commit_doc = dbs_sync["local"]["commits"].find_one({"local_server_name": my_doc["server"]["name"]}) # Find oldest commit of local server
            if not commit_doc:
                print(TOOLNAME + "ERROR! No commit found on local server! Exit!")
                exit(1)
            temp_id = "bottausshiwasshi"
        commit_cnt = 0

        while 1:
            query = {"local_server_name": my_doc["server"]["name"], "parent": temp_id}
            commit_doc = dbs_sync["local"]["commits"].find_one(query)

            if not commit_doc: break
            log_doc = __construct_log_doc(my_doc["server"]["name"], temp_id, commit_doc["_id"], "push")
            temp_id = commit_doc["_id"]

            __pull_of_push_from_commit("push", commit_doc, log_doc)

            dbs_sync["master"]["logs"].insert(log_doc)
            dbs_sync["local"]["logs"].insert(log_doc)

            dbs_sync["master"]["commits"].insert(commit_doc)

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

        print(TOOLNAME + "Finished push! Uploaded " + str(commit_cnt) + " commits.")


    user = os.environ["USER"] # TODO, use from master db username?
    hostname = os.environ["HOSTNAME"] # and also password?
    mac = get_mac() # this may deleted

    args = getArgs()

    if not args.host or not args.port or not args.mhost or not args.mport:
        print(TOOLNAME+"ERROR! Local/Master host/port are not set!")
        exit(1)
    local_url = "mongodb://" + args.host + ":" + str(args.port)
    master_url = "mongodb://" + args.mhost + ":" + str(args.mport)
    print(TOOLNAME + "LocalDB server is: " + local_url)
    print(TOOLNAME + "Master server is: " + master_url)

    server_names = ["local", "master"]

    dbs = {"local": MongoClient(local_url)["yarrdb"], "master": MongoClient(master_url)["yarrdb"]}
    dbs_sync = {"local": MongoClient(local_url)["ldbtool"], "master": MongoClient(master_url)["ldbtool"]}

    last_sync_datetime_default = dateutil.parser.parse("2000-7-20T1:00:00.000Z")

    collection_names = dbs["master"].collection_names()

    current_datetime = datetime.datetime.utcnow()

    my_doc = dbs_sync["local"]["my"].find_one()
    if not my_doc:
        my_doc = __query()
        my_doc["server"] = {}
        print(TOOLNAME + "Hello! It seems that it is your first time to use sync_tool!")
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


    if args.sync_opt == "commit": __commit()
    elif args.sync_opt == "fetch": __fetch()
    elif args.sync_opt == "pull": __pull()
    elif args.sync_opt == "push": __push()
    else:
        print(TOOLNAME + "--sync-opt not given or not matched! exit!")
        exit(1)



if __name__ == '__main__': sync()
