"""Second-server harness settings: physical server identity checked before DDL."""
import json
import os
from pathlib import Path
import re
import tempfile
import MySQLdb
from django.core.exceptions import ImproperlyConfigured

_isolated = json.loads(Path(os.environ["WORKSPACE_ISOLATED_CONFIG"]).read_text())
_db = _isolated["database"]
_data = Path(_isolated["datadir"]).resolve(strict=True)
if (not re.fullmatch(r"test_ctug_executor_[0-9a-f]{16}", _db["NAME"])
        or _db["HOST"] != "." or not _db["OPTIONS"]["named_pipe"]
        or _data.parent.parent != Path(tempfile.gettempdir()).resolve()
        or not _data.parent.name.startswith("ctug-p3c5-separate-")):
    raise ImproperlyConfigured("Isolated executor configuration refused.")
_probe = MySQLdb.connect(host=".", user=_db["USER"], passwd=_db["PASSWORD"],
                     unix_socket=_db["OPTIONS"]["unix_socket"], named_pipe=True,
                     server_public_key_path=_db["OPTIONS"]["server_public_key_path"])
with _probe.cursor() as _cursor:
    _cursor.execute("SELECT @@datadir,@@skip_networking,@@socket")
    _directory, _skip, _pipe = _cursor.fetchone()
    if (Path(_directory).resolve() != _data or _skip != 1
            or not _pipe.lower().endswith(_db["OPTIONS"]["unix_socket"].lower())):
        raise ImproperlyConfigured("Physical isolated MySQL identity refused.")
_probe.close()
os.environ["WORKSPACE_DEPLOYMENT_SETTINGS"] = "1"
for _key, _field in (("DB_NAME", "NAME"), ("DB_USER", "USER"), ("DB_PASSWORD", "PASSWORD"), ("DB_HOST", "HOST"), ("DB_PORT", "PORT")):
    os.environ[_key] = str(_db[_field])
from .settings import *  # noqa: F403

DATABASES = {"default": _db}
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
WORKSPACE_REGISTRATION_APPROVAL_ENABLED = True
WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED = True
