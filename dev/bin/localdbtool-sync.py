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
sys.path.append(os.getcwd())


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
    args = parser.parse_args()


    if args.config is not None:
        conf = readConfig(args.config)    # Read from config file
        if "host" in conf["mongoDB"]:       args.host = conf["mongoDB"]["host"]
        if "port" in conf["mongoDB"]:       args.port = conf["mongoDB"]["port"]
        if "username" in conf["mongoDB"]:   args.username = conf["mongoDB"]["username"]
        if "password" in conf["mongoDB"]:   args.password = conf["mongoDB"]["password"]
        if "host" in conf["flask"]:         args.fhost = conf["flask"]["host"]
        if "port" in conf["flask"]:         args.fport = conf["flask"]["port"]
        if "dbv" in conf["sw"]:             args.dbv = conf["sw"]["dbv"]

    return args





sys.path.append(os.getcwd())


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

sys.path.append(os.getcwd())

def sync():
    user = os.environ["USER"]
    hostname = os.environ["HOSTNAME"]
    mac = get_mac()

    args = getArgs()

    if not args.host or not args.port or not args.mhost or not args.mport:
        print(TOOLNAME+"ERROR! Local/Master host/port are not set!")
        exit(1)
    local_url = "mongodb://" + args.host + ":" + str(args.port)
    master_url = "mongodb://" + args.mhost + ":" + str(args.mport)
    print(TOOLNAME+"LocalDB server is: " + local_url)
    print(TOOLNAME+"Master server is: " + master_url)

    server_names = ["Local", "Master"]

    clients = [MongoClient(local_url), MongoClient(master_url)]
    dbs = [clients[0]["localdb"], clients[1]["localdb"]]
    dbs_sync = [clients[0]["ldbtool"], clients[1]["ldbtool"]]

    last_time_default = dateutil.parser.parse("2000-7-20T1:00:00.000Z")

    collection_names = dbs[1].collection_names()

    query = {"mac": mac} # TODO, This key will be changed
    sync_doc = dbs_sync[1]["sync"].find_one(query, sort=[("datetime", -1)])

    datetimes = []
    for collection_name in collection_names:
        if "fs.chunks" == collection_name: continue # Treat fs.chunks with fs.files

        print(TOOLNAME+"Collection: " + collection_name)

        last_time = last_time_default
        if sync_doc:
            last_time = sync_doc[collection_name]["datetime"]
            print("\tLast sync time is: " + str(last_time))

        query_key = ""
        if not "fs" in collection_name:
            query_key = "sys.mts"
        elif "fs.files" in collection_name:
            query_key = "uploadDate"

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

        documents = []
        totals = []
        for i in range(2):
            documents.append(dbs[i][collection_name].find({query_key: {"$gt": last_time} }))
            totals.append(documents[i].count())
            print("\t" + server_names[i] + " has " + str(totals[i]) + " documents ahead")


        if not args.y: continue

        x = [0, 1]
        y = [1, 0]
        for i in range(2): # Copy from local first, then copy from Master
            if totals[x[i]] == 0: continue

            dup_count = 0
            count = 0
            for document in documents[x[i]]:
                doc_dup = dbs[y[i]][collection_name].find_one({"_id": document["_id"]})
                if doc_dup:
                    if not doc_dup == document:
                        if i == 1: # Copy from Master
                            dup_count += 1
                else:
                    if "fs.files" in collection_name:
                        chunks_doc = dbs[x[i]]["fs.chunks"].find_one({"files_id": document["_id"]}) # Find linked doc in fs.chunks
                count += 1
                printProgressBar(count, totals[x[i]], prefix = '        Progress copy from ' + server_names[x[i]], suffix = 'Complete')

            if dup_count != 0:
                print("\t\tFound " + str(dup_count) + " dup docs")

    if not args.y: return

    query = {"user": user, "hostname": hostname, "mac": mac, "sys": {"rev": 0, "cts": datetime.datetime.now(), "mts": datetime.datetime.now()}}
    index = 0
    for collection_name in collection_names:
        if "fs.chunks" == collection_name:
            index = index - 1
            continue # Treat fs.chunks with fs.files
        query[collection_name] = {"datetime": datetimes[index]}
    pprint.PrettyPrinter(indent=4).pprint(query)

if __name__ == '__main__': sync()
