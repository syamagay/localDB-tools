#!/bin/bash
#################################
# Contacts: Arisa Kubota
# Email: arisa.kubota at cern.ch
# Date: July 2019
# Project: Local Database for Yarr
# Usage: ./setup_tool.sh
################################

set -e

# Usage
function usage {
    cat <<EOF

Set some tools for Local DB by:

    ./setup_tool.sh

    - h               Show this usage
    - t               Set LocalDB tools into ${HOME}/.local/bin
    - r               Clean the settings (reset)

EOF
}

# Start
if [ `echo ${0} | grep bash` ]; then
    echo "[LDB] DO NOT 'source'"
    usage
    return
fi

shell_dir=$(cd $(dirname ${BASH_SOURCE}); pwd)
tools=false
reset=false
while getopts htr OPT
do
    case ${OPT} in
        h ) usage ;;
        t ) tools=true ;;
        r ) reset=true ;;
        * ) usage
            exit ;;
    esac
done

BIN=${HOME}/.local/bin
BASHLIB=${HOME}/.local/lib/localdb-tools/bash-completion/completions
MODLIB=${HOME}/.local/lib/localdb-tools/modules
ENABLE=${HOME}/.local/lib/localdb-tools/enable

if "${reset}"; then
    echo -e "[LDB] Clean Local DB settings:"
    echo -e "[LDB]      -> remove Local DB Tools in ${BIN}"
    for i in `ls -1 ${shell_dir}/../bin/`; do
        if [ -f ${BIN}/${i} ]; then
            echo -e "[LDB]         - ${i}"
        fi
    done
    echo -e "[LDB]      -> remove retrieve repository in ${HOME}/.localdb_retrieve"
    echo -e "[LDB] Continue? [y/n]"
    read -p "[LDB] > " answer
    while [ -z ${answer} ]; 
    do
        read -p "[LDB] > " answer
    done
    echo -e "[LDB]"
    if [[ ${answer} != "y" ]]; then
        echo "[LDB] Exit ..."
        echo "[LDB]"
        exit
    fi
    # binary
    for i in `ls -1 ${shell_dir}/../bin/`; do
        if [ -f ${BIN}/${i} ]; then
            rm ${BIN}/${i}
        fi
    done
    bin_empty=true
    for i in `ls -1 ${BIN}`; do
        if [ `echo ${i} | grep localdbtool` ]; then
            bin_empty=false
        fi
    done
    if "${bin_empty}"; then
        if [ -d ${HOME}/.local/lib/localdb-tools ]; then
            rm -r ${HOME}/.local/lib/localdb-tools
        fi
    fi
    # library
    if ! "${bin_empty}"; then
        for i in `ls -1 ${shell_dir}/../lib/localdb-tools/bash-completion/completions/`; do
            if [ -f ${BASHLIB}/${i} ]; then
                rm ${BASHLIB}/${i}
            fi
        done
        for i in `ls -1 ${shell_dir}/../lib/localdb-tools/modules/`; do
            if [ -f ${MODLIB}/${i} ]; then
                rm ${MODLIB}/${i}
            fi
        done
        lib_empty=true
        for i in `ls -1 ${MODLIB}`; do
            if [ `echo ${i} | grep py` ]; then
                lib_empty=false
            fi
        done
        for i in `ls -1 ${BASHLIB}`; do
            if [ `echo ${i} | grep localdbtool` ]; then
                lib_empty=false
            fi
        done
        if [ ${lib_empty} ]; then
            if [ -d ${HOME}/.local/lib/localdb-tools ]; then
                rm -r ${HOME}/.local/lib/localdb-tools
            fi
        fi
    fi
    if [ -d ${HOME}/.localdb_retrieve ]; then
        rm -r ${HOME}/.localdb_retrieve
    fi
    echo -e "[LDB] Finish Clean Up!"
    exit
fi

