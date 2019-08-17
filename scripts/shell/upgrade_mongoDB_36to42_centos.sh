#!/bin/bash
##################################
## Author1: Eunchong Kim (eunchong.kim at cern.ch)
## Copyright: Copyright 2019, localDB tools
## Date: Aug. 2019
## Project: Local Database Tools
## Description: Update mongoDB 3.6 to 4.0 for centos
##################################

# Variables for SLACK app
header="Content-type: application/json"
url="https://hooks.slack.com/services/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"

message_type="ERROR"
message="ARCHIVE FAILED!"
TIME="`date +"%Y-%m-%d %H:%M:%S"`"
data="{\"text\":\"
        [$message_type] $message from $HOSTNAME
        TIME: $TIME
    \"}"

data_path=/var/lib/mongo
backup_path=./mongoDB-backup

port=27777

#----------------------
# Set expands variables and prints a little + sign before the line
#----------------------
set -x


#----------------------
# Stop mongoDB daemon
#----------------------
sudo systemctl stop mongod.service


#----------------------
# Backup mongoDB data directory
#----------------------
mkdir -p $backup_path
sudo tar zcvf ${backup_path}/mongo_`date +%y%m%d_%H%M%S`.tar.gz ${data_path} \
    && (echo $? && echo -e "$TIME, succeed") \
    || (echo $? && curl -X POST -H "$header" --data "$data" $url \
        && echo -e "$RED $message_type $NC $message" \
        && echo -e "$TIME, $message_type $message" \
        && exit 1
    )


#----------------------
# 3.6 to 4.0
#----------------------
# Update mongoDB bin to 4.0
echo -e \
"[mongodb-org-4.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/\$releasever/mongodb-org/4.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-4.0.asc" \
    | sudo tee /etc/yum.repos.d/mongodb-org-4.0.repo
sudo yum update -y

# Open mongoDB temporary
sudo mongod --port ${port} --dbpath ${data_path} &
sleep 15

# Upgrade mongoDB data to 4.0
mongo --port ${port} --eval "db.adminCommand( { setFeatureCompatibilityVersion: '4.0' } )"

# Shutdown temporary mongoDB
mongod --port ${port} --dbpath ${data_path} --shutdown


#----------------------
# 4.0 to 4.2
#----------------------
# Update mongoDB bin to 4.2
echo -e \
"[mongodb-org-4.2]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/\$releasever/mongodb-org/4.2/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-4.2.asc" \
    | sudo tee /etc/yum.repos.d/mongodb-org-4.2.repo
sudo yum update -y

# Open mongoDB temporary
sudo mongod --port ${port} --dbpath ${data_path} &
sleep 15

# Upgrade mongoDB data to 4.0
mongo --port ${port} --eval "db.adminCommand( { setFeatureCompatibilityVersion: '4.2' } )"

# Shutdown temporary mongoDB
mongod --port ${port} --dbpath ${data_path} --shutdown


#----------------------
# Clean
#----------------------
sudo rm -f /etc/yum.repos.d/mongodb-org-3.6.repo /etc/yum.repos.d/mongodb-org-4.0.repo


#----------------------
# Change permission, context
#----------------------
sudo chcon -R -u system_u -t mongod_var_lib_t /var/lib/mongo/
sudo chown -R mongod:mongod /var/lib/mongo


#----------------------
# Start mongoDB daemon
#----------------------
sudo systemctl start mongod.service
