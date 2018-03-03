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

## Usage Docs

[Usage Documentation](usage_docs.md)

[Scoring Matches](scoring_matches.md)


## Caching

Django caching by default sets TTLs to the same values in internal caches (ie memcached) and downstream caches via the Cache-Control header (ie in local browser caches).

If what you want is to *locally* cache things until they are explicitly expired, but have those same things not cached by browsers, you have to over-ride this behaviour.
Fortunately, that is simple code up, once you have figured out how it works.

1. In settings.py, set a default value for caching things:

    ```python
    VIEW_CACHE_TIME=86400
    ```
1. Import that value into `urls.py`
    ```python
    from django.conf import settings
    ```
1. set views to be cached in `urls.conf`:
    ```python
    url(r'^some_view/(?P<arg_object_id>[0-9]+)', 
    cache_page(settings.VIEW_CACHE_TIME)(views.players), name='some_view'),

    ```
1. Then in `views.py`, set the cache-control header. Leave `max_age` alone, but add:
    ```python
    cached_view_cc_args = {
       'must_revalidate': True,
    }


    @cache_control(**cached_view_cc_args)
    def my_view(request, arg_object_id='some_default'):
        pass
    ```
This way, your rendered views are cached locally, so expensive pages do not need to be regenerated, and browsers always get a fresh page.

