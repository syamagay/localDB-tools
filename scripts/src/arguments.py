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
    parser.add_argument("--config", "-f",           help="Config file path",             type=str)
    parser.add_argument("--host",                   help="Host",                         type=str)
    parser.add_argument("--port",                   help="Port",                         type=int)
    parser.add_argument("--db",                     help="Db",                           type=str)
    parser.add_argument("--username", "-u",         help="User name",                    type=str)
    parser.add_argument("--password", "-p",         help="User password",                type=str)
    parser.add_argument("--KeyFile",                help="Path to user key file",        type=str)
    parser.add_argument("--fhost",                  help="Flask Host",                   type=str)
    parser.add_argument("--fport",                  help="Flask Port",                   type=int)
    parser.add_argument("--userdb",                 help="userdb",                       type=str)
    parser.add_argument("--ssl",                    help="Enable ssl",                   action='store_true')
    parser.add_argument("--sslPEMKeyFile",          help="Path to certificate",          type=str)
    parser.add_argument("--sslCAFile",              help="Path to CA file",              type=str)
    parser.add_argument("--tls",                    help="Enable tls",                   action='store_true')
    parser.add_argument("--tlsCertificateKeyFile",  help="Path to certificate",          type=str)
    parser.add_argument("--tlsCAFile",              help="Path to CA file",              type=str)
    parser.add_argument("--auth",                   help="Set authentication mechanism", type=str)
    parser.add_argument("--is_development",         help="Is development env?",          action="store_true")

    args = parser.parse_args()

    # Overwrite arguments from config file
    if args.config is not None:
        conf = readConfig(args.config)    # Read from config file
        if "mongoDB" in conf:
            if "host"       in conf["mongoDB"] and not args.host          : args.host            = conf["mongoDB"]["host"]
            if "port"       in conf["mongoDB"] and not args.port          : args.port            = conf["mongoDB"]["port"]
            if "db"         in conf["mongoDB"] and not args.db            : args.db              = conf["mongoDB"]["db"]
            if "username"   in conf["mongoDB"] and not args.username      : args.username        = conf["mongoDB"]["username"]
            if "password"   in conf["mongoDB"] and not args.password      : args.password        = conf["mongoDB"]["password"]
            if "KeyFile"    in conf["mongoDB"] and not args.KeyFile       : args.KeyFile         = conf["mongoDB"]["KeyFile"]
            if "ssl"        in conf["mongoDB"]:
                if "enabled"            in conf["mongoDB"]["ssl"] and not args.ssl                   : args.ssl                   = conf["mongoDB"]["ssl"]["enabled"]
                if "PEMKeyFile"         in conf["mongoDB"]["ssl"] and not args.sslPEMKeyFile         : args.sslPEMKeyFile         = conf["mongoDB"]["ssl"]["PEMKeyFile"]
                if "CAFile"             in conf["mongoDB"]["ssl"] and not args.sslCAFile             : args.sslCAFile             = conf["mongoDB"]["ssl"]["CAFile"]
            if "tls"        in conf["mongoDB"]:
                if "enabled"            in conf["mongoDB"]["tls"] and not args.tls                   : args.tls                   = conf["mongoDB"]["tls"]["enabled"]
                if "CertificateKeyFile" in conf["mongoDB"]["tls"] and not args.tlsCertificateKeyFile : args.tlsCertificateKeyFile = conf["mongoDB"]["tls"]["CertificateKeyFile"]
                if "CAFile"             in conf["mongoDB"]["tls"] and not args.tlsCAFile             : args.tlsCAFile             = conf["mongoDB"]["tls"]["CAFile"]
            if "auth"       in conf["mongoDB"] and not args.auth          : args.auth            = conf["mongoDB"]["auth"]
        if "flask" in conf:
            if "host"       in conf["flask"]   and not args.fhost         : args.fhost           = conf["flask"]["host"]
            if "port"       in conf["flask"]   and not args.fport         : args.fport           = conf["flask"]["port"]
        if "userdb" in conf:
            if "db"         in conf["userDB"]  and not args.udb           : args.userdb          = conf["userDB"]["db"]
        if "is_development" in conf            and not args.is_development: args.is_development  = conf["is_development"]

    # default
    if not args.host   : args.host   = "localhost"
    if not args.port   : args.port   = 27017
    if not args.db     : args.db     = "localdb"
    if not args.fhost  : args.fhost  = "localhost"
    if not args.fport  : args.fport  = 5000
    if not args.userdb : args.userdb = "localdb_user"

    return args
