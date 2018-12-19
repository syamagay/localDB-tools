# Development Status

  This is the viewer of YARR-DB ( https://github.com/jlab-hep/Yarr/wiki )
  
  Currently you can use the following :

  * Check the list of modules and chips whose data taken by YARR in the top page ( for both FE-I4B and RD53A )
  * Check the result of scan for each module and chip ( for both FE-I4B and RD53A )
  * Write which run is summary for the module into database and check them in the module page ( for FE-I4B )
  * Make the plot of scan for each module with adjusting parameters ( for FE-I4B in local )

  Now implementing (comming soon) :
  
  * Write which run is summary for the module into database and check them in the module page ( for RD53A )
  * Make the plot of scan for each module with adjusting parameters ( for RD53A )
  * Request to create user account who can upload pictures into database ( for both of asics )

# User guide 

  ## Requirements

  * CentOS7
  * Firefox or Safari ( I checked that Chrome was not working well )
  * mongodb ( running ) ... refer to this wiki : https://github.com/jlab-hep/Yarr/wiki to install 
  * python 2.X or 3.X ( which can use PyROOT )
  * python modules : written in install_list
  * YARR S/W
  
  ## Preparation
  
  1) Set library path to ROOT and python
  
  ```
  $ source path/to/devtoolset-2/enable
  $ source path/to/bin/thispython.sh
  $ source path/to/bin/thisroot.sh
  ```
  
  2) Git clone this source
  
  ```
  $ git clone https://gitlab.cern.ch/akubota/web-app-db-yarr.git
  ```
  
  ## User Setting

  1) Make conf.yaml
  Copy web-app-db-yarr/scripts/yaml/web-conf.yml to web-app-db-yarr/conf.yml.
  ```
  $ cd path/to/web-app-db-yarr
  $ cp scripts/yaml/web-conf.yml conf.yml
  ```
  Change somethings if user's needs.
  - mongodb host/port ... change if user use mongodb in other server. 
  - mongodb db/userdb ... change if user set dbname (yarrdb/userdb) in mongodb.
  - mongodb username/password ... change if user set authorization into mongodb.
  - flask host/port ... change if user want to check viewer from external server.
  - python ... change if user use python3

  2) Install python modules
  ```
   $ cd path/to/web-app-db-yarr/scripts/install
   $ ./make_pipinstall.sh ---> generate pipinstall.py
   $ python pipinstall.py 
  ```
  - PIPPATH ... change if user use python3.

  3) Copy path/to/web-app-db-yarr/scripts/apache/config.conf to /etc/httpd/conf.d/web-app-db-yarr.conf if you use apache system 

  ## running web-app-db-yarr

  You can run web-app-db-yarr by excuting app.py, and check viewer by typing localhost:5000/yarrdb or <IPADDRESS>:5000/yarrdb/ in browser.
  You can check viewer by typing <IPADDRESS>/yarrdb/ if you use apache system.

  ```
   $  python app.py --config conf.yml
  ```
  
# helpful information
  ## Add summary plots

  You can add summary results for each stage and module in summary page by excuting script.

  _CAUTION_

  _This script can insert plots into database without outputting them to the display._

  _Please check the plots in browser before excuting this script._

  * make json file "identity.json" in directory web-app-db-yarr/scripts/json/ ( sample : "identity.json.save" )

  ```
    {
        "userIdentity" : "...",  # change to user who run scan program
    
        "institution"  : "..."   # change to user's institution
    }
  ```

  * modify parameter_default.json in directory web-app-db-yarr/scripts/json/

  ```
   "testType" : {
        "mapType" : [
            #,                 # max value of x axis (1D plot) and z axis (2D plot)
            bool[true/false],  # true if set log scale, or false if linear scale
            #                  # number of bins (1D plot) (same as max value if it is blank)
         ],
   }
  ```

  * run summary.py in web-app-db-yarr/scripts/writeDB/summary.py (flowchart is as follow)

  ```
   $ python summary.py
   
   --- stage list ---
   0 : wire bond
   1 : encapsulation

   # Type stage number >> 0
   # ok.

   # Type serial number of module >> ###-001
   # found.

   # Start to add summary plots 
    
         < General information >       
    ---------------------------------- 
     serialNumber : ###-001
     stage        : wirebond
     institution  : ...
     userIdentity : ...
    ---------------------------------- 
 
   # Continue to check results of this module? Type 'y' if continue >> y
    
         < Confirm information >       
    ---------------------------------- 
     0, analogscan
     runNumber   : 1003                 <---- by default the latest scan is set in this stage and test type
     datetime    : 20XX/XX/XX XX:XX:XX
    ----------------------------------
     1, digitalscan
     runNumber   : 1006                 <---- by default the latest scan is set in this stage and test type
     datetime    : 20XX/XX/XX XX:XX:XX
    ----------------------------------

   # Type 'y' if continue to make plots, or type the number before scan name if change run number >> 0 
 
     testType        : analogscan
     Run number list : 
                       1000 : 20XX/XX/XX XX:XX:XX
                       1001 : 20XX/XX/XX XX:XX:XX
                       1002 : 20XX/XX/XX XX:XX:XX
                       1003 : 20XX/XX/XX XX:XX:XX

   # Enter run number from this list for summary plot. If you want not to select, type "N". >> 1001 <---- you can change to other scan from latest scan

         < Confirm information >       
    ---------------------------------- 
     0, analogscan
     runNumber   : 1001                 <---- change
     datetime    : 20XX/XX/XX XX:XX:XX
    ----------------------------------
     1, digitalscan
     runNumber   : 1006                 <---- by default the latest scan is set in this stage and test type
     datetime    : 20XX/XX/XX XX:XX:XX
    ----------------------------------

   # Type 'y' if continue to make plots, or type the number before scan name if change run number >> y <---- this answer will only decide whether to make histogram
 
   # Start to make histograms.
   # Finish to make histograms of all scans.

   # Continue to insert plots into Database? Type 'y' if continue >> y <---- do not type "y" if you don't want to insert into database, then you can exit.
   # done.

  ```

  ## Setup pyenv 
  yum install some packages

  ```
   $ sudo yum install gcc zlib-devel bzip2 bzip2-devel readline readline-devel sqlite sqlite-devel openssl openssl-devel git
  ```

  install pyenv

  * clone pyenv repository

  ```
   $ git clone https://github.com/pyenv/pyenv.git ~/.pyenv
  ```

  * add path to pyenv in bash_profile

  ```
   $ echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bash_profile
   $ echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
   $ source ~/.bash_profile
  ```

  * check version of pyenv

  ```
   $ pyenv --version
   pyenv 1.2.2.6-g694b551
  ```

  install python X.X.X using pyenv

  * install

  ```
    $ pyenv install X.X.X
  ```

  + change version of python

  ```
    $ pyenv global X.X.X
    $ pyenv local X.X.X (only current directory)
  ```
  

