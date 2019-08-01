#!/bin/bash
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for YARR
# Description: Automatically create tool installer
#################################

BIN_DIR=bin
COMMON_NAME=localdbtool
ITSNAME="[LocalDB Tool Auto]"

function usage() {
    echo -e "Usage) ./compiler.sh <tool-src-path>"
    echo -e "\t-h, --help: Show this help\n"
}

# Start
echo -e "$ITSNAME Welcome!"

# Arguments loop
if [ -z $1 ]; then
    echo -e "$ITSNAME No arguments! Abort!"
    usage
    exit 1
fi

while [ ! -z $1 ]; do
    PARAM=`echo $1 | awk -F= '{print $1}'`
    case $PARAM in
        -h | --help)
            usage
            return
            ;;
        *)
            # Find src by path
            if [ ! -f $1 ]; then
                echo -e "$ITSNAME no src file found in $1 ! Abort!"
                usage
                exit 1
            else
                TOOL_PATH=$1
                TOOL_FILE=`basename $TOOL_PATH`
                TOOL_NOEX=${TOOL_FILE%.py}
                TARGET=${COMMON_NAME}-${TOOL_FILE}
                echo -e "$ITSNAME tool name is $TARGET"
            fi
            ;;
    esac
    shift
done


# Create bin
echo -e "$ITSNAME Create $BIN_DIR/$TARGET ..."
mkdir -p $BIN_DIR
rm -f $BIN_DIR/$TARGET
#grep -vh -e "^\s*#" -e "__main__" configs/*.py >> $BIN_DIR/$TARGET
grep -vh -e "__main__" configs/*.py >> $BIN_DIR/$TARGET
grep -vh -e "import" -e "__main__" functions/*.py >> $BIN_DIR/$TARGET
grep -vh -e "import" $TOOL_PATH >> $BIN_DIR/$TARGET
chmod +x $BIN_DIR/$TARGET

## Copy default configure files
#TARGET_CONF=$TARGET_DIR/root/etc/$TARGET_NOEX
#echo -e "$ITSNAME Create $TARGET_CONF ..."
#mkdir -p $TARGET_CONF
#cp configures/${TARGET_NOEX}.conf $TARGET_CONF/.
#
## Copy cron configure
#TARGET_CRON=$TARGET_DIR/root/etc/cron.d
#echo -e "$ITSNAME Create $TARGET_CRON ..."
#mkdir -p $TARGET_CRON
#cp cron.d/$TARGET_NOEX $TARGET_CRON/.
#
## Copy bash completion
#TARGET_COMP=$TARGET_DIR/root/usr/share/bash-completion/completions
#echo -e "$ITSNAME Create $TARGET_COMP ..."
#cp completions/$TARGET_NOEX $TARGET_COMP/.
#
## Copy Makefile
#echo -e "$ITSNAME Create Makefile ..."
#cp Makefile $TARGET_DIR/.
#
##complete -F _menu ./bin/localdb-tool.py

echo -e "$ITSNAME Finish!"

echo -e "$ITSNAME Tool $TOOL_PATH is on $TARGET_DIR"
