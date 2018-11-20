import os, datetime, json

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

def setTime(date):
    DIFF_FROM_UTC = 9
    time = (date+datetime.timedelta(hours=DIFF_FROM_UTC)).strftime("%Y/%m/%d %H:%M:%S")
    return time

def writeJson(fileName, data):
    f = open(fileName, 'w')
    json.dump(data,f,indent=4)
    f.close()        
 
def readJson(fileName):
    try:
        f = open(fileName, 'r')
    except:
        f = open("{}/parameter_default.json".format( os.path.dirname(os.path.abspath(__file__)), 'r'))
    json_data = json.load(f)
    f.close()  
    return json_data

def allowed_file(filename):
   return '.' in filename and \
       filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

  
