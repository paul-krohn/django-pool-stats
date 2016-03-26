#!/bin/bash


sudo apt-get update -qq
sudo apt-get upgrade -y

sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password password janet'
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password janet'
sudo apt-get install -y mysql-server python3.4 python3.4-dev python-virtualenv python-pip mysql-client libmysqlclient-dev

rm -r django-pool-stats
virtualenv django-pool-stats -p python3.4
. django-pool-stats/bin/activate
pip install -r /vagrant/requirements.pip
