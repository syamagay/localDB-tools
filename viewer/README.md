status in 1th July 2019

# Start up Viewer Application
`viewer/setup_viewer.sh` can...
- Initialize configulation file
- Start Viewer Application

## Pre Requirement
- centOS7
- MongoDB is running
- python3
```bash
$ cd viewer
$ ./setup_viewer.sh
Local DB Server IP address: XXX.XXX.XXX.XXX
Local DB Server port: XXXXX

Are you sure that's correct? [y/n]
# answer 'y' and move on to the setup
y

Finished setting up of Viewer Application!!

Try accessing the DB viewer in your web browser...
From the DAQ machine: http://localhost:5000/localdb/
From other machines : http://XXX.XXX.XXX.XXX/localdb/

# you should run Viewer Application in screen
$ screen
$ python36 app.py --config conf.yml

Connecto to mongoDB server: mongodb://127.0.0.1:27017/localdb
 * Serving Flask app "app" (lazy loading)
 * Environment: production
   WARNING: Do not use the development server in a production environment.
   Use a production WSGI server instead.
 * Debug mode: off
HI 2019-07-01 22:55:37,102 - werkzeug - INFO -  * Running on http://XXX.XXX.XXX.XXX:5000/ (Press CTRL+C to quit)

[detached]
```
Access http://XXX.XXX.XXX.XXX:5000/ in your browser to check the Viewer Application.

# Advance
Viewer Application show the result plots in browser if PyROOT is avairable in the DB server.

```bash
# 1. Check if PyROOT is available
$ for ii in 1 2 3 4; do  if pydoc3 modules | cut -d " " -f${ii} | grep -x ROOT > /dev/null; then echo "PyROOT is available"; fi;  done
PyROOT is available    # Abailable
"No message"           # Not available 

# 2. Install ROOT software which can use PyROOT by Python3
$ root_install_dir=`pwd`
$ wget https://root.cern.ch/download/root_v6.16.00.source.tar.gz
$ tar zxf https://root.cern.ch/download/root_v6.16.00.source.tar.gz
$ rm -f https://root.cern.ch/download/root_v6.16.00.source.tar.gz
$ mv root-6.16.00 6.16.00
$ mkdir 6.16.00-build
$ cd 6.16.00-build
$ cmake -DCMAKE_INSTALL_PREFIX=${root_install_dir}/6.16.00-install -DPYTHON_EXECUTABLE=/usr/bin/python36 ../6.16.00
$ cmake --build . -- -j4
$ make install

# 3. Confirm if the installation was successful
$ source ${root_install_dir}/6.16.00-build/bin/thisroot.sh
$ for ii in 1 2 3 4; do  if pydoc3 modules | cut -d " " -f${ii} | grep -x ROOT > /dev/null; then echo "PyROOT is available"; fi;  done
PyROOT is available
```


----------------------------------
  
# Helpful Information

  ## summary.py

  You can add summary results for each stage and module in summary page by excuting script.

  _CAUTION_

  _This script can insert plots into database without outputting them to the display._

  _Please check the plots in browser before excuting this script._

  * modify parameter_default.json in directory web-app-db-yarr/scripts/json/

  ```
   "testType" : {
        "mapType" : [
            #,                 # mix value of x axis (1D plot) and z axis (2D plot)
            #,                 # max value of x axis (1D plot) and z axis (2D plot)
            bool[true/false],  # true if set log scale, or false if linear scale
            #                  # number of bins (1D plot) (same as max value if it is blank)
         ],
   }
  ```

  * run summary.py in web-app-db-yarr/scripts/writeDB/summary.py (flowchart is as follow)

  ```
   $ python summary.py -- ../../conf.yml
  ```

