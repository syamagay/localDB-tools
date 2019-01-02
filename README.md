# Development Status

  This is the viewer for YARR-DB ( https://github.com/jlab-hep/Yarr/wiki )
  
  Currently you can use the following :

  * Check the list of modules and chips whose data taken by YARR in the top page ( for FE-I4B and RD53A )
  * Check the result of scan for each module and chip ( for FE-I4B and RD53A )
  * Write which run is summary for the module into database and check them in the module page ( for FE-I4B )
  * Make the plot of scan for each module with adjusting parameters ( for FE-I4B and RD53A )
  * Write administrator account into userDB by script 

  Now implementing (comming soon) :
  
  * Write which run is summary for the module into database and check them in the module page ( for RD53A )
  * Request to create user account who can upload pictures into database 
  * Write user account into userDB in browser

# Quich Tutorial

  ```
  $ git clone https://gitlab.cern.ch/akubota/web-app-db-yarr.git
  $ cd path/to/web-app-db-yarr
  $ cp scripts/yaml/web-conf.yml conf.yml
  $ python app.py --config conf.yml
  ```

# User Guide 

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
  ```
  $ cd path/to/web-app-db-yarr
  $ cp scripts/yaml/web-conf.yml conf.yml
  $ vim conf.yml
  ```

  2) Install python modules
  ```
  $ cd path/to/web-app-db-yarr/scripts/install
  $ ./make_pipinstall.sh ---> generate pipinstall.py
  $ python pipinstall.py 
  ```
  - PIPPATH ... change if user use python3.

  3) If you use apache system 
  ```
  $ cd path/to/web-app-db-yarr
  $ cp scripts/apache/config.conf /etc/httpd/conf.d/web-app-db-yarr.conf
  $ apachectl restart
  $ systemctl restart httpd
  ```

  ## running web-app-db-yarr
  ```
   $  python app.py --config conf.yml
  ```

  You can check viewer by typing localhost:5000/yarrdb or <IPADDRESS>:5000/yarrdb/ , or <IPADDRESS>/yarrdb/ if you use apache system.
  
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
  
