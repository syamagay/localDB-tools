#!/bin/bash
#################################
# Contacts: Arisa Kubota
# Email: arisa.kubota at cern.ch
# Date: July 2019
# Project: Local Database for Yarr
# Description: Login Database 
# Usage: ./db_server_install.sh
################################

set -e

# Usage
function usage {
    cat <<EOF

Usage:
    ./db_server_install.sh 

EOF
}

# Start
if [ `echo ${0} | grep bash` ]; then
    echo -e "[LDB] DO NOT 'source'"
    usage
    return
fi
shell_dir=$(cd $(dirname ${BASH_SOURCE}); pwd)
ip=`hostname -i`
today=`date +%y%m%d`
# packages list to be required
yumpackages=$(cat ${shell_dir}/requirements-yum.txt)
pippackages=$(cat ${shell_dir}/requirements-pip.txt)
LOGDIR="${shell_dir}/instlog"
if [ ! -d ${LOGDIR} ]; then
    mkdir ${LOGDIR}
fi
port=true
initialize=true
services=(
    "mongod"
    "httpd"
)
while getopts hpi OPT
do
    case ${OPT} in
        h ) usage ;;
        p ) port=false ;;
        i ) initialize=false ;; 
        * ) usage
            exit ;;
    esac
done

# Confirmation
echo -e "[LDB] This script performs ..."
echo -e ""
echo -e "[LDB]  - Install yum packages: '${shell_dir}/requirements-yum.txt'"
echo -e "[LDB]         $ sudo yum install \$(cat ${shell_dir}/requirements-yum.txt)"
echo -e "[LDB]  - Install pip modules: '${shell_dir}/requirements-pip.txt'"
echo -e "[LDB]         $ sudo pip3 install \$(cat ${shell_dir}/requirements-pip.txt)"
echo -e "[LDB]  - Start Apache Service:"
echo -e "[LDB]         $ sudo /usr/sbin/setsebool -P httpd_can_network_connect 1"
if "${port}"; then
    echo -e "[LDB]         $ sudo firewall-cmd --add-service=http --permanent"
    echo -e "[LDB]         $ sudo firewall-cmd --reload"
fi
echo -e "[LDB]         $ sudo systemctl start httpd"
echo -e "[LDB]  - Initialize Local DB Server:"
echo -e "[LDB]         IP address: ${ip}"
echo -e "[LDB]         port      : 27017"
if "${initialize}"; then
    echo -e "[LDB]         Backup data in Local DB ('/var/lib/mongo') into '/var/lib/mongo-${today}.tar.gz'"
    echo -e "[LDB]         Reset data in Local DB"
fi
echo -e "[LDB]  - Start MongoDB Service:"
if "${port}"; then
    echo -e "[LDB]         $ sudo firewall-cmd --zone=public --add-port=27017/tcp --permanent" 
    echo -e "[LDB]         $ sudo firewall-cmd --reload"
fi
echo -e "[LDB]         $ sudo systemctl start mongod"
echo -e "[LDB]         $ sudo systemctl enable mongod"
echo -e ""
echo -e "[LDB] Continue? [y/n]"
while [ -z ${answer} ]; 
do
    read -p "> " answer
done
echo -e ""
if [ ${answer} != "y" ]; then
    echo -e "[LDB] Exit..."
    echo -e "[LDB] You can install packages without opening port by:"
    echo -e "[LDB]     $ ./db_server_install.sh -p"
    echo -e "[LDB] You can install packages without initialize Local DB Server by:"
    echo -e "[LDB]     $ ./db_server_install.sh -i"
    echo -e ""
    echo -e "[LDB] If you want to setup them manually, the page 'https://github.com/jlab-hep/Yarr/wiki/Installation' should be helpful!"
    echo -e ""
    exit
fi
sudo echo -e "[LDB] OK!"

# Set log file
LOGFILE="${LOGDIR}/`date "+%Y%m%d_%H%M%S"`"
exec 2> >(awk '{print strftime("[%Y-%m-%d %H:%M:%S] "),$0 } { fflush() } ' | tee ${LOGFILE}) 1>&2
trap 'echo -e ""; echo -e "[LDB] Installation stopped by SIGINT!!"; echo -e "[LDB] You may be in unknown state."; echo -e "[LDB] Check ${LOGFILE} for debugging in case of a problem of re-executing this script."; exit 1' 2

