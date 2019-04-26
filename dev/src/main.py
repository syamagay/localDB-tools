#!/bin/python
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Main function for Local DB tool
#################################

if __name__ == '__main__':
    args = getArgs()

    if args.menu[0] == "summary":
        summary()
    elif args.menu[0] == "sync":
        sync()
    elif args.menu[0] == "verify":
        verify()
