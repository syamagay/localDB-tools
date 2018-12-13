import os, sys
sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) + "/src" )

from getpass import getpass
import hashlib

from pymongo import MongoClient
import func
from arguments import *   # Pass command line arguments into app.py

args = getArgs()            # Get command line arguments
client = MongoClient(host=args.host, port=args.port)
localdb = client['yarrlocal']

### FOR CREATE ADMINISTRATOR CODE###

if localdb.user.find({ "type" : "administrator" }).count() == 0 :
    # check python version
    print( "# Use python : version " + str(args.fpython) + "\n")

    print("Set administrator account ...")
    print(" ")
    print("< necessary information >")
    items = ['userName', 'firstName', 'lastName', 'institute', 'email', 'passWord', 'passWord again']
    
    for item in items :
        print(' - ' + item)
        
    print(" ")

    if args.fpython == 2 :
        answer = raw_input('Continue (y/n) >> ')
    elif args.fpython == 3 :
        answer = input('Continue (y/n) >> ')

    if answer == 'y' : 
    
        print(" ")
        admininfo = []
        for item in items :
            if not (item == 'passWord' or item == 'passWord again') :
                print("Input {}".format(item))
                if args.fpython == 2 :
                    admininfo.append(raw_input(' >> ')) #python2
                elif args.fpython == 3 :
                    admininfo.append(input(' >> ')) #python3
            else :
                print("Input {}".format(item))
                if args.fpython == 2 :
                    admininfo.append(getpass(' >> ')) #python2
                elif args.fpython == 3 :
                    admininfo.append(getpass(' >> ')) #python3
        
        if not admininfo[5] == admininfo[6] :
            print("not match password, exit ...")
            sys.exit()     
        
        print(" ")
        print("Please check the input information")
        for item in items :
            if not (item == 'passWord' or item == 'passWord again') :
                print(' - ' + item + ' : ' + admininfo[items.index( item )])
        
        print(" ")
        if args.fpython == 2 :
            answer = raw_input('Continue (y/n) >> ')
        elif args.fpython == 3 :
            answer = input('Continue (y/n) >> ')

        if answer == 'y' : 
            admininfo[5] = hashlib.md5(admininfo[5].encode("utf-8")).hexdigest()
            userinfo = { "userName"  : admininfo[0],
                         "firstName" : admininfo[1],
                         "lastName"  : admininfo[2],
                         "authority" : 7,
                         "type"      : "administrator",
                         "institute" : admininfo[3],
                         "email"     : admininfo[4],
                         "password"  : admininfo[5] }
        
            print(" ")
            print("Creating administrator account ...")
            localdb.user.insert({ "userName"  : userinfo['userName'],
                                  "firstName" : userinfo['firstName'],
                                  "lastName"  : userinfo['lastName'],
                                  "authority" : int(userinfo['authority']),
                                  "institute" : userinfo['institute'],
                                  "type"      : userinfo['type'], 
                                  "email"     : userinfo['email'],
                                  "passWord"  : userinfo['password'] })
            print(" ")
            print("done")
        else :
            print(" ")
            print("exit...")

    print(" ")
