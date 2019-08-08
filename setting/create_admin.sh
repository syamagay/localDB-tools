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
    - h               Show this page
    - i <IP address>  Local DB server IP address, default: 127.0.0.1
    - p <port>        Local DB server port, default: 27017
    - n               If you don't want to add security in mongodb, please add this option. 

EOF
}

ip=`ip -f inet -o addr show| grep -e en -e eth|cut -d\  -f 7 | cut -d/ -f 1`
dbip=127.0.0.1
dbport=27017
auth=1

while getopts i:p:nh OPT
do
    case ${OPT} in
        i ) dbip=${OPTARG} ;;
        p ) dbport=${OPTARG} ;;
        n ) auth=0 ;;
        h ) usage
            exit ;;
        * ) usage
            exit ;;
    esac
done

echo "Are you a sudo user? [y/n]"
read -p "> " ans
while [ -z ${ans} ]; 
do
    echo "Are you a sudu user? [y/n]"
    read -p "> " ans
done
echo " "

if [ ${ans} != "y" ]; then
    echo "Sorry, sudo user only can run this program. Exit ..."
    echo " "
    exit
fi

read -p "Input your account name: " USER
sudo echo ""

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

read -p "Register localDB admin's name: " user
echo ""
read -sp "Register localDB admin's Password: " password
echo ""
#read -sp "Secret string: " string
#echo ""

password_hash=`echo -n ${password}|md5sum|sed -e "s/-//"|sed -e "s/ //g"`


mongo --host ${dbip} --port ${dbport} <<EOF

use admin
db.createUser({user: '${user}', pwd: '${password}', roles: [{role: 'root', db: 'admin'}]})  

use localdb
db.createUser({user: '${user}', pwd: '${password_hash}', roles: [{role: 'readWrite', db: 'localdb'},{role: 'readWrite', db: 'localdb_user'}]}) 

EOF

if  [ ${auth} -eq 0 ]; then

    echo ${user} > /home/${USER}/.localdbkey
    echo -n ${password_hash} >> /home/${USER}/.localdbkey
    chmod 700 /home/${USER}/
    chmod 700 /home/${USER}/.localdbkey
    chown ${USER}:${USER} /home/${USER}/.localdbkey

    cp ${viewer_dir}/../scripts/yaml/web-conf.yml ${viewer_dir}/../viewer/conf.yml
    sed -i -e "s/DBIPADDRESS/${dbip}/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/DBPORT/${dbport}/g" ${viewer_dir}/../viewer/conf.yml
    sed -i -e "s/#localdbkeypass/localdbkeypass/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s!localdbkeypass!/home/${USER}/.localdbkey!" ${viewer_dir}/../viewer/conf.yml 
    chmod 700 ${viewer_dir}/../viewer/conf.yml 
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
    sudo sed -i -e "s/#security/security/" /etc/mongod.conf 
    sudo sed -i -e "s/#  authorization: enabled/  authorization: enabled/" /etc/mongod.conf
    sudo systemctl restart mongod.service
    echo ""
    echo "Protect your mongodb!!"
    echo ""

    echo ${user} > /home/${USER}/.localdbkey
    echo ${password_hash} >> /home/${USER}/.localdbkey
    chmod 700 /home/${USER}/
    chmod 700 /home/${USER}/.localdbkey
    chown ${USER}:${USER} /home/${USER}/.localdbkey

    cp ${viewer_dir}/../scripts/yaml/web-conf.yml ${viewer_dir}/../viewer/conf.yml
    sed -i -e "s/DBIPADDRESS/${dbip}/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/DBPORT/${dbport}/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s/#localdbkey/localdbkey/g" ${viewer_dir}/../viewer/conf.yml 
    sed -i -e "s!localdbkeypass!/home/${USER}/.localdbkey!" ${viewer_dir}/../viewer/conf.yml 
    chmod 700 ${viewer_dir}/../viewer/conf.yml 
    chown ${USER}:${USER} ${viewer_dir}/../viewer/conf.yml
   
    echo ""
    echo "Finished the setting of localdb with certification!!"
    echo ""
    echo " For checking the setting of Local DB: /etc/mongod.conf "
    echo ""
    echo " For checking of the Viewer Application: `pwd`/conf.yml"
    echo ""
fi


