#!/bin/bash

##############################################
############### user setting #################
##############################################

# set apache ( set true if you use apache, or false if not )
APACHE=false
# set python version ( set true if you use python3 , or false if you use python2 )
PYTHON3=false
# set IP address
CHANGEIP="'127.0.0.1'"
# set port of mongoDB
CHANGEPORT="27017"

##############################################

# chenge codes 
NAV="./templates/parts/nav.html"
USER="userfunc.py"
SHELL="make_pipinstall.sh"
SETTING="userset.py"
SUMMARY="addsummary.py"

# check ROOT library
if [ -n "${ROOTSYS}" ]; then
  CHANGEROOTLIB="'`echo ${ROOTSYS}`/lib'"
else
  CHANGEROOTLIB=""
fi

sed -i -e "s/CHANGEIP/${CHANGEIP}/g" ${SETTING}
sed -i -e "s/CHANGEPORT/${CHANGEPORT}/g" ${SETTING}
sed -i -e "s/CHANGEADMIN/${CHANGEADMIN}/g" ${SETTING}
sed -i -e "s/CHANGEPASS/${CHANGEPASS}/g" ${SETTING}

if ${PYTHON3} ; then
  sed -i -e "/python2/d" ${USER}
  sed -i -e "/python2/d" ${SUMMARY}
  sed -i -e "s/PIPPATH/pip3/g" ${SHELL}
else
  sed -i -e "/python3/d" ${USER}
  sed -i -e "/python3/d" ${SUMMARY}
  sed -i -e "s/PIPPATH/pip/g" ${SHELL}
fi

if $APACHE ; then
  if [ -n "${ROOTLIB}" ]; then
    sed -i -e "s!ROOTLIB!${ROOTLIB}!g" ${SETTING}
  else
    sed -i -e "/ROOTLIB/d" ${SETTING}
  fi
  sed -i -e "s/YARR/yarrdb/g" ${NAV} 
else
  sed -i -e "s/YARR//g" ${NAV}
  sed -i -e "/ROOTLIB/d" ${SETTING}
fi
