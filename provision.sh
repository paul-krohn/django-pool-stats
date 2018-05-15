#!/bin/bash

set -ex

# update all the things
sudo apt-get update -qq
sudo apt-get upgrade -y

# packages
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password password janet'
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password janet'
sudo apt-get install -y mysql-common mysql-server mysql-client
sudo apt-get install -y python3 python3-dev python-virtualenv python-pip
sudo apt-get install -y libmysqlclient-dev memcached
sudo apt-get install -y firefox

GECKO_VERSION=v0.20.1

BASE_DIR="/usr/local/django-pool-stats"
VE_DIR="${BASE_DIR}/ve"

sudo mkdir -p ${BASE_DIR}
sudo chown $USER:$USER ${BASE_DIR}

BIN_DIR="${BASE_DIR}/bin"
mkdir -p $BIN_DIR
if ! [ `which geckodriver` ] ; then
    curl -LO https://github.com/mozilla/geckodriver/releases/download/${GECKO_VERSION}/geckodriver-${GECKO_VERSION}-linux64.tar.gz
    sudo tar -C /usr/local/bin -zxf geckodriver-${GECKO_VERSION}-linux64.tar.gz
fi

touch ~vagrant/.bash_profile
sudo chown ${USER}:${USER} ~vagrant/.bash_profile
/bin/echo ". ${VE_DIR}/bin/activate" > ~vagrant/.bash_profile

# python virtualenv
if [ ! -d ${VE_DIR} ] ; then
    virtualenv ${VE_DIR} -p python3
    . ${VE_DIR}/bin/activate
    pip install --upgrade pip
#    chown -R vagrant:vagrant ${VE_DIR}
fi
. ${VE_DIR}/bin/activate
pip install -r /vagrant/requirements.txt


# set up mysql user
cat <<MYSQL_USER | mysql -u root -pjanet
create database if not exists pool_stats;
create user if not exists 'pool_stats'@'localhost';
GRANT ALL ON pool_stats.* TO 'pool_stats'@'localhost';
GRANT ALL ON test_pool_stats.* TO 'pool_stats'@'localhost';
flush privileges;
MYSQL_USER

# allow access from not-localhost, so a dev has a chance
sudo sed -i 's/bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/my.cnf

