#!/usr/bin/env python3
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Get arguments
#################################

from configs.development import * # Omajinai

menus=["summary", "verify", "sync"]

def readConfig(conf_path):
    f = open(conf_path, "r")
    conf = yaml.safe_load(f)
    return conf

def getArgs():
    menus_str = ""
    for menu in menus:  menus_str += menu + ", "

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("menu", nargs="+", help="Choose: "+menus_str, type=str)
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

    #if args.menu[0] not in menus: # Check menu
    #    print("[LDB] ERROR! No '" + args.menu[0] + "' menu in the tool.")
    #    exit(1)

    # Overwrite arguments from config file
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
