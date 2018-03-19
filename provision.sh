#!/bin/bash

# update all the things
sudo apt-get update -qq
sudo apt-get upgrade -y

# packages
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password password janet'
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password janet'
sudo apt-get install -y mysql-common mysql-server mysql-client
sudo apt-get install -y python3.5 python3.5-dev python-virtualenv python-pip
sudo apt-get install -y libmysqlclient-dev memcached

VE_DIR="/usr/local/django-pool-stats-ve"

/bin/echo ". ${VE_DIR}/bin/activate" > ~vagrant/.bash_profile
chown vagrant:vagrant

# python virtualenv
if [ ! -d ${VE_DIR} ] ; then
    sudo virtualenv ${VE_DIR} -p python3.5
    sudo chown -R vagrant:vagrant ${VE_DIR}
fi
. ${VE_DIR}/bin/activate
pip install -r /vagrant/requirements.pip


# set up mysql user
cat <<MYSQL_USER | mysql -u root -pjanet
create database if not exists pool_stats;
GRANT ALL ON pool_stats.* TO 'pool_stats'@'localhost' identified by 'isysroot';
GRANT ALL ON test_pool_stats.* TO 'pool_stats'@'localhost' identified by 'isysroot';
flush privileges;
MYSQL_USER

# allow access from not-localhost, so a dev has a chance
sed -i 's/bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/my.cnf


# teensy wrapper to start the app in development mode
cat <<EOF > ~vagrant/runserver.sh
cd /vagrant/pool
python manage.py runserver 0.0.0.0:8000
EOF

chown vagrant:vagrant ~vagrant/runserver.sh
chmod +x ~vagrant/runserver.sh

