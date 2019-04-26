#!/bin/bash
#################################
# Author: Eunchong Kim
# Email: eunchong.kim at cern.ch
# Date: April 2019
# Project: Local Database for ITk
# Description: Archive mongo data
#################################

function usage() {
    echo -e "Usage) ./bin/localdbtool-archive.sh --config <...>"
    echo -e "\t-h -help"
    echo -e "\t-f --config : config path"
    echo -e "\t-d --data : data directory path"
    echo -e "\t-a --archive_path : archive path"
    echo -e "\t-n --n_archives : # of archives to keep"
    exit 1
}

if [ -z $1 ]; then
    echo -e "Wrong usage!"
    usage
fi

while [ ! -z $1 ]; do
#    PARAM=`echo $1 | awk -F= '{print $1}'`
    case $1 in
        -h | --help)
            usage
            ;;
        -f | --config)
            config_path=$2
            shift
            ;;
        -a | --archive_path)
            archive_path=$2
            shift
            ;;
        -d | --data_path)
            data_path=$2
            shift
            ;;
        -n | --n_archives)
            n_archives=$2
            shift
            ;;
        *)
            echo -e "Wrong usage!"
            usage
            ;;
    esac
    shift
done

# Parse from yaml file
function parse_yaml {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}

# Read config file if set
if [ ! -z $config_path ]; then
    echo "The config path set! Read config file ..."
    eval $(parse_yaml $config_path)
fi

echo "config_path='$config_path', data_path='$data_path', archive_path='$archive_path', n_archives='$n_archives', Leftovers: $@"

if [[ -z "$data_path" || -z $archive_path || -z $n_archives ]]; then
    echo "database path or backup path or # of archives not set! Exit!"
    exit 1
fi

mkdir -p $archive_path

tar zcvf ${archive_path}/mongo_`date +%y%m%d_%H%M%S`.tar.gz ${data_path}

# Delete over numbers of archives
nn=$(echo $n_archives+1 | bc)
if test -n "`ls -t ${archive_path}/* | tail -n+$nn`"; then
  rm -v `ls -t ${archive_path}/* | tail -n+$nn`
fi
