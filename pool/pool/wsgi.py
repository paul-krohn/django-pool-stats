"""
WSGI config for the 'pool' project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

this_directory = os.path.dirname(__file__)
settings_module = 'pool.settings'
override_settings_file = 'override_settings.py'
if os.path.exists(os.path.join(this_directory, override_settings_file)):
    settings_module = 'pool.override_settings'
else:
    print("no %s in %s" % (override_settings_file, this_directory))
print("settings module is %s" % settings_module)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

application = get_wsgi_application()
