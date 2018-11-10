from binascii import a2b_base64
from pdf2image import convert_from_path
import logging, base64 
import os, getpass

IMAGE_FOLDER = '/tmp/{}'.format(os.getlogin())
def bin_to_image(typ, binary):
    if typ == 'png' or typ == 'jpg':
        data = 'data:image/png;base64,' + binary
    if typ == 'pdf':
        file_pdf = open('{}/image.pdf'.format(IMAGE_FOLDER),'wb')
        binData=a2b_base64(binary)
        file_pdf.write(binData)
        file_pdf.close()
        path = '{}/image.pdf'.format(IMAGE_FOLDER)
        image = convert_from_path(path)
        image[0].save('{}/image.png'.format(IMAGE_FOLDER), 'png')
        binary_png = open('{}/image.png'.format(IMAGE_FOLDER),'rb')
        byte = base64.b64encode(binary_png.read()).decode()
        binary_png.close()
        data = 'data:image/png;base64,' + byte
    return data