# Check python module
echo -e "[LDB] Check python modules..."
/usr/bin/env python3 ${shell_dir}/check_python_modules.py
if [ $? = 1 ]; then
    echo -e "[LDB] Failed!!!"
    echo -e "[LDB] Install the missing modules by:"
    echo -e "[LDB] pip3 install --user -r ${shell_dir}/requirements-pip.txt"
    echo -e "[LDB] exit..."
    exit
fi
echo -e "[LDB] Done."
echo -e ""

readme=${shell_dir}/README

if [ -f ${readme} ]; then
    rm ${readme}
fi

echo -e "# scanConsole with Local DB" | tee -a ${readme}
echo -e "" | tee -a ${readme}

if "${tools}"; then
    # Setting function
    mkdir -p ${BIN}
    mkdir -p ${BASHLIB}
    mkdir -p ${MODLIB}
    
    cp ${shell_dir}/../bin/* ${BIN}/
    chmod +x ${BIN}/*
    
    cp -r ${shell_dir}/../lib/localdb-tools/bash-completion/completions/* ${BASHLIB}/
    cp -r ${shell_dir}/../lib/localdb-tools/modules/* ${MODLIB}/
    cp ${shell_dir}/../lib/localdb-tools/enable ${ENABLE}


    if ! cat $HOME/.bashrc | grep 'export PATH="$HOME/.local/bin:$PATH"' 2>&1 > /dev/null; then
        # Add PATH on ~/.local/bin in bashrc
        echo -e "[LDB] Add PATH on ~/.local/bin"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> $HOME/.bashrc
        echo -e "[LDB]"
    fi
fi

# settings
echo -e "## Settings" | tee -a ${readme}
echo -e "- 'Makefile'" | tee -a ${readme}
echo -e "  - description: install required softwares and setup Local DB functions for the machine." | tee -a ${readme}
echo -e "  - requirements: sudo user, git, net-tools" | tee -a ${readme}
echo -e "- './setup_tool.sh'" | tee -a ${readme}
echo -e "  - description: setup Local DB functions for the user local." | tee -a ${readme}
echo -e "  - requirements: required softwares" | tee -a ${readme}
echo -e "" | tee -a ${readme}

# all function
ITSNAME="LocalDB Tools"
echo -e "## $ITSNAME" | tee -a ${readme}
echo -e "'source ${HOME}/.local/lib/localdb-tools/enable' can enable tab-completion" | tee -a ${readme}
echo -e "" | tee -a ${readme}

# upload.py
ITSNAME="LocalDB Tool Setup Upload Tool"
echo -e "### $ITSNAME" | tee -a ${readme}
echo -e "- 'localdbtool-upload --scan <path to result directory>' can upload scan data" | tee -a ${readme}
echo -e "- 'localdbtool-upload --dcs <path to result directory>' can upload dcs data based on scan data" | tee -a ${readme}
echo -e "- 'localdbtool-upload --cache' can upload every cache data" | tee -a ${readme}
echo -e "- 'localdbtool-upload --help' can show more usage." | tee -a ${readme}
echo -e "" | tee -a ${readme}

# retrieve.py
ITSNAME="LocalDB Tool Setup Retrieve Tool"
echo -e "### $ITSNAME" | tee -a ${readme}
echo -e "- 'localdbtool-retrieve init' can initialize retrieve repository" | tee -a ${readme}
echo -e "- 'localdbtool-retrieve remote add <remote name>' can add remote repository for Local DB/Master Server" | tee -a ${readme}
echo -e "- 'localdbtool-retrieve --help' can show more usage." | tee -a ${readme}
echo -e "" | tee -a ${readme}

# finish
ITSNAME="Quick Trial"
echo -e "## $ITSNAME" | tee -a ${readme}
echo -e "$ source ${HOME}/.local/lib/localdb-tools/enable" | tee -a ${readme}
echo -e "$ localdbtool-retrieve init" | tee -a ${readme}
echo -e "$ localdbtool-retrieve remote add origin" | tee -a ${readme}
echo -e "$ localdbtool-retrieve log origin" | tee -a ${readme}
echo -e "" | tee -a ${readme}
echo -e "[LDB] This description is saved as ${readme}"
