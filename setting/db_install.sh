#!/bin/bash
##################################################################
# Install script for the QA/QC storage system
# Usage : ./db_install.sh [IP address]
# Instruction : https://github.com/jlab-hep/Yarr/wiki/Installation
#
# Contacts : Minoru Hirose (hirose@champ.hep.sci.osaka-u.ac.jp)
#            Eunchong Kim (kim@hep.phys.titech.ac.jp)
#            Arisa Kubota (kubota.a.af@m.titech.ac.jp)
##################################################################
set -e

ip=`ip -f inet -o addr show| grep -e en -e eth|cut -d\  -f 7 | cut -d/ -f 1`
port=27017
dbname="localdb"
cachedir=/usr/local/localdb/cacheDB

# setting site config
address=${cachedir}/lib/address.json
declare -a nic=()  
num=0
for DEV in `find /sys/devices -name net | grep -v virtual`; 
do 
    nic[${num}]=`ls --color=none ${DEV}`
    num=$(( num + 1 ))
done
dbnic="${nic[0]}"
if [ -f ${address} ]; then
    tmpmacaddress=`cat ${address}|grep 'macAddress'|awk -F'["]' '{print $4}'`
    tmpname=`cat ${address}|grep 'name'|awk -F'["]' '{print $4}'`
    tmpinstitution=`cat ${address}|grep 'institution'|awk -F'["]' '{print $4}'`
fi
macaddress=`ifconfig ${dbnic} | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}'`
if [ -f ${address} ] && [ ${macaddress} = ${tmpmacaddress} ] && [ ${HOSTNAME} = ${tmpname} ] && [ -n ${tmpinstitution} ]; then
    echo "Site Config file is exist: ${address}"
    institution=${tmpinstitution}
