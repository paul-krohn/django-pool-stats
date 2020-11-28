#!/bin/bash

set -e

CHEF_VERSION="16.1.16"
CHEF_REVISION="-1"

cd /tmp

INSTALLED_VERSION=$(dpkg -s chef | grep Version | awk '{print $2}')

if [[ ${INSTALLED_VERSION} != "${CHEF_VERSION}${CHEF_REVISION}"  ]] ; then
    curl -s -LO https://packages.chef.io/files/stable/chef/${CHEF_VERSION}/ubuntu/18.04/chef_${CHEF_VERSION}${CHEF_REVISION}_amd64.deb
    sudo dpkg -i chef_${CHEF_VERSION}-1_amd64.deb
fi
cd /chef
sudo chef-solo --chef-license accept -c solo.rb -j solo.json