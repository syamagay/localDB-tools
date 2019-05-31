#!/bin/bash

if [ ! -f my_web_configure.yml ]; then
    cp ../scripts/yaml/web-conf.yml my_web_configure.yml
fi
$EDITOR my_web_configure.yml
