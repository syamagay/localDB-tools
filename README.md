# User guide 

# basic information

  ## Setting 
  
  requirements
  *  mongodb ( running ) 
  * python 2.X or 3.X ( which can use PyROOT )
  * python modules : install_list
  * YARR S/W
  
  ## preparetion
  
  set library path to ROOT and python
  
  ```
  $ source path/to/devtoolset-2/enable
  $ source path/to/bin/thispython.sh
  $ source path/to/bin/thisroot.sh
  ```
  
  git clone this source
  
  ```
  $ git clone https://gitlab.cern.ch/akubota/web-app-db-yarr.git
  ```
  
  setting before running web-app 

  modify setting.sh
  * APACHE : true : run by apache
  * PYTHON3 : true : you use python3
  * IPADDRESS : where you run this web app ( default : "'127.0.0.1'" )
  * PORT : port of mongoDB ( default : "27017" )
  modify codes by executing setting.sh

  ```
   $ ./setting.sh
  ```

  install python modules by executing make_pipinstall.sh and pipinstall.py

  ```
   $ ./make_pipinstall.sh ---> generate pipinstall.py
   $ python pipinstall.py 
  ```

  modify web-app-db-yarr.conf if you use apache system 

  ```
    WSGISocketPrefix run/wsgi
    <VirtualHost *:80>
        WSGIApplicationGroup %{GLOBAL}
        LoadModule wsgi_module /usr/local/Python/3.5.1/lib/python3.5/site-packages/mod_wsgi/server/mod_wsgi-py35.cpython-35m-x86_64-linux-gnu.so # modify for your environment
        WSGIDaemonProcess app user=apache group=apache threads=5
        WSGIScriptAlias /yarr /var/www/web-app-db-yarr/.wsgi
        <Directory /var/www/web-app-db-yarr>
            WSGIProcessGroup app
            WSGIScriptReloading On
            Order deny,allow
            Deny from all # modify by yourself
            Allow from all # modify by yourself
        </Directory>
    </VirtualHost>
  ```

  run web-app-db-yarr

  ```
   $  python app.py
   **first running** 
  Set administrator account ...
   < necessary information >
   - userName
   - firstName
   - lastName
   - institute
   - email
   - passWord
   - passWord agein
  Continue (y/n) >>
  # type "y" and enter information if you set administrator account 
  # after input or typing "n", web-app-db-yarr starts 
  # you can check viewer by typing <IPADDRESS>:5000 in browser
  ```
  
# helpful information
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
  
## web-app-db-yarr 
  | 
  |- app.py 
  |     : main program     
  |- PlotTools/, root.py, parameter_default.json
  |     : for making histogram using PyROOT
  |- func.py
  |- userfunc.py
  |- img.py 
  |
  |- static/
  |    |- assets 
  |    |    : for bootstrap 
  |    |- upload 
  |         : directory ro save images for displaying summary page temporarily
  |
  |- templates/
       |- toppage.html
       |    : top page page (html)
       |- component.html
       |    : module or chip page (html)
       |- display_index.html
       |    : part of displaying result in summary (html)
       |- photo.html
       |    : show photos page (html)
       |- photo_index.html
       |    : photo index (html)
       |- test_index.html
       |    : part of displaying test run list (html)
       |- result_XXX.html
       |    : part of displaying test result for each component (html)
       |- admin_XXX.html
       |    : admin page (html)
       |- error.html
       |   : error page (html)
       |- parts
            : header, loader, navigate bar, footer