# Check what is missing for Local DB
echo -e "[LDB] Looking for missing things for Local DB and its Tools..."
echo -e "[LDB] -------------------------------------------------------------"
if [ ! -e "/etc/yum.repos.d/mongodb-org-3.6.repo" ]; then
    echo -e "[LDB] Add: mongodb-org-3.6 repository in /etc/yum.repos.d/mongodb-org-3.6.repo."
fi
for pac in ${yumpackages[@]}; do
    if ! yum list installed 2>&1 | grep ${pac} > /dev/null; then
	echo -e "[LDB] yum install: ${pac}"
    fi
done
for pac in ${pippackages[@]}; do
    if ! pip3 list 2>&1 | grep ${pac} 2>&1 > /dev/null; then
       echo -e "[LDB] pip3 install: ${pac}"
    fi
done
if ! getsebool httpd_can_network_connect | grep off > /dev/null; then
    echo -e "[LDB] SELinux: turning on httpd_can_network_connect"
fi
if "${port}"; then
    if ! sudo firewall-cmd --list-all | grep http > /dev/null; then
        echo -e "[LDB] Firewall: opening port=80/tcp for appache."
    fi
    if ! sudo firewall-cmd --list-ports --zone=public --permanent | grep 27017/tcp > /dev/null; then
        echo -e "[LDB] Firewall: opening port=27017/tcp for viewer application."
    fi
fi
for svc in ${services[@]}; do
    if ! systemctl status ${svc} 2>&1 | grep running > /dev/null; then
        echo -e "[LDB] Start: ${svc}"
    fi
    if ! systemctl list-unit-files -t service|grep enabled 2>&1 | grep ${svc} > /dev/null; then
        echo -e "[LDB] Enable: ${svc}"
    fi
done
echo -e "[LDB] ----------------------------------------------------"

# Install necessary packages if not yet installed
echo -e "[LDB] Start installing necessary packages..."
# Add mongoDB repository and installing mongoDB
if [ -e "/etc/yum.repos.d/mongodb-org-3.6.repo" ]; then
    echo -e "[LDB] mongodb-org-3.6 repository already installed. Nothing to do."
else
    echo -e "[LDB] Adding mongodb-org-3.6 repository."
    sudo sh -c "echo \"[mongodb-org-3.6]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/7Server/mongodb-org/3.6/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-3.6.asc\" > /etc/yum.repos.d/mongodb-org-3.6.repo"
fi
# Install yum packages
for pac in ${yumpackages[@]}; do
    if yum list installed 2>&1 | grep ${pac} > /dev/null; then
        echo -e "[LDB] ${pac} already installed. Nothing to do."
    else
        echo -e "[LDB] ${pac} not found. Starting to install..."
        sudo yum install -y ${pac}
    fi
done

# Enable RedHad SCL packages
source /opt/rh/devtoolset-7/enable

# Install python packages by pip for the DB viewer
for pac in ${pippackages[@]}; do
    if pip3 list 2>&1 | grep ${pac} 2>&1 > /dev/null; then
        echo "${pac} already installed. Nothing to do."
    else
        echo "${pac} not found. Starting to install..."
        sudo pip3 install ${pac}
    fi
done
/usr/bin/env python3 ${shell_dir}/check_python_modules.py
if [ $? = 1 ]; then
    echo -e "[LDB] Failed, exit..."
    exit
fi

# Setup apache to use DB
if getsebool httpd_can_network_connect | grep off > /dev/null; then
    echo -e "[LDB] Boolian:httpd_can_network_connect is turning on."
    sudo /usr/sbin/setsebool -P httpd_can_network_connect 1
else
    echo -e "[LDB] httpd_can_network_connect is already on. Nothing to do."
fi

# Setup Viewer Application
echo -e ""
echo -e "[LDB] Setting up the Viewer Application..."
echo -e "[LDB] Create config file in /etc/httpd/conf.d/localDB-tools.conf"
sudo cp ${shell_dir}/../scripts/apache/config.conf /etc/httpd/conf.d/localDB-tools.conf

