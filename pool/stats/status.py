from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponse
from .models import Season
import json
import time


class HealthChecker(object):

    cache_string = str(time.time())
    cache_key = 'key_{}'.format(cache_string)

    def __init__(self):
        self.checks = dict()
        self.healthy = True
        self.version = settings.VERSION

    def db_check(self):
        try:
            Season.objects.get(is_default=True)
            self.checks['db'] = True
        except:
            self.checks['db'] = False
            self.healthy = False

    def cache_check(self):
        try:
            cache.set(self.cache_key, self.cache_string, 5)  # don't need it to last long ...
            if cache.get(self.cache_key) == self.cache_string:
                self.checks['cache'] = True
            else:
                self.checks['cache'] = False
                self.healthy = False
        except:
            self.checks['cache'] = False
            self.healthy = False

    def check(self):

        self.cache_check()
        self.db_check()

        report = dict()
        report['checks'] = self.checks
        report['healthy'] = self.healthy
        report['version'] = self.version
        return report

    def status(self):
        return 200 if self.healthy else 500


def index(request):

    checker = HealthChecker()

    return HttpResponse(
        json.dumps(checker.check(), indent=4, sort_keys=True) + "\n",
        content_type="text/javascript",
        status=checker.status()
    )

