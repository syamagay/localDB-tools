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
userdb = client[args.userdb]

##### function #####
def input_v( message ) :
    answer = ""
    if args.fpython == 2 : answer = raw_input( message ) 
    if args.fpython == 3 : answer =     input( message )
    return answer

##### FOR CREATE ADMINISTRATOR CODE #####
if not userdb.user.find({ "type" : "administrator" }).count() == 0 :
    print( "Administrator account is already exist, exit ..." )
    sys.exit()     

items = ['user name', 'institution', 'password', 'password again']

# check python version
print( "# Use python : version " + str(args.fpython) )
print( " " )
print( "# Create administrator account ..." )
print( " " )

answer = ""
while answer == "" :
    answer = input_v( "# Type 'y' if conitinue to create administrator account >> " )

if not answer == 'y' :
    print(" ")
    print("# Exit ...")
    sys.exit()     

admininfo = {}
for item in items :
    info = ""
    while info == "" :
        if not (item == 'password' or item == 'password again') :
            print(" ")
            info = input_v( "# Enter {}. >> ".format(item) )
        else :
            print(" ")
            info =  getpass("# Enter {}. >> ".format(item))
    admininfo.update({ item : info })
       
if not admininfo['password'] == admininfo['password again'] :
    print(" ")
    print("# Not match password, exit ...")
    sys.exit()     

print(" ")
print("# Please check the input information")
print(" ")
print("------------------------------------")
for item in items :
    if not (item == 'password' or item == 'password again') :
        print(' ' + item + ' : ' + admininfo[ item ])
print("------------------------------------")
print(" ")
answer = input_v("# Type 'y' if continue >> ")

if not answer == 'y' :
    print(" ")
    print("# Exit ...")
    sys.exit()     

admininfo['password'] = hashlib.md5(admininfo['password'].encode("utf-8")).hexdigest()
userinfo = { "userName"     : admininfo['user name'],
             "userIdentity" : "Administrator",
             "authority"    : 7,
             "type"         : "administrator",
             "institution"  : admininfo["institution"],
             "passWord"     : admininfo['password'] }

print(" ")
print("# Creating administrator account ...")

userdb.user.insert( userinfo )
print(" ")
print("# Finish")
print(" ")

