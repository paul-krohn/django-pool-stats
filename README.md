## Developing

### Memcached

Memcached defaults to `localhost:11211`, very easy to start:
```
memcached -d
```

### Choice of databases

Development has been done on, and instructions are provided for mysql. There is no direct database access or raw SQL in the application and no know reason why any database supported by Django will not work.

### MySQL setup

Assuming you stick with the default user/database name:

```
create user pool_stats@localhost identified by 'some_password';
create database pool_stats;
grant all privileges on pool_stats.* to 'pool_stats'@'localhost';
grant all privileges on test_pool_stats.* to 'pool_stats'@'localhost';
flush privileges;
```

### Override settings ###

Any setting can be over-ridden in `pool/pool/override_settings.py`; for example, database passwords:
```
from .settings import *
DATABASES['default']['PASSWORD'] = 'some_password'
```

There is a .gitignore entry for the file, so you don't accidentally check it in.

### Migrations

Standard django-style:

```
python manage.py migrate
```

### Fixtures

Fixtures are provided to get you up and running with sample data; they are broken up so you can load just what you need.

```
SAMPLES="sample_seasons sample_game_setup sample_sponsors sample_players sample_divisions sample_teams  sample_matches  sample_weeks"
for SAMPLE in ${SAMPLES} ; do {
  python manage.py loaddata $SAMPLE;
} ; done
```