from binascii import a2b_base64
from pdf2image import convert_from_path
import logging, base64 

def bin_to_image(typ, binary):
    if typ == 'png' or typ == 'jpg':
        data = 'data:image/png;base64,' + binary
    if typ == 'pdf':
        file_pdf = open('/tmp/image.pdf','wb')
        binData=a2b_base64(binary)
        file_pdf.write(binData)
        file_pdf.close()
        path = '/tmp/image.pdf'
        image = convert_from_path(path)
        image[0].save('/tmp/image.png', 'png')
        binary_png = open('/tmp/image.png','rb')
        byte = base64.b64encode(binary_png.read()).decode()
        binary_png.close()
        data = 'data:image/png;base64,' + byte
    return data
