#!/bin/bash

# set IP address
IPADDRESS="'192.168.1.43'"
# set port of mongoDB
PORT="28000"
# set username and password of admin page
ADMIN="admin"
PASS="password"

# check ROOT library
if [ -n "${ROOTSYS}" ]; then
    ROOTLIB="'`echo ${ROOTSYS}`/lib'"
else
    ROOTLIB=""
fi

# chenge codes in app.py and userfunc.py
APP="apptest.py"
USER="userfunctest.py"
ROOT="root.py"

sed -i -e "s/IPADDRESS/${IPADDRESS}/g" ${APP}
sed -i -e "s/PORT/${PORT}/g" ${APP}
sed -i -e "s/ADMIN/${ADMIN}/g" ${APP}
sed -i -e "s/PASS/${PASS}/g" ${APP}

if [ -n "${ROOTLIB}" ]; then
    sed -i -e "s!ROOTLIB!${ROOTLIB}!g" ${APP}
else
    sed -i -e "/ROOTLIB/d" ${APP}
fi
