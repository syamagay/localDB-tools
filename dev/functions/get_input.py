#!/usr/bin/env python3
# -*- coding: utf-8 -*
##################################
## Author1: Eunchong Kim (eunchong.kim at cern.ch)
## Copyright: Copyright 2019, ldbtools
## Date: Jul. 2019
## Project: Local Database Tools
## Description: Logging error message and exit with code
##################################

from configs.development import * # Omajinai

def getInput(message, confirm_flg):
    answer = input(message)
    yes_no = ""
    if confirm_flg:
        while yes_no not in ("yes", "no"):
            yes_no = input("Your input is '%s'. Is it correct? ['yes' or 'no']: " % answer)
            if yes_no == "yes":
                break
            elif yes_no == "no":
                answer = input(message)
            else:
                print("Enter 'yes' or 'no'.")

    return answer
