#!/bin/bash

##############################################
############### user setting #################
##############################################

# set python version ( set true if you use python3 , or false if you use python2 )
PYTHON3=false
# set IP address
CHANGEIP="'127.0.0.1'"
# set port of mongoDB
CHANGEPORT="27017"

##############################################

# chenge codes 
SETTING="scripts/src/listset.py"

sed -i -e "s/CHANGEIP/${CHANGEIP}/g" ${SETTING}
sed -i -e "s/CHANGEPORT/${CHANGEPORT}/g" ${SETTING}
sed -i -e "s/CHANGEADMIN/${CHANGEADMIN}/g" ${SETTING}
sed -i -e "s/CHANGEPASS/${CHANGEPASS}/g" ${SETTING}

if ${PYTHON3} ; then
  sed -i -e "s/PYTHONV/3/g" ${SETTING}
else
  sed -i -e "s/PYTHONV/2/g" ${SETTING}
fi
