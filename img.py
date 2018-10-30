import logging 

def bin_to_image(typ, binary):
#def bin_to_image():
    #typ = 'png'
    if typ == 'png':
      data = 'data:image/png;base64,' + binary
    if typ == 'pdf':
      data = 'data:application/pdf;base64,' + binary
    #logging.log(100,data)
    #logging.info('info')
    return data
