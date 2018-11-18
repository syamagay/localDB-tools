#!/bin/bash

### FILE NAME
PYTHON_SCRIPT="pipinstall.py"
MODULE_TEXT="install_list"
LOG_TEXT="install_log"

### COMMAND PATH
PIP_PATH=`which pip`
if [ $? -ne 0 ]; then
    echo "command 'pip' is not exist, exit ... "
    exit
fi
ECHO_PATH=`which echo`
if [ $? -ne 0 ]; then
    echo "command 'echo' is not exist, exit ... "
    exit
fi

### MAKE PYTHON SCRIPT
echo "import os" > ${PYTHON_SCRIPT}
echo "pip = os.path.join('${PIP_PATH}')" >> ${PYTHON_SCRIPT}
echo "echo = os.path.join('${ECHO_PATH}')" >> ${PYTHON_SCRIPT}

echo "module_list = []" >> ${PYTHON_SCRIPT}
echo "success_list = []" >> ${PYTHON_SCRIPT}
echo "failure_list = []" >> ${PYTHON_SCRIPT}

echo "f = open('${MODULE_TEXT}')" >> ${PYTHON_SCRIPT}
echo "readlines = f.readlines()" >> ${PYTHON_SCRIPT}
echo "for line in readlines :" >> ${PYTHON_SCRIPT}
echo "    module_list.append(line.strip())" >> ${PYTHON_SCRIPT}

echo "os.system(echo + ' \"[start] installation\" > ${LOG_TEXT}')" >> ${PYTHON_SCRIPT}
echo "print('Start installation ...')" >> ${PYTHON_SCRIPT}

echo "for module in module_list :" >> ${PYTHON_SCRIPT}
echo "    os.system(echo + ' \"-------------------------------------[start]-------------------------------------\" >> ${LOG_TEXT}')" >> ${PYTHON_SCRIPT}
echo "    os.system(echo + ' \"install ' + module +' ...\" >> ${LOG_TEXT}')" >> ${PYTHON_SCRIPT}
echo "    output = os.system(pip + ' install ' + module + ' >> ${LOG_TEXT} 2>&1')" >> ${PYTHON_SCRIPT}

echo "    if output == 0 :" >> ${PYTHON_SCRIPT}
echo "        success_list.append(module)" >> ${PYTHON_SCRIPT}
echo "    else : " >> ${PYTHON_SCRIPT}
echo "        failure_list.append(module)" >> ${PYTHON_SCRIPT}

echo "    os.system(echo + ' \"-------------------------------------[done]-------------------------------------\" >> ${LOG_TEXT}')" >> ${PYTHON_SCRIPT}
echo "    os.system(echo + ' \" \" >> ${LOG_TEXT}')" >> ${PYTHON_SCRIPT}

echo "print(' ')" >> ${PYTHON_SCRIPT}
echo "print('...Done.')" >> ${PYTHON_SCRIPT}
echo "print(' ')" >> ${PYTHON_SCRIPT}

echo "if success_list :" >> ${PYTHON_SCRIPT}
echo "    print('Successfully installed :')" >> ${PYTHON_SCRIPT}
echo "    for success in success_list :" >> ${PYTHON_SCRIPT}
echo "        print(' - ' + success)" >> ${PYTHON_SCRIPT}
echo "    print(' ')" >> ${PYTHON_SCRIPT}

echo "if failure_list :" >> ${PYTHON_SCRIPT}
echo "    print('Could not install with something problems :')" >> ${PYTHON_SCRIPT}
echo "    for failure in failure_list :" >> ${PYTHON_SCRIPT}
echo "        print(' - ' + failure)" >> ${PYTHON_SCRIPT}
echo "    print(' ')" >> ${PYTHON_SCRIPT}

echo "print('Please see ${LOG_TEXT} for checking detail')" >> ${PYTHON_SCRIPT}