# Open port
if "${port}"; then
    echo -e ""
    echo -e "[LDB] Opening port for httpd..."
    if sudo firewall-cmd --list-all | grep http > /dev/null; then
        echo -e "[LDB] http is already allowed by firewall."
    else
        sudo firewall-cmd --add-service=http --permanent
        sudo firewall-cmd --reload
    fi
fi

# Prepare database directory
if "${initialize}"; then
    echo -e ""
    echo -e "[LDB] Preparing initial data in localdb..."
    sudo systemctl stop mongod
    if [ -e /var/lib/mongo ]; then
        echo -e "[LDB] Found /var/lib/mongo. Backing up the contents in /var/lib/mongo-${today}.tar.gz..."
        cd /var/lib
        sudo tar zcf mongo-${today}.tar.gz mongo
        cd - > /dev/null
        sudo rm -rf /var/lib/mongo
    fi
    sudo mkdir -p /var/lib/mongo
    
    sudo chcon -R -u system_u -t mongod_var_lib_t /var/lib/mongo/
    sudo chown -R mongod:mongod /var/lib/mongo
fi

# Modify mongod.conf
if ! cat /etc/mongod.conf | grep "bindIp: 127.0.0.1,${ip}" > /dev/null; then
    sudo sed -i -e "s/bindIp: 127.0.0.1/bindIp: 127.0.0.1,${ip}/g" /etc/mongod.conf
fi

# Open port
if "${port}"; then
    echo -e ""
    echo -e "[LDB] Opening port for Local DB access"
    if sudo firewall-cmd --list-ports --zone=public --permanent | grep 27017/tcp > /dev/null; then
        echo -e "[LDB] port=27017/tcp is already allowed by firewall."
    else
        sudo firewall-cmd --zone=public --add-port=27017/tcp --permanent
        sudo firewall-cmd --reload
    fi
fi

# Start and enable DB and http servers
services=(
    "mongod"
    "httpd"
)
for svc in ${services[@]}; do
    echo -e ""
    echo -e "[LDB] Setting up ${svc}..."
    if systemctl status ${svc} | grep running > /dev/null; then
        echo -e "[LDB] ${svc} is already running. Nothing to do."
    else
        echo -e "[LDB] Starting ${svc} on your local machine."
        sudo systemctl start ${svc}
    fi
    if systemctl list-unit-files -t service|grep enabled | grep ${svc} > /dev/null; then
        echo -e "[LDB] ${svc} is already enabled. Nothing to do."
    else
        echo -e "[LDB] Enabling ${svc} on your local machine."
        sudo systemctl enable ${svc}
    fi
done

mongo --host ${ip} --port 27017 <<EOF

use localdb
db.createCollection('childParentRelation');
db.createCollection('component');
db.createCollection('componentTestRun');
db.createCollection('config');
db.createCollection('fs.chunks');
db.createCollection('fs.files');
db.createCollection('institution');
db.createCollection('testRun');
db.createCollection('user');
db.createCollection('environment');
db.createCollection('comment');
db.createCollection('tag');

EOF

echo -e "[LDB] Done."
echo -e ""

readme=${shell_dir}/README

echo -e ""
echo -e "Finished installation!!"
echo -e "Install log can be found in: ${LOGFILE}"
echo -e ""
echo -e "# Local DB Installation for DB Server" | tee ${readme} 
echo -e "" | tee -a ${readme}
echo -e "## 1. Setup Viewer Application" | tee -a ${readme}
echo -e "\`\`\`" | tee -a ${readme}
echo -e "cd localDB-tools/viewer" | tee -a ${readme}
echo -e "./setup_viewer.sh" | tee -a ${readme}
echo -e "python3 app.py --config conf.yml" | tee -a ${readme}
echo -e "\`\`\`" | tee -a ${readme}
echo -e "" | tee -a ${readme}
echo -e "## 2. Access Viewer Application" | tee -a ${readme}
echo -e "- From the DB machine: http://localhost:5000/localdb/" | tee -a ${readme}
echo -e "- From other machines : http://${ip}/localdb/" | tee -a ${readme}
echo -e "" | tee -a ${readme}
echo -e "## 3.Check more detail" | tee -a ${readme}
echo -e "- https://github.com/jlab-hep/Yarr/wiki" | tee -a ${readme}
echo -e "This description is saved as ${readme}. Enjoy!!"
