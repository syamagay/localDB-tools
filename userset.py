IPADDRESS=CHANGEIP
PORT=CHANGEPORT

import os, sys

os.environ['LIBPATH']=ROOTLIB
os.environ['LD_LIBRARY_PATH']=ROOTLIB
os.environ['PYTHONPATH']=ROOTLIB
sys.path.append(ROOTLIB)
