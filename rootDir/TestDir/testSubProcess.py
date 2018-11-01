import subprocess
 
cmd = "ls -l"
subprocess.call(cmd.split())

runNumber = 1329
cmd = "/usr/bin/python ../YARR_PyAna/drawFei4ModuleMap.py 1329"
subprocess.call(cmd.split())
