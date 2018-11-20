from bson.objectid import ObjectId 
from bson.binary import BINARY_SUBTYPE

import pymongo
from pymongo import MongoClient

from getpass import getpass
import hashlib

client = MongoClient(host='localhost', port=28000)
localdb = client['yarrlocal']

def add_request(userinfo) :
    password = hashlib.md5(userinfo[5].encode("utf-8")).hexdigest()
    localdb.request.insert({ "userName"  : userinfo[0],
                             "firstName" : userinfo[1],
                             "lastName"  : userinfo[2],
                             "email"     : userinfo[3],
                             "institute" : userinfo[4],
                             "type"      : "user", 
                             "password"  : password })
def add_user(userinfo) :
    localdb.user.insert({ "userName"  : userinfo['userName'],
                          "firstName" : userinfo['firstName'],
                          "lastName"  : userinfo['lastName'],
                          "authority" : int(userinfo['authority']),
                          "institute" : userinfo['institute'],
                          "type"      : userinfo['type'], 
                          "email"     : userinfo['email'],
                          "passWord"  : userinfo['password'] })
   
def remove_request(userid) :
    localdb.request.remove({ "_id" : ObjectId(userid) })

def remove_user(userid) :
    localdb.user.remove({ "_id" : ObjectId(userid) })


### FOR CREATE ADMINISTRATOR CODE###

import sys

if localdb.user.find({ "type" : "administrator" }).count() == 0 :
    print("Set administrator account ...")
    print(" ")
    print("< necessary information >")
    items = ['userName', 'firstName', 'lastName', 'institute', 'email', 'passWord', 'passWord again']
    
    for item in items :
        print(' - ' + item)
        
    print(" ")
    if raw_input('Continue (y/n) >> ') == 'y' : #python2
    
        print(" ")
        admininfo = []
        for item in items :
            if not (item == 'passWord' or item == 'passWord again') :
                print("Input {}".format(item))
                admininfo.append(raw_input(' >> ')) #python2
                #admininfo.append(input(' >> ')) #python3
            else :
                print("Input {}".format(item))
                admininfo.append(getpass(' >> ')) #python2
                #admininfo.append(getpass(' >> ')) #python3
        
        if not admininfo[5] == admininfo[6] :
            print("not match password, exit ...")
            sys.exit()     
        
        print(" ")
        print("Please check the input information")
        for item in items :
            if not (item == 'passWord' or item == 'passWord again') :
                print(' - ' + item + ' : ' + admininfo[items.index( item )])
        
        print(" ")
        if raw_input('Continue (y/n) >> ') == 'y' : #python2
        #if input('Continue (y/n) >> ') == 'y' :#python3
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
            add_user(userinfo) 
        
            print(" ")
            print("done")
        else :
            print(" ")
            print("exit...")

    print(" ")
