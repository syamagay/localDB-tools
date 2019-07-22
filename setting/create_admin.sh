#!/bin/bash
##################################################################
# Create user for mongodb
# Usage : ./setup_viewer.sh [-i IP address] [-p port]
# Instruction : https://github.com/jlab-hep/Yarr/wiki/Installation
#
# Contacts : Hiroki Okuyama (okuyama.h.ag@m.titech.ac.jp)
##################################################################
set -e

viewer_dir=$(cd $(dirname $0); pwd)

# Usage
function usage {
    cat <<EOF

Usage:
    ./create_user.sh [-i ip address] [-p port]

Options:
    - i <IP address>  Local DB server IP address, default: 127.0.0.1
    - p <port>        Local DB server port, default: 27017
    - n               

EOF
}

ip=`ip -f inet -o addr show| grep -e en -e eth|cut -d\  -f 7 | cut -d/ -f 1`
dbip=127.0.0.1
dbport=27017
auth=1

while getopts i:p:n OPT
do
    case ${OPT} in
        i ) dbip=${OPTARG} ;;
        p ) dbport=${OPTARG} ;;
        n ) auth=0 ;;
        * ) usage
            exit ;;
    esac
done

echo "Local DB Server IP address: ${dbip}"
echo "Local DB Server port: ${dbport}"
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
    echo "Try again create_admin.sh, Exit ..."
    echo " "
    exit
fi

sudo systemctl start mongod.service
sudo systemctl enable mongod.service

read -p "Admin's name: " user
echo ""
read -sp "Admin's Password: " password
echo ""
read -p "Input user : " USER
echo ""
#read -sp "Secret string: " string
#echo ""



mongo --host ${dbip} --port ${dbport} <<EOF

use admin
db.createUser({user: '${user}', pwd: '${password}', roles: [{role: 'root', db: 'admin'}]})  

use localdb
db.createUser({user: '${user}', pwd: '${password}', roles: [{role: 'readWrite', db: 'localdb'}]}) 

use localdb_user
db.createUser({user: '${user}', pwd: '${password}', roles: [{role: 'readWrite', db: 'localdb_user'}]}) 

EOF

if  [ ${auth} -eq 0 ]; then
    cp ${viewer_dir}/../scripts/yaml/web-conf.yml ${viewer_dir}/../viewer/conf.yml
    sed -i -e "s/DBIPADDRESS/${dbip}/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/DBPORT/${dbport}/g" ${viewer_dir}/../viewer/conf.yml
    sed -i -e "s/#username/username/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/#password/password/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/localdbuser/${user}/" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/localdbpass/${password}/" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/userdbuser/${user}/" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/userdbpass/${password}/" ${viewer_dir}/../viewer/conf.yml 
    chmod 400 ${viewer_dir}/../viewer/conf.yml 
    chown ${USER}:${USER} ${viewer_dir}/../viewer/conf.yml
    
    echo ""
    echo "Finished the setting of localdb with certification!!"
    echo ""
    echo "For checking the setting of Local DB: /etc/mongod.conf "
    echo ""
    echo "For checking of the Viewer Application: ${viewer_dir}/conf.yml"
    echo ""

elif [ ${auth} -eq 1 ]; then
    sudo systemctl stop mongod.service
    sed -i -e "s/#security/security/" /etc/mongod.conf 
    sed -i -e "s/#  authorization: enabled/  authorization: enabled/" /etc/mongod.conf
    sudo systemctl restart mongod.service
    echo ""
    echo "Protect your mongodb!!"
    echo ""
    cp ${viewer_dir}/../scripts/yaml/web-conf.yml ${viewer_dir}/../viewer/conf.yml
    sed -i -e "s/DBIPADDRESS/${dbip}/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/DBPORT/${dbport}/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/#username/username/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/#password/password/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/localdbuser/${user}/" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/localdbpass/${password}/" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/userdbuser/${user}/" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/userdbpass/${password}/" ${viewer_dir}/../viewer/conf.yml 
    chmod 400 ${viewer_dir}/../viewer/conf.yml 
    chown ${USER}:${USER} ${viewer_dir}/../viewer/conf.yml
    
    echo ""
    echo "Finished the setting of localdb with certification!!"
    echo ""
    echo " For checking the setting of Local DB: /etc/mongod.conf "
    echo ""
    echo " For checking of the Viewer Application: `pwd`/conf.yml"
    echo ""
fi


