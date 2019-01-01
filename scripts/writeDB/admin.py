"""
script for create admin user 
and write admin's data into database

necessary information
- institution : that has server ownership
- user name   : required at login as admin
- password    : required at login as admin
"""
##### import #####
import os, sys, hashlib
from   getpass import getpass
from   pymongo import MongoClient

sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) + "/src" )
import func
from   arguments import *   # Pass command line arguments into app.py

args    = getArgs()            # Get command line arguments
if args.username : url = "mongodb://" + args.username + ":" + args.password + "@" + args.host + ":" + str(args.port) 
else :             url = "mongodb://"                                             + args.host + ":" + str(args.port) 
client  = MongoClient( url )
yarrdb  = client[args.db]
localdb = client[args.userdb]

def input_v( message ) :
    answer = ""
    if args.fpython == 2 : answer = raw_input( message ) 
    if args.fpython == 3 : answer =     input( message )
    return answer

##### FOR CREATE ADMINISTRATOR CODE #####
if localdb.user.find({ "type" : "administrator" }).count() == 0 : # if admin has already created, you cannot add admin 

    items = ['user name', 'institution', 'password', 'password again']

    # check python version
    print( "# Use python : version " + str(args.fpython) + "\n" )

    print( "# Create administrator account ..." )
    print( " " )

    answer = input_v( "# Type 'y' if conitinue to create administrator account >> " )

    if not answer == 'y' :
        print(" ")
        print("# Exit ...")
        sys.exit()     

    print(" ")
    admininfo = {}
    for item in items :
        info = ""
        while info == "" :
            if not (item == 'passWord' or item == 'passWord again') :
                input_item = ""
                while input_item = "" :
                    input_item = input_v( "# Enter {}. >> ".format(item) )
                print(" ")
                print( "# Your input ... {0} : {1}".format( item, input_item ) )
                print(" ")
                answer = ""
                while not answer == 'y' and not answer == 'm' :
                    answer = input_v( "# Type 'y' if conitune, or 'm' if want to change input item >> " )
    
                if answer == "y" : info = input_item
            else :
                info =  getpass("# Enter {}. >> ")
                print(" ")
                while not answer == 'y' and not answer == 'm' :
                    answer = input_v( "# Type 'y' if conitune, or 'm' if want to change input item >> " )
    
                if not answer == "y" : info = ""
           
    if not admininfo['passWord'] == admininfo['passWord again'] :
        print(" ")
        print("# Not match password, exit ...")
        sys.exit()     
    
    print(" ")
    print("# Please check the input information")
    for item in items :
        if not (item == 'passWord' or item == 'passWord again') :
            print(' - ' + item + ' : ' + admininfo[ item ])
    
    print(" ")
    answer = input_v("# Type 'y' if continue >> ")

    if not answer == 'y' :
        print(" ")
        print("# Exit ...")
        sys.exit()     

    items = ['user name', 'institution', 'password', 'password again']
    admininfo['password'] = hashlib.md5(admininfo['password'].encode("utf-8")).hexdigest()
    userinfo = { "userName"     : admininfo['user name'],
                 "userIdentity" : "Administrator",
                 "authority"    : 7,
                 "type"         : "administrator",
                 "institution"  : admininfo["insitution"],
                 "passWord"     : admininfo['pass word'] }
    
    print(" ")
    print("# Creating administrator account ...")

    localdb.user.insert( userinfo )
    print(" ")
    print("# Finish")
    print(" ")

