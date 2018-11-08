import bson.objectid, bson.binary 
import pymongo
from pymongo import MongoClient
from getpass import getpass

client = MongoClient(host='localhost', port=28000)
userdb = client['user']

user_name = "administrator"

User = userdb.user.find_one({ "userName" : user_name })
if User :
    print('User "{}" is already exist, aborting ...'.format(User['userName']))
else :
    print('Set password')
    #pass_word_1st = input('>> ') #pythhon3
    pass_word_1st = getpass('>> ') #python2
    
    print('Confirm password')
    #pass_word_2nd = input('>> ') #pythhon3
    pass_word_2nd = getpass('>> ') #python2
    
    if pass_word_1st != pass_word_2nd :
        print('Password does not match the confirm password, aborting ...')
    else :
        userdb.user.insert({ "userName" : user_name,
                             "passWord" : pass_word_1st })
        User = userdb.user.find_one({ "userName" : user_name })
        if User['userName'] == user_name and User['passWord'] == pass_word_1st :
            print('Succeeded to create new user : {}'.format(User['userName']))
        else :
            print('Failed to create new user : {}'.format(User['userName'])) 
