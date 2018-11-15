import os, pwd # Import the user database on unix based systems
from binascii import a2b_base64 # convert a block of base64 data back to binary
from pdf2image import convert_from_path # convert pdf to image
import base64 # Base64 encoding scheme
import getpass

USER=pwd.getpwuid( os.geteuid() ).pw_name
IMAGE_DIR = '/tmp/{}'.format( USER ) # directory to temporarily store image.pdf and image.png

IMAGE_TYPE = [ "png", "jpeg", "jpg", "JPEG", "jpe", "jfif", "pjpeg", "pjp", "gif" ]

def bin_to_image( typ, binary ) :
    if typ in IMAGE_TYPE :
        data = 'data:image/png;base64,' + binary
    if typ == 'pdf' :
        filePdf = open( '{}/image.pdf'.format( IMAGE_DIR ), 'wb' )
        binData = a2b_base64( binary )
        filePdf.write( binData )
        filePdf.close()
        path = '{}/image.pdf'.format( IMAGE_DIR )
        image = convert_from_path( path )
        image[0].save( '{}/image.png'.format( IMAGE_DIR ), 'png' )
        binaryPng = open( '{}/image.png'.format( IMAGE_DIR ), 'rb' )
        byte = base64.b64encode( binaryPng.read() ).decode()
        binaryPng.close()
        data = 'data:image/png;base64,' + byte
    return data
