from .settings import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.1.101', 'carnegie.local']

LEAGUE['name'] = "SFPA"
LEAGUE['logo'] = '/static/stats/SFPAIncLongLogo4C.png'
LEAGUE['tag_line'] = 'Unity in Sportsmanship'
LEAGUE['background_image'] = '8ballrack2.png'

# DATABASES['default']['NAME'] = 'root'
DATABASES['default']['USER'] = 'root'
DATABASES['default']['PASSWORD'] = 'rabbit'
DATABASES['default']['HOST'] = 'db'
DATABASES['default']['PORT'] = '3306'

DATABASES['default']['OPTIONS'] = {'init_command': "SET FOREIGN_KEY_CHECKS=0", }

CACHES["default"]["LOCATION"] = "redis://redis:6379/0"
CACHES["page"]["LOCATION"] = "redis://redis:6379/1"

# thank you apple for this non-standard location
# LOGGING['handlers']['syslog']['address'] = '/var/run/syslog'

VIEW_CACHE_TIME = 1
MAX_SUBSTITUTIONS = 2
STATIC_ROOT = '/usr/local/pool-stats-static'