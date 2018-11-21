#!/bin/bash

# set apache
APACHE=false

# set IP address
IPADDRESS="'127.0.0.1'"
# set port of mongoDB
PORT="27017"
# set username and password of admin page
ADMIN="'admin'"
PASS="'password'"

# check ROOT library
if [ -n "${ROOTSYS}" ]; then
  ROOTLIB="'`echo ${ROOTSYS}`/lib'"
else
  ROOTLIB=""
fi

# chenge codes in app.py and userfunc.py
APP="app.py"
NAV="./templates/parts/nav.html"
USER="userfunctest.py"
ROOT="root.py"

sed -i -e "s/IPADDRESS/${IPADDRESS}/g" ${APP}
sed -i -e "s/PORT/${PORT}/g" ${APP}
sed -i -e "s/ADMIN/${ADMIN}/g" ${APP}
sed -i -e "s/PASS/${PASS}/g" ${APP}

if $APACHE ; then
  if [ -n "${ROOTLIB}" ]; then
    sed -i -e "s!ROOTLIB!${ROOTLIB}!g" ${APP}
    sed -i -e "s!ROOTLIB!${ROOTLIB}!g" ${ROOT}
  else
    sed -i -e "/ROOTLIB/d" ${APP}
    sed -i -e "/ROOTLIB/d" ${ROOT}
  fi
  sed -i -e "s/YARR/yarr/g" ${NAV} 
else
  sed -i -e "s/YARR//g" ${NAV}
  sed -i -e "/ROOTLIB/d" ${APP}
  sed -i -e "/ROOTLIB/d" ${ROOT}
fi
