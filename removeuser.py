import bson.objectid, bson.binary 
import pymongo
from pymongo import MongoClient
from getpass import getpass

client = MongoClient(host='localhost', port=28000)
userdb = client['user']

Admin = userdb.user.find_one({ "userName" : "administrator" })
print('Input administrator password')  
admin_pass = getpass('>> ')
if Admin['passWord'] != admin_pass :
    print("Permission denied")
else :
    print('Enter user name to remove')
    #user_name = input('>> ') #python3
    user_name = raw_input('>> ') #python2
    
    User = userdb.user.find_one({ "userName" : user_name })
    if User :
        userdb.user.remove({ "userName" : user_name })
        if userdb.user.find({ "userName" : user_name }).count() == 0:
            print('Removed user : {}'.format(User['userName']))
        else :
            print('Failed to remove new user : {}'.format(User['userName'])) 
    else :
        print('User "{}" is not exist, aborting ...'.format(User['userName']))
