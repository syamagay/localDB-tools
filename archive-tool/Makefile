#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Makefile for archive tool
#################################

TARGETDIR?=/
SRC=src
TARGETETCDIR=/etc/localdbtools
CONFIGURE=/etc/localdbtools/archive.yml
CRONTAB=/etc/cron.d/localdbtool-archive
BINFILE=/usr/bin/localdbtool-archive.sh
BASHCOMPLETION=/usr/share/bash-completion/completions/localdbtool-archive

#CONFIGURE_LOCAL=$(shell pwd)/default-sync.yml
#CRONTAB_LOCAL=$(shell pwd)/crontab-sync

all:
	@echo "Makefile usage"
	@echo ""
	@echo " Configuration is done using environment variable"
	@echo ""
	@echo " TARGETDIR defines where to install RPi-Monitor"
	@echo ""
	@echo " The current values are:"
	@echo "  TARGETDIR=${TARGETDIR}"
	@echo "  CONFIGURE=${SRC}${CONFIGURE}"
	@echo "  CRONTAB=${SRC}${CRONTAB}"
	@echo ""
	@echo " Once environment variable are set, execute: make install"
	@echo ""

install: check
	@echo "Install sync tool ..."
	@mkdir -p ${TARGETETCDIR}
	@cp ${SRC}${CONFIGURE} ${CONFIGURE}
	@cp ${SRC}${CRONTAB} ${CRONTAB}
	@cp ${SRC}${BINFILE} ${BINFILE}
	@cp ${SRC}${BASHCOMPLETION} ${BASHCOMPLETION}

uninstall:
	@rm -rf ${CONFIGURE} ${TARGETETCDIR} ${CRONTAB} ${BINFILE} ${BASHCOMPLETION}

check:
	@/usr/bin/env python3 ../scripts/check_python_modules.py


# TODO complete install on local
install-local: check $(CONFIGURE_LOCAL) $(CRONTAB_LOCAL)
	crontab $(CRONTAB_LOCAL)

$(CONFIGURE) $(CRONTAB):
	@mkdir -p configures
	@cp src/etc/localdbtools/default.yml configures/default.yml
	@cp src/etc/cron.d/localdbtool-sync configures/localdbtool-sync

$(CRONTAB_LOCAL): ${CONFIGURE_LOCAL}
	@echo "* * 3 * * $(PWD)/$(TARGET) sync --config $(PWD)/$(CONFIG)" > $(CRONTAB_LOCAL)
	"$$[EDITOR]" $(CRONTAB_LOCAL)

${CONFIGURE_LOCAL}:


clean:
	@echo "USE 'make uninstall'!"

.PHONY: clean check uninstall
