## Overview ##
You'll need MySQL, Memcached, and a python3 virtualenv.

### MySQL ###

```shell
$ brew install mysql56
```

There is nothing about the code that requires a specific version of MySQL. MySQL 5.6 is widely supported and hosted, so I've stuck with that; much easier to upgrade than downgrade due to the hosting environment.

#### Create a MySQL user ####
There is a default user the application uses to connect to mysql, you should over-ride that as described in the *Environment* section of the README for any environment other than your workstation.
```mysql
$ myql -u root
mysql> GRANT ALL ON sfpa_stats.* TO 'sfpa_django'@'localhost' identified by 'some_password';
mysql> create database if not exists sfpa_stats;
mysql> flush privileges;
```

### Memcached ###
```shell
$ brew install memcached
$ memcached -d
```

### Python ###
#### Environment ####

* Python 2.x is not supported, hasn't been tested.
* Python 3.4, as distributed with OS X, has been used for all development.

```
$ cd ~/Documents/django-pool-stats
$ virtualenv -p python3.4 django-pool-stats-ve
$ . django-pool-stats-ve/bin/activate
```

#### Requirements ####
Unfortunately I had to do a bit of a workaround to get `mysqlclient-python` to compile correctly on OS X. With the above virtualenv sourced:
```shell
$ git clone git@github.com:PyMySQL/mysqlclient-python.git
$ cd mysqlclient-python
$ CFLAGS=" -isysroot /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform" python setup.py install
```
Then install the rest of the requiremments, ie:
```shell
$ cd ~/Documents/django-pool-stats
$ pip install -r requiremments.pip
```

Now you can start it up in development mode:
```shell
$ cd ~/Documents/django-pool-stats/sfpa
$ python manage.py runserver
```
Now open your browser and go to http://localhost:8000/stats/
