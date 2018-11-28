import os, pwd # Import the user database on unix based systems
from binascii import a2b_base64 # convert a block of base64 data back to binary
from pdf2image import convert_from_path # convert pdf to image
import base64 # Base64 encoding scheme
import datetime, json

USER=pwd.getpwuid( os.geteuid() ).pw_name
USER_DIR = '/tmp/{}'.format( USER ) # directory to temporarily store image.pdf and image.png

IMAGE_TYPE = [ "png", "jpeg", "jpg", "JPEG", "jpe", "jfif", "pjpeg", "pjp", "gif" ]
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

