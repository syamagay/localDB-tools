import datetime, json

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
        f = open("parameter_default.json", 'r')
    json_data = json.load(f)
    f.close()  
    return json_data
   
