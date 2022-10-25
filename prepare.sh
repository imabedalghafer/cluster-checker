#!/bin/bash

echo 'preparing python3 virtual env to install into it the requirements.txt file'
echo "in case you don't have python3 installed on your wsl, you can either install it or use WSL of ubuntu 20.04"
if [ -f /bin/yum ]
then
    echo 'rpm based distro detected..'
    echo 'executing rpm -qa | grep virtualenv'
    rpm -qa | grep virtualenv
    if [ $? -eq 0 ]
    then
        echo 'virtual environment of python package avaible, creating a new dev environment and install requirements on it'
        python3 -m venv dev
        source dev/bin/activate
        dev/bin/pip install --upgrade pip
        dev/bin/pip install opencensus lxml xmltodict
        echo 'Ready to go, please ensure to activate the dev before you run the script, to activate it use source dev/bin/activate'
    else
        echo 'Please install the python3 venv module, usually the package name is python3-virtualenv'
    fi
elif [ -f /bin/apt ]
then
    echo 'deb based distro detected..'
    echo 'executing apt list --installed | grep venv'
    apt list --installed | grep venv
    if [ $? -eq 0 ]
    then
        echo 'virtual environment of python package avaible, creating a new dev environment and install requirements on it'
        python3 -m venv dev
        source dev/bin/activate
        dev/bin/pip install --upgrade pip
        dev/bin/pip install opencensus lxml xmltodict
        echo 'Ready to go, please ensure to activate the dev before you run the script, to activate it use source dev/bin/activate'
    else
        echo 'Please install the python3 venv module usually its name is python3.X-venv'
    fi
fi