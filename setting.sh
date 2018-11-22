#!/bin/bash

##############################################
############### user setting #################
##############################################

# set apache
APACHE=true
# set python version ( set true if you use python3 )
PYTHON3=true
# set IP address
IPADDRESS="'127.0.0.1'"
# set port of mongoDB
PORT="27017"
# set username and password of admin page
ADMIN="'admin'"
PASS="'password'"

##############################################

# chenge codes 
APP="app.py"
FEI4="fei4.py"
NAV="./templates/parts/nav.html"
USER="userfunc.py"
ROOT="root.py"
SHELL="make_pipinstall.sh"

# check ROOT library
if [ -n "${ROOTSYS}" ]; then
  ROOTLIB="'`echo ${ROOTSYS}`/lib'"
else
  ROOTLIB=""
fi

sed -i -e "s/IPADDRESS/${IPADDRESS}/g" ${APP}
sed -i -e "s/PORT/${PORT}/g" ${APP}
sed -i -e "s/PORT/${PORT}/g" ${FEI4}
sed -i -e "s/PORT/${PORT}/g" ${USER}
sed -i -e "s/ADMIN/${ADMIN}/g" ${APP}
sed -i -e "s/PASS/${PASS}/g" ${APP}

if ${PYTHON3} ; then
  sed -i -e "/python2/d" ${USER}
  sed -i -e "s/PIPPATH/pip3/g" ${SHELL}
else
  sed -i -e "/python3/d" ${USER}
  sed -i -e "s/PIPPATH/pip/g" ${SHELL}
fi

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
