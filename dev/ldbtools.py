#!/usr/bin/env python3
# -*- coding: utf-8 -*
##################################
## Author1: Eunchong Kim (eunchong.kim at cern.ch)
## Copyright: Copyright 2019, ldbtools
## Date: Jul. 2019
## Project: Local Database Tools
## Description: Main menu
##################################

from configs.development import *

if __name__ == '__main__':
    args = getArgs()

    if args.menu[0] == "summary":
        summary()
    elif args.menu[0] == "sync":
        sync()
    elif args.menu[0] == "verify":
        verify()
    elif args.menu[0] == "verify2":
        verify2()
