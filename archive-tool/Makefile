#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Makefile for archive tool
#################################

TOOLNAME="LocalDB Tool - Archive"
TARGETDIR?=/
SRC=src/
CONFIGURE=etc/localdbtools/archive.yml
CRONTAB=etc/cron.d/localdbtool-archive
BINFILE=usr/bin/localdbtool-archive.sh
BASHCOMPLETION=usr/share/bash-completion/completions/localdbtool-archive

## DO NOT TOUCH THESE
CONFIGUREDIR = $(patsubst %/,%,$(dir ${CONFIGURE}))
CRONTABDIR = $(patsubst %/,%,$(dir ${CRONTAB}))
BINFILEDIR = $(patsubst %/,%,$(dir ${BINFILE}))
BASHCOMPLETIONDIR = $(patsubst %/,%,$(dir ${BASHCOMPLETION}))


all:
	@echo "Makefile usage"
	@echo ""
	@echo " Configuration is done using environment variable"
	@echo ""
	@echo " TARGETDIR defines where to install ${TOOLNAME}"
	@echo ""
	@echo " The current values are:"
	@echo "  TARGETDIR=${TARGETDIR}"
	@echo "  CONFIGURE=${SRC}${CONFIGURE}"
	@echo "  CRONTAB=${SRC}${CRONTAB}"
	@echo ""
	@echo " Once environment variable are set, execute: make install"
	@echo ""

install: check
	@echo "Install ${TOOLNAME} ..."
	@mkdir -p ${TARGETDIR}${CONFIGUREDIR}
	@cp ${SRC}${CONFIGURE} ${TARGETDIR}${CONFIGURE}
	@mkdir -p ${TARGETDIR}${CRONTABDIR}
	@cp ${SRC}${CRONTAB} ${TARGETDIR}${CRONTAB}
	@mkdir -p ${TARGETDIR}${BINFILEDIR}
	@cp ${SRC}${BINFILE} ${TARGETDIR}${BINFILE}
	@mkdir -p ${TARGETDIR}${BASHCOMPLETIONDIR}
	@cp ${SRC}${BASHCOMPLETION} ${TARGETDIR}${BASHCOMPLETION}
	@echo "Installation finished, please edit ${TARGETDIR}${CONFIGURE} and ${TARGETDIR}${CRONTAB}"
	@echo ""

uninstall:
	@rm -rf ${TARGETDIR}${CONFIGURE} ${TARGETDIR}${CRONTAB} ${TARGETDIR}${BINFILE} ${TARGETDIR}${BASHCOMPLETION}

check:
	@/usr/bin/env python3 ../setting/check_python_modules.py

clean:
	@echo "USE 'make uninstall'!"

.PHONY: clean check uninstall
