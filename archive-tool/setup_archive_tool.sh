#!/bin/bash
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Setup archive tool for local use
#################################

ITSNAME="[LocalDB Tool Setup Archive Tool]"

# Start
echo -e "$ITSNAME Welcome!"

# Copy bin
cp -r src/bin .
chmod +x bin/*

# Copy yml configure
if [ ! -f my_archive_configure.yml ]; then
    cp src/etc/localdbtools/archive.yml my_archive_configure.yml
fi
$EDITOR my_archive_configure.yml

# Enable bash completion
source src/share/bash-completion/completions/localdbtool-archive
complete -F _localdbtool_archive ./bin/localdbtool-archive.sh

echo -e "$ITSNAME Finish!"

echo -e "$ITSNAME Usage)"
echo -e "\t./bin/localdbtool-archive.sh -f my_archive_configure.yml"
echo -e "\tor"
echo -e "\t./bin/localdbtool-sync.py -d <mongo data directory path> -a <archive location> -n <# of archives>"
