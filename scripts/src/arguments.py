#!/usr/bin/python

# Pass arguments to app.py

import argparse # Pass command line arguments into python script
import yaml     # Read YAML config file

def readConfig(conf_path):
    f = open(conf_path, "r")
    conf = yaml.safe_load(f)
    return conf

def getArgs():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", "-f",   help="Config file path", type=str)
    parser.add_argument("--host",           help="Host",             type=str)
    parser.add_argument("--port",           help="Port",             type=int)
    parser.add_argument("--db",             help="Db",               type=str)
    parser.add_argument("--version",        help="DB Version",       type=int)
    parser.add_argument("--username", "-u", help="User name",        type=str)
    parser.add_argument("--password", "-p", help="User password",    type=str)
    parser.add_argument("--fhost",          help="Flask Host",       type=str)
    parser.add_argument("--fport",          help="Flask Port",       type=int)
    parser.add_argument("--localdbkey", "-k", help="User Info",      type=str)
    parser.add_argument("--userdb",         help="userdb",           type=str, default="localdb_user")
    parser.add_argument("--lokaldbkey", "-k", help="User Info",      type=str)
    parser.add_argument("--fhost",          help="Flask Host",       type=str, default="localhost")
    parser.add_argument("--fport",          help="Flask Port",       type=int, default=5000)
    parser.add_argument("--fpython",        help="Python Version",   type=int, default=2)
    parser.add_argument("--ssl",            help="Enable ssl",       action='store_true')
    parser.add_argument("--sslPEMKeyFile",  help="Specify client certificate", type=str)
    parser.add_argument("--sslCAFile",      help="Specify CA certificate", type=str)
    parser.add_argument("--is_development", help="Is development env?", action="store_true")

    args = parser.parse_args()

    # Overwrite arguments from config file
    if args.config is not None:
        conf = readConfig(args.config)    # Read from config file
        if "mongoDB" in conf:
            if "host"       in conf["mongoDB"] and not args.host          : args.host            = conf["mongoDB"]["host"]
            if "port"       in conf["mongoDB"] and not args.port          : args.port            = conf["mongoDB"]["port"]
            if "db"         in conf["mongoDB"] and not args.db            : args.db              = conf["mongoDB"]["db"]
            if "version"    in conf["mongoDB"] and not args.version       : args.version         = conf["mongoDB"]["version"]
            if "username"   in conf["mongoDB"] and not args.username      : args.username       = conf["mongoDB"]["username"]
            if "password"   in conf["mongoDB"] and not args.password      : args.password       = conf["mongoDB"]["password"]
            if "localdbkey" in conf["mongoDB"] and not args.localdbkey    : args.localdbkey     = conf["mongoDB"]["localdbkey"]
        if "flask" in conf:
            if "host"       in conf["flask"]   and not args.fhost         : args.fhost          = conf["flask"]["host"]
            if "port"       in conf["flask"]   and not args.fport         : args.fport          = conf["flask"]["port"]
        if "userdb" in conf:
            if "db"         in conf["userDB"]  and not args.udb           : args.userdb     = conf["userDB"]["db"]
        if "ssl" in conf:
            if "enabled"    in conf["ssl"]     and not args.ssl           : args.ssl            = conf["ssl"]["enabled"]
            if "PEMKeyFile" in conf["ssl"]     and not args.sslPEMKeyFile : args.sslPEMKeyFile  = conf["ssl"]["PEMKeyFile"]
            if "CAFile"     in conf["ssl"]     and not args.sslCAFile     : args.sslCAFile      = conf["ssl"]["CAFile"]
        if "is_development" in conf and not args.is_development: args.is_development = conf["is_development"]

    # default
    if not args.host: args.host="localhost"
    if not args.port: args.port=27017
    if not args.db: args.db="localdb"
    if not args.fhost: args.fhost="localhost"
    if not args.fport: args.fport=5000

    return args
