from flask import Blueprint
import os, pwd

USER = pwd.getpwuid( os.geteuid() ).pw_name

app = Blueprint("upload", __name__,
    static_url_path='/tmp/{}/static'.format( USER ), static_folder='/tmp/{}/static'.format( USER )
)

app = Blueprint("result", __name__,
    static_url_path='/tmp/{}/result'.format( USER ), static_folder='/tmp/{}/result'.format( USER )
)
