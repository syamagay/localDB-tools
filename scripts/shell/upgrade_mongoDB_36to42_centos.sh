#!/bin/bash
##################################
## Author1: Eunchong Kim (eunchong.kim at cern.ch)
## Copyright: Copyright 2019, localDB tools
## Date: Aug. 2019
## Project: Local Database Tools
## Description: Update mongoDB 3.6 to 4.0 for centos
##################################


#----------------------
# Stop mongoDB daemon
#----------------------
sudo systemctl stop mongod.service


#----------------------
# 3.6 to 4.0
#----------------------
# Update mongoDB bin to 4.0
echo -e \
    "[mongodb-org-4.0]\n" \
    "name=MongoDB Repository\n" \
    "baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/4.0/x86_64/\n" \
    "gpgcheck=1\n" \
    "enabled=1\n" \
    "gpgkey=https://www.mongodb.org/static/pgp/server-4.0.asc" \
    | sudo tee /etc/yum.repos.d/mongodb-org-4.2.repo
sudo yum update -y

# Open mongoDB temporary
sudo mongod &
sleep 15

# Upgrade mongoDB data to 4.0
mongo --eval "db.adminCommand( { setFeatureCompatibilityVersion: "4.0" } )"

# Shutdown temporary mongoDB
mongod --shutdown


#----------------------
# 4.0 to 4.2
#----------------------
# Update mongoDB bin to 4.2
echo -e \
    "[mongodb-org-4.2]" \
    "name=MongoDB Repository" \
    "baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/4.2/x86_64/" \
    "gpgcheck=1" \
    "enabled=1" \
    "gpgkey=https://www.mongodb.org/static/pgp/server-4.2.asc" \
    | sudo tee /etc/yum.repos.d/mongodb-org-4.0.repo
sudo yum update -y

# Open mongoDB temporary
sudo mongod &
sleep 15

# Upgrade mongoDB data to 4.0
mongo --eval "db.adminCommand( { setFeatureCompatibilityVersion: "4.2" } )"

# Shutdown temporary mongoDB
mongod --shutdown


#----------------------
# Clean
#----------------------
sudo rm -f /etc/yum.repos.d/mongodb-org-3.6.repo /etc/yum.repos.d/mongodb-org-4.0.repo


#----------------------
# Start mongoDB daemon
#----------------------
sudo systemctl start mongod.service
