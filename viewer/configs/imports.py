#==============================
# Default modules
#==============================
import os, sys, datetime
import hashlib
import shutil
import uuid                         # Get mac address
import base64                       # Base64 encoding scheme
import gridfs                       # gridfs system 
import io

#==============================
# Log
#==============================
import logging, logging.config
import coloredlogs

#==============================
# For input
#==============================
import yaml, argparse


#==============================
# Pymongo and flask
#==============================
from flask            import (
        Flask, request, redirect, url_for, render_template, session, make_response, jsonify,
        Blueprint
    )

from flask_pymongo    import PyMongo # Flask pymongo, oh, why not use pymongo?
from pymongo          import MongoClient, DESCENDING # Pymongo, oh why not use flask-pymongo?

# Bson
from bson.objectid    import ObjectId 

# Upload system
from werkzeug         import secure_filename

# ?
from PIL              import Image

#==============================
# Plot
#==============================
import plotly
from plotly.graph_objs import *



#-----------------------------------------------------------------
# Global Variables
#-----------------------------------------------------------------
class LocalDB:
    db_mongo = ""
    def getMongo():
        return LocalDB.db_mongo

    def setMongo(mongo):
        LocalDB.db_mongo = mongo
