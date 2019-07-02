#!/bin/bash
##################################################################
# Installation for setting up Local DB Server
# Usage : ./db_server_install.sh
# Instruction : https://github.com/jlab-hep/Yarr/wiki/Installation
#
# Contacts : Arisa Kubota (kubota.a.af@m.titech.ac.jp)
##################################################################
set -e

# Usage
function usage {
    cat <<EOF

Usage:
    ./db_server_install.sh 

EOF
}

ip=`ip -f inet -o addr show| grep -e en -e eth|cut -d\  -f 7 | cut -d/ -f 1`

echo " "
echo "Local DB Server IP address: ${ip}"
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
    echo "Try again db_server_install.sh, Exit ..."
    echo " "
    exit
fi

setting_dir=`pwd`

### start installation

LOGFILE="instlog_"`date "+%Y%m%d_%H%M%S"`
exec 2> >(awk '{print strftime("[%Y-%m-%d %H:%M:%S] "),$0 } { fflush() } ' | tee $LOGFILE) 1>&2

trap 'echo ""; echo "Installation stopped by SIGINT!!"; echo "You may be in unknown state."; echo "Check ${LOGFILE} for debugging in case of a problem of re-executing this script."; exit 1' 2

#packages list to be required
yumpackages=(
    "epel-release.noarch"
    "centos-release-scl.noarch"
    "bc.x86_64"
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
)
for sw in ${scl_sw[@]}; do
    source /opt/rh/${sw}/enable
done

#install python packages by pip for the DB viewer
cd ${setting_dir}
sudo pip3 install -r requirements-pip.txt

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
    cd ${setting_dir} > /dev/null
    sudo rm -rf /var/lib/mongo
fi
sudo mkdir -p /var/lib/mongo

cd ${setting_dir}
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

## Needed to avoid tons of warnings by mongod in /var/log/messages
#sudo ausearch -c 'ftdc' --raw | audit2allow -M my-ftdc
#sudo semodule -i my-ftdc.pp

#setting up web-base DB viewer
echo ""
echo "Setting up the web-base DB viewer..."
cd ${setting_dir}
cd ../
cp ./scripts/apache/config.conf /etc/httpd/conf.d/localDB-tools.conf

echo ""
echo "Finished installation!!"
echo "Install log can be found in: $LOGFILE"
echo ""
echo "----------------------------------------------------------------"
echo "-- First thing to do..."
echo "----------------------------------------------------------------"
echo "Start the web application by..." | tee README
echo "cd /var/www/localDB-tools/viewer" | tee -a README
echo "python36 app.py --config conf.yml" | tee -a README
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
echo ""
