#!/bin/bash

set -ex

CHEF_VERSION="14.11.21"

cd /tmp

if [ $(which chef-solo) ] ; then
    INSTALLED_VERSION=$(chef-solo --version |awk '{print $2}')
else
    INSTALLED_VERSION="none"
fi

if [[ ${INSTALLED_VERSION} != ${CHEF_VERSION} ]] ; then
    curl -s -LO https://packages.chef.io/files/stable/chef/${CHEF_VERSION}/ubuntu/18.04/chef_${CHEF_VERSION}-1_amd64.deb
    sudo dpkg -i chef_${CHEF_VERSION}-1_amd64.deb
fi
cd /chef
sudo chef-solo -c solo.rb -j solo.json