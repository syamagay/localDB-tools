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
    parser.add_argument("--host",           help="Host",             type=str, default="localhost")
    parser.add_argument("--port",           help="Port",             type=int, default=27017)
    parser.add_argument("--db",             help="Db",               type=str, default="localdb")
    parser.add_argument("--version",        help="DB Version",       type=int)
    parser.add_argument("--oldversion",     help="old DB Version",   type=float)
    parser.add_argument("--username", "-u", help="User name",        type=str)
    parser.add_argument("--password", "-p", help="User password",    type=str)
    parser.add_argument("--fhost",          help="Flask Host",       type=str, default="localhost")
    parser.add_argument("--fport",          help="Flask Port",       type=int, default=5000)
    parser.add_argument("--fpython",        help="Python Version",   type=int, default=2)
    parser.add_argument("--is_development", help="Is development env?", action="store_true")

    args = parser.parse_args()

    # Overwrite arguments from config file
    if args.config is not None:
        conf = readConfig(args.config)    # Read from config file
        if "host"      in conf["mongoDB"]: args.host        = conf["mongoDB"]["host"]
        if "port"      in conf["mongoDB"]: args.port        = conf["mongoDB"]["port"]
        if "db"        in conf["mongoDB"]: args.db          = conf["mongoDB"]["db"]
        if "version"   in conf["mongoDB"]: args.version     = conf["mongoDB"]["version"]
        if "oldversion"in conf["mongoDB"]: args.oldversion = conf["mongoDB"]["oldversion"]
        if "username"  in conf["mongoDB"]: args.username   = conf["mongoDB"]["username"]
        if "password"  in conf["mongoDB"]: args.password   = conf["mongoDB"]["password"]
        if "host"      in conf["flask"]:   args.fhost      = conf["flask"]["host"]
        if "port"      in conf["flask"]:   args.fport      = conf["flask"]["port"]
        if "python"    in conf:            args.fpython    = conf["python"]
        if "is_development"    in conf:     args.is_development = conf["is_development"]

    return args
