#!/bin/bash
##################################################################
# Start the Viewer Application
# Usage : ./setup_viewer.sh [-i IP address] [-p port]
# Instruction : https://github.com/jlab-hep/Yarr/wiki/Installation
#
# Contacts : Arisa Kubota (kubota.a.af@m.titech.ac.jp)
##################################################################
set -e

viewer_dir=$(cd $(dirname $0); pwd)

# Usage
function usage {
    cat <<EOF

Usage:
    ./setup_viewer.sh [-i ip address] [-p port]

Options:
    - i <IP address>  Local DB server IP address, default: 127.0.0.1
    - p <port>        Local DB server port, default: 27017

EOF
}

ip=`ip -f inet -o addr show| grep -e en -e eth|cut -d\  -f 7 | cut -d/ -f 1`
dbip=127.0.0.1
dbport=27017

while getopts i:p:c:n:d OPT
do
    case ${OPT} in
        i ) dbip=${OPTARG} ;;
        p ) dbport=${OPTARG} ;;
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
    echo "Try again setup_viewer.sh, Exit ..."
    echo " "
    exit
fi

#setting up web-base DB viewer
cp ${viewer_dir}/../scripts/yaml/web-conf.yml conf.yml
sed -i -e "s/DBIPADDRESS/${dbip}/g" conf.yml 
sed -i -e "s/DBPORT/${dbport}/g" conf.yml 

echo ""
echo "Finished setting up of Viewer Application!!"
echo ""
echo "Start Viewer Application by..."
echo ""
echo "python36 app.py --config conf.yml &"
echo ""
echo "Try accessing the DB viewer in your web browser..." 
echo "From the DAQ machine: http://localhost:5000/localdb/" 
echo "From other machines : http://${ip}/localdb/"
echo ""
