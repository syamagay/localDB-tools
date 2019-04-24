#!/bin/bash
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Setup sync tool for local use
#################################

ITSNAME="[LocalDB Tool Setup Sync Tool]"

# Start
echo -e "$ITSNAME Welcome!"

# Check python modules
echo -e "$ITSNAME Check python modules..."
/usr/bin/env python3 ../scripts/check_python_modules.py || return

# Copy bin
cp -r src/usr/bin .
chmod +x bin/*

# Copy yml configure
if [ ! -f my_configure.yml ]; then
    cp src/etc/localdbtools/default.yml my_configure.yml
fi
$EDITOR my_configure.yml

# Enable bash completion
source src/usr/share/bash-completion/completions/localdbtool-sync
complete -F _localdbtool_sync ./bin/localdbtool-sync.py

echo -e "$ITSNAME Finish!"

echo -e "$ITSNAME Usage)"
echo -e "\t./bin/localdbtool-sync.py --config my_default.yml"
echo -e "\tor"
echo -e "\t./bin/localdbtool-sync.py --host <local server host> --port <local server port> --mhost <master server hsot> --mport<master server port> ..."
