from flask import Blueprint
import pwd

USER = pwd.getpwuid( os.geteuid() ).pw_name

app = Blueprint("upload", __name__,
    static_url_path='/tmp/{}/static'.format( USER ), static_folder='/tmp/{}/static'.format( USER )
)