else
    echo "Enter the institution name where this machine (MAC address: ${macaddress}) is or 'exit' ... "
    read -p "> " -a answer
    while [ ${#answer[@]} == 0 ]; 
    do
        echo "Enter the institution name where this machine (MAC address: ${macaddress}) is or 'exit' ... "
        read -p "> " -a answer
    done
    if [ ${answer[0]} == "exit" ]; then
        echo "Exit ..."
        echo " "
        exit
    else
        for a in ${answer[@]}; do
            institution="${institution#_}_${a}"
        done
    fi
fi

echo " "
echo "Test Site Information"
echo "  MAC address: ${macaddress}"
echo "  Machine Name: ${HOSTNAME}"   
echo "  Institution: ${institution}"
echo " "
echo "Are you sure that's correct? [y/n]"
read -p "> " answer
while [ -z ${answer} ]; 
do
    echo "Are you sure that's correct? [y/n]"
    read -p "> " answer
done
echo " "

if [ ${answer} != "y" ]; then
    if [ -f ${address} ]; then 
        echo "Remove Site Config file: ${address}"
        echo " "
        rm ${address}
    fi
    echo "Try again setup.sh, Exit ..."
    echo " "
    exit
fi

### start installation

LOGFILE="instlog."`date "+%Y%m%d_%H%M%S"`
#exec 2>&1> >(awk '{print strftime("[%Y-%m-%d %H:%M:%S] "),$0 } { fflush() } ' | tee $LOGFILE)
exec 2> >(awk '{print strftime("[%Y-%m-%d %H:%M:%S] "),$0 } { fflush() } ' | tee $LOGFILE) 1>&2

trap 'echo ""; echo "Installation stopped by SIGINT!!"; echo "You may be in unknown state."; echo "Check ${LOGFILE} for debugging in case of a problem of re-executing this script."; exit 1' 2

#packages list to be required
yumpackages=(
    "epel-release.noarch"
    "centos-release-scl.noarch"
    "cmake"
    "bc.x86_64"
    "wget.x86_64"
    "rh-mongodb36-mongo-cxx-driver-devel.x86_64"
    "rh-mongodb36-boost-devel.x86_64"
    "mongodb-org.x86_64"
    "devtoolset-7.x86_64"
    "gnuplot.x86_64"
    "python.x86_64"
    "httpd.x86_64"
    "python36" 
    "python36-devel" 
    "python36-pip" 
    "python36-tkinter"
)
services=(
    "mongod"
    "httpd"
)

#checking what is missing for localDB and viewer
echo "Looking for missing things for Yarr-localDB and its viewer..."
echo "-------------------------------------------------------------"
if [ ! -e "/etc/yum.repos.d/mongodb-org-3.6.repo" ]; then
    echo "Add: mongodb-org-3.6 repository in /etc/yum.repos.d/mongodb-org-3.6.repo."
fi
for pac in ${yumpackages[@]}; do
    if ! yum info ${pac} 2>&1 | grep "Installed Packages" > /dev/null; then
	echo "yum install: ${pac}"
    fi
done
if ! getsebool httpd_can_network_connect | grep off > /dev/null; then
    echo "SELinux: turning on httpd_can_network_connect"
fi
if ! sudo firewall-cmd --list-all | grep http > /dev/null; then
    echo "Firewall: opening port=80/tcp for appache."
fi
if ! sudo firewall-cmd --list-ports --zone=public --permanent | grep 5000/tcp > /dev/null; then
    echo "Firewall: opening port=5000/tcp for viewer application."
fi
for svc in ${services[@]}; do
    if ! systemctl status ${svc} 2>&1 | grep running > /dev/null; then
        echo "Start: ${svc}"
    fi
    if ! systemctl list-unit-files -t service|grep enabled 2>&1 | grep ${svc} > /dev/null; then
        echo "Enable: ${svc}"
    fi
done
echo "----------------------------------------------------"

#installing necessary packages if not yet installed
echo "Start installing necessary packages..."
#adding mongoDB repository and installing mongoDB
if [ -e "/etc/yum.repos.d/mongodb-org-3.6.repo" ]; then
    echo "mongodb-org-3.6 repository already installed. Nothing to do."
else
    echo "Adding mongodb-org-3.6 repository."
    sudo sh -c "echo \"[mongodb-org-3.6]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/7Server/mongodb-org/3.6/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-3.6.asc\" > /etc/yum.repos.d/mongodb-org-3.6.repo"
fi
#installing yum packages
for pac in ${yumpackages[@]}; do
    if yum info ${pac} | grep "Installed Packages" > /dev/null; then
        echo "${pac} already installed. Nothing to do."
    else
        echo "${pac} not found. Starting to install..."
        sudo yum install -y ${pac}
    fi
done

#enabling RedHad SCL packages
scl_sw=(
    "devtoolset-7"
    "rh-mongodb36"
)
for sw in ${scl_sw[@]}; do
    echo "Checking if ${sw} is already enabled in .bashrc..."
    if grep "source /opt/rh/${sw}/enable" ~/.bashrc > /dev/null; then
        echo "Already setup. Nothing to do."
    else
        echo "Not found. Adding a source command in your .bashrc"
        echo -e "\n#added by the mongoDB install script" >> ~/.bashrc
        echo "source /opt/rh/${sw}/enable" >> ~/.bashrc
    fi
    source /opt/rh/${sw}/enable
done

#install python packages by pip for the DB viewer
#sudo pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --upgrade pip
pip3 install -r requirements.txt

#installing cmake for cmaking CERN ROOT
echo ""
echo "Start checking if cmake software is available..."
cmakedir="3.10"
cmakever="3.10.2"
if cmake --version 2>&1|grep ${cmakever} > /dev/null; then
    echo "Found cmake version of ${cmakever}"
else
    echo "Not found cmake version of ${cmakever}"
    cd /usr/local/src
    sudo wget https://cmake.org/files/v${cmakedir}/cmake-${cmakever}.tar.gz
    sodu tar zxvf cmake-${cmakever}.tar.gz
    rm cmake-${cmakever}.tar.gz 
    cd cmake-${cmakever}/
    sudo ./bootstrap
    sudo make
    sudo make install
    PATH=$PATH:/opt/cmake/bin
    source /etc/bashrc
    cd -
fi

#installing CERN ROOT if it's not setup.
echo ""
echo "Start checking if the ROOT software is available..."
#rootver="root_v6.16.00"
rootver="6.16.00"
rootpac=root_v${rootver}.source.tar.gz
rootloc+=`pwd`"/root/bin/thisroot.sh"
if which root 2>&1| grep "no root in" > /dev/null; then
    if [ -e ./${rootver}/bin ]; then
        echo "ROOT directory was found. Skip downloading it..."
    else
        echo "ROOT not found. Downloading the pre-compiled version of ${rootver}..."
        wget https://root.cern.ch/download/${rootpac} 
        tar zxf ${rootpac}
        rm -f ${rootpac}
        mv root-${rootver} ${rootver}
        mkdir ${rootver}-build && cd ${rootver}-build 
        cmake -DCMAKE_INSTALL_PREFIX=../${rootver}-install -DPYTHON_EXECUTABLE=/usr/bin/python36 ../${rootver}
        cmake --build . -- -j4 
        make install
        cd ../
    fi
else
    echo "ROOT was found. Checking if PyROOT is available"
    pyroot_found="false"
    for ii in 1 2 3 4; do
	if pydoc modules | cut -d " " -f${ii} | grep -x ROOT > /dev/null; then
	    pyroot_found="true"
	fi
    done
    if [ ${pyroot_found} != "true" ]; then
	echo "WARNING: PyROOT is not available."
	echo "Check if PYTHONPATH is properly set or if you compiled ROOT with the PyROOT option enabled."
	echo "You need a manual fix to enable some features in the viewer."
    else
	echo "PyROOT is available in your environment."
    fi
fi

source ${rootver}-build/bin/thisroot.sh

#setting up apache to use DB
if getsebool httpd_can_network_connect | grep off > /dev/null; then
    echo "Boolian:httpd_can_network_connect is turning on."
    sudo /usr/sbin/setsebool -P httpd_can_network_connect 1
else
    echo "httpd_can_network_connect is already on. Nothing to do."
fi

#opening port
echo ""
echo "Opening port for httpd..."
if sudo firewall-cmd --list-all | grep http > /dev/null; then
    echo "http is already allowed by firewall."
else
    sudo firewall-cmd --add-service=http --permanent
    sudo firewall-cmd --reload
fi
echo "Opening port for viewer..."
if sudo firewall-cmd --list-ports --zone=public --permanent | grep 5000/tcp > /dev/null; then
    echo "port=5000/tcp is already allowed by firewall."
else
    sudo firewall-cmd --zone=public --add-port=5000/tcp --permanent
    sudo firewall-cmd --reload
fi

#Preparing database directory
echo ""
echo "Preparing initial data in localdb..."
sudo systemctl stop mongod
if [ -e /var/lib/mongo ]; then
    today=`date +%y%m%d`
    echo "Found /var/lib/mongo. Backing up the contents in /var/lib/mongo-${today}.tar.gz..."
    cd /var/lib
    sudo tar zcf mongo-${today}.tar.gz mongo
    cd - > /dev/null
    sudo rm -rf /var/lib/mongo
else
    sudo mkdir -p /var/lib/mongo
fi
#wget https://cernbox.cern.ch/index.php/s/kNz1xyhZ5bov7Iu
wget --no-check-certificate http://osksn2.hep.sci.osaka-u.ac.jp/~hirose/mongo_example.tar.gz
echo "Unarchiving..."
tar zxf mongo_example.tar.gz
sudo mv ./var/lib/mongo /var/lib
sudo rm -rf ./var
sudo chcon -R -u system_u -t mongod_var_lib_t /var/lib/mongo/
sudo chown -R mongod:mongod /var/lib/mongo

#starting and enabling DB and http servers
services=(
    "mongod"
    "httpd"
)
for svc in ${services[@]}; do
    echo ""
    echo "Setting up ${svc}..."
    if systemctl status ${svc} | grep running > /dev/null; then
        echo "${svc} is already running. Nothing to do."
    else
        echo "Starting ${svc} on your local machine."
        sudo systemctl start ${svc}
    fi
    if systemctl list-unit-files -t service|grep enabled | grep ${svc} > /dev/null; then
        echo "${svc} is already enabled. Nothing to do."
    else
        echo "Enabling ${svc} on your local machine."
        sudo systemctl enable ${svc}
    fi
done

#setting up web-base DB viewer
echo ""
echo "Setting up the web-base DB viewer..."
cd ../../
cp localDB-tools/scripts/apache/config.conf /etc/httpd/conf.d/localDB-tools.conf
echo ""
echo "Preparing a config file based on the skeleton file..."
cp localDB-tools/scripts/yaml/web-conf.yml localDB-tools/viewer/conf.yml
cd localDB-tools/viewer
python36 app.py --config conf.yml &

#Needed to avoid tons of warnings by mongod in /var/log/messages
#sudo sh -c "ausearch -c 'ftdc' --raw | audit2allow -M my-ftdc"
#sudo sh -c "semodule -i my-ftdc.pp"

#setting cache directory
if [ ! -e ${cachedir} ]; then
    sudo mkdir -p ${cachedir}
fi
if [ ! -e ${cachedir}/lib/tmp ]; then
    sudo mkdir -p ${cachedir}/lib/tmp
fi
if [ ! -e ${cachedir}/var/log ]; then
    sudo mkdir -p ${cachedir}/var/log
fi
if [ ! -e ${cachedir}/var/cache ]; then
    sudo mkdir -p ${cachedir}/var/cache/scan
    sudo mkdir -p ${cachedir}/var/log/db
    sudo mkdir -p ${cachedir}/var/cache/dcs
fi
sudo chmod -R 777 ${cachedir}

# create database config
dbcfg=${cachedir}/lib/database.json
echo "{" > ${dbcfg}
echo "    \"hostIp\": \"${ip}\"," >> ${dbcfg}
echo "    \"hostPort\": \"${port}\"," >> ${dbcfg}
echo "    \"dbName\": \"${dbname}\"," >> ${dbcfg}
echo "    \"cachePath\": \"${cachedir}\"," >> ${dbcfg}
echo "    \"stage\": [" >> ${dbcfg}
echo "        \"Bare Module\"," >> ${dbcfg}
echo "        \"Wire Bonded\"," >> ${dbcfg}
echo "        \"Potted\"," >> ${dbcfg}
echo "        \"Final Electrical\"," >> ${dbcfg}
echo "        \"Complete\"," >> ${dbcfg}
echo "        \"Loaded\"," >> ${dbcfg}
echo "        \"Parylene\"," >> ${dbcfg}
echo "        \"Initial Electrical\"," >> ${dbcfg}
echo "        \"Thermal Cycling\"," >> ${dbcfg}
echo "        \"Flex + Bare Module Attachment\"," >> ${dbcfg}
echo "        \"Testing\"" >> ${dbcfg}
echo "    ]," >> ${dbcfg}
echo "    \"environment\": [" >> ${dbcfg}
echo "        \"vddd_voltage\"," >> ${dbcfg}
echo "        \"vddd_current\"," >> ${dbcfg}
echo "        \"vdda_voltage\"," >> ${dbcfg}
echo "        \"vdda_current\"," >> ${dbcfg}
echo "        \"hv_voltage\"," >> ${dbcfg}
echo "        \"hv_current\"," >> ${dbcfg}
echo "        \"temperature\"" >> ${dbcfg}
echo "    ]," >> ${dbcfg}
echo "    \"component\": [" >> ${dbcfg}
echo "        \"Front-end Chip\"," >> ${dbcfg}
echo "        \"Front-end Chips Wafer\"," >> ${dbcfg}
echo "        \"Hybrid\"," >> ${dbcfg}
echo "        \"Module\"," >> ${dbcfg}
echo "        \"Sensor Tile\"," >> ${dbcfg}
echo "        \"Sensor Wafer\"" >> ${dbcfg}
echo "    ]" >> ${dbcfg}
echo "}" >> ${dbcfg}
echo "Create DB Config file: ${dbcfg}"
echo " "

# create site address config 
echo "{" > ${address}
echo "    \"macAddress\": \"${macaddress}\"," >> ${address}
echo "    \"hostname\": \"${HOSTNAME}\"," >> ${address}
echo "    \"institution\": \"${institution}\"" >> ${address}
echo "}" >> ${address}
echo "Create Site Config file: ${address}"
echo " "

sudo chmod -R 722 ${cachedir}/var
sudo chmod -R 744 ${cachedir}/lib/tmp

echo "Create Cache Directory: ${dir}"
echo " "

echo "MongoDB Server IP address: ${ip}, port: ${port}"
echo " "

# clontab

echo ""
echo "Finished installation!!"
echo "Install log can be found in: $LOGFILE"
echo ""
echo "----------------------------------------------------------------"
echo "-- First thing to do..."
echo "----------------------------------------------------------------"
echo "Please log-off and log-in again to activate environmental variables."
echo "Then,,,"
echo "Start the web application by..." | tee README
echo "cd /var/www/localDB-tools/viewer" | tee -a README
echo "python app.py --config conf.yml" | tee -a README
echo "" | tee -a README
echo "Try accessing the DB viewer in your web browser..." | tee -a README
echo "From the DAQ machine: http://localhost:5000/localdb/" | tee -a README
echo "From other machines : http://${ip}/localdb/" | tee -a README
echo "" | tee -a README
echo "To register QA/QC data, check usage at..." | tee -a README
echo "" | tee -a README
echo "https://github.com/jlab-hep/Yarr/wiki/Quick-tutorial" | tee -a README
echo ""
echo "Prepared a README file for the reminder. Enjoy!!"
