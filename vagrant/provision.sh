#!/bin/bash


sudo apt-get update -qq
sudo apt-get upgrade -y

sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password password janet'
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password janet'
sudo apt-get install -y mysql-server python3.4

# virtualenv django-pool-stats
# . django-pool-stats/bin/activate
#
# pip install -r
