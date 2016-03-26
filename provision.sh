#!/bin/bash

# update all the things
sudo apt-get update -qq
sudo apt-get upgrade -y

# packages
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password password janet'
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password janet'
sudo apt-get install -y mysql-common mysql-server mysql-client
sudo apt-get install -y python3.4 python3.4-dev python-virtualenv python-pip
sudo apt-get install -y libmysqlclient-dev memcached

# python virtualenv
rm -r /vagrant/django-pool-stats-ve
virtualenv /vagrant/django-pool-stats-ve -p python3.4
. /vagrant/django-pool-stats-ve/bin/activate
pip install -r /vagrant/requirements.pip
