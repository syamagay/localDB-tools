# Default modules
import os, sys, datetime
import hashlib
import shutil
import uuid
import base64                          # Base64 encoding scheme
import gridfs                          # gridfs system 
import io

#-----------------------------------------------------------------
# Installed modules
#-----------------------------------------------------------------
# Flask
from flask            import (
        Flask, request, redirect, url_for, render_template, session, make_response, jsonify,
        Blueprint
    )

# Flask pymongo, oh, why not use pymongo?
from flask_pymongo    import PyMongo

# Pymongo, oh why not use flask-pymongo?
from pymongo          import MongoClient

# Bson
from bson.objectid    import ObjectId 

# Upload system
from werkzeug         import secure_filename

# ?
from PIL              import Image

# Import Yaml
import yaml

sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) )

# Will be replaced by ?
from scripts.src      import listset
from scripts.src      import static
from scripts.src.func import *


#-----------------------------------------------------------------
# Controllers
#-----------------------------------------------------------------
from controllers        import *
