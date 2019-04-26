#!/usr/bin/env python3
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Get arguments
#################################

from __future__ import print_function # Use print() in python2 and 3
import yaml, argparse

menus=["summary", "verify", "sync"]

def readConfig(conf_path):
    f = open(conf_path, "r")
    conf = yaml.load(f)
    return conf

def getArgs():
    menus_str = ""
    for menu in menus:  menus_str += menu + ", "

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    #parser.add_argument("menu", nargs="+", help="Choose: "+menus_str, type=str)
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

    #if args.menu[0] not in menus: # Check menu
    #    print("[LDB] ERROR! No '" + args.menu[0] + "' menu in the tool.")
    #    exit(1)

    # Overwrite arguments from config file
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
