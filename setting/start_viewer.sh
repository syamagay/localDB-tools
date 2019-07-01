#!/bin/bash
##################################################################
# Start the Viewer Application
# Usage : ./start_viewer.sh [-i IP address] [-p port]
# Instruction : https://github.com/jlab-hep/Yarr/wiki/Installation
#
# Contacts : Arisa Kubota (kubota.a.af@m.titech.ac.jp)
##################################################################
set -e

# Usage
function usage {
    cat <<EOF

Usage:
    ./start_viewer.sh [-i ip address] [-p port]

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
    echo "Try again start_viewer.sh, Exit ..."
    echo " "
    exit
fi

#setting up web-base DB viewer
echo ""
echo "Setting up the web-base DB viewer..."
cd ../
echo "Preparing a config file based on the skeleton file..."
cp scripts/yaml/web-conf.yml viewer/conf.yml
cd viewer
sed -i -e "s/DBIPADDRESS/${dbip}/g" conf.yml 
sed -i -e "s/DBPORT/${dbport}/g" conf.yml 
sed -i -e "s/IPADDRESS/${ip}/g" conf.yml
python36 app.py --config conf.yml &

echo ""
echo "Finished setting up of Viewer Application!!"
echo ""
echo "Try accessing the DB viewer in your web browser..." 
echo "From the DAQ machine: http://localhost:5000/localdb/" 
echo "From other machines : http://${ip}/localdb/"
echo ""
