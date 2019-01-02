import os, pwd # Import the user database on unix based systems
from binascii import a2b_base64 # convert a block of base64 data back to binary
from pdf2image import convert_from_path # convert pdf to image
import base64 # Base64 encoding scheme
import datetime, json
from arguments import *   # Pass command line arguments into app.py
from bson.objectid import ObjectId 
from pymongo import MongoClient

from getpass import getpass
import hashlib

# set mongodb
args = getArgs()            # Get command line arguments
if args.username is None:
    url = "mongodb://" + args.host + ":" + str(args.port) 
else:
    url = "mongodb://" + args.username + ":" + args.password + "@" + args.host + ":" + str(args.port) 
client = MongoClient( url )
userdb = client['yarrlocal']

USER=pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) # directory to temporarily store image.pdf and image.png

IMAGE_TYPE = [ "png", "jpeg", "jpg", "JPEG", "jpe", "jfif", "pjpeg", "pjp", "gif" ]
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

def setTime(date):
    DIFF_FROM_UTC = 9 # for Japan
    time = (date+datetime.timedelta(hours=DIFF_FROM_UTC)).strftime("%Y/%m/%d %H:%M:%S")
    return time

def allowed_file(filename):
   return '.' in filename and \
       filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def bin_to_image( typ, binary ) :
    if typ in IMAGE_TYPE :
        data = 'data:image/png;base64,' + binary
    if typ == 'pdf' :
        filePdf = open( '{}/image.pdf'.format( USER_DIR ), 'wb' )
        binData = a2b_base64( binary )
        filePdf.write( binData )
        filePdf.close()
        path = '{}/image.pdf'.format( USER_DIR )
        image = convert_from_path( path )
        image[0].save( '{}/image.png'.format( USER_DIR ), 'png' )
        binaryPng = open( '{}/image.png'.format( USER_DIR ), 'rb' )
        byte = base64.b64encode( binaryPng.read() ).decode()
        binaryPng.close()
        data = 'data:image/png;base64,' + byte
    return data

def add_request(userinfo) :
    password = hashlib.md5(userinfo[5].encode("utf-8")).hexdigest()
    userdb.request.insert({ "userName"  : userinfo[0],
                             "firstName" : userinfo[1],
                             "lastName"  : userinfo[2],
                             "email"     : userinfo[3],
                             "institution" : userinfo[4],
                             "type"      : "user", 
                             "password"  : password })
def add_user(userinfo) :
    userdb.user.insert({ "userName"  : userinfo['userName'],
                          "firstName" : userinfo['firstName'],
                          "lastName"  : userinfo['lastName'],
                          "authority" : int(userinfo['authority']),
                          "institution" : userinfo['institution'],
                          "type"      : userinfo['type'], 
                          "email"     : userinfo['email'],
                          "passWord"  : userinfo['password'] })
   
def remove_request(userid) :
    userdb.request.remove({ "_id" : ObjectId(userid) })

def remove_user(userid) :
    userdb.user.remove({ "_id" : ObjectId(userid) })

