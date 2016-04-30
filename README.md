### Override settings ###

Any setting can be over-ridden in `pool/pool/override_settings.py`; for example, production database passwords:
```
from .settings import *
DATABASES['default']['PASSWORD'] = 'production_db_password'
```

There is a .gitignore entry for the file, so you don't accidentally check it in.
