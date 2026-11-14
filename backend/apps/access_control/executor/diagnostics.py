"""Read-only deployment diagnostics; no implicit installation or privilege changes."""
from django.conf import settings
from django.db import connection, transaction
from apps.access_control.protected_requests import require


def verify_deployment():
    server = getattr(settings, "WORKSPACE_EXECUTOR_SERVER", None)
    if server is not None:
        require(not server.get("isolated_datadir"))
        from pathlib import Path
        from cryptography.hazmat.primitives import serialization
        from .engine import Executor
        key = serialization.load_pem_private_key(Path(server["issuer_private_key"]).read_bytes(), password=None)
        executor = Executor(server, key)
        executor.identity()
        with transaction.atomic(durable=True):
            executor.control()
        return
    identity = getattr(settings, "WORKSPACE_RUNTIME_IDENTITY", None)
    clients = getattr(settings, "WORKSPACE_EXECUTOR_CLIENTS", None)
    require(type(identity) is dict and type(clients) is dict and set(clients) == {"ordinary"})
    with connection.cursor() as c:
        c.execute("SELECT DATABASE(),CURRENT_USER(),@@server_uuid,CURRENT_ROLE()")
        require(c.fetchone() == (identity["schema"], identity["principal"], identity["server_uuid"], "NONE"))
        c.execute("SHOW GRANTS")
        for (grant,) in c.fetchall():
            upper = grant.upper()
            require(" ON " in upper and not any(w in upper for w in ("ALL PRIVILEGES", "GRANT OPTION", "PROXY", "CREATE", "ALTER", "DROP", "TRIGGER", "EXECUTE")))
            permissions, target = upper.split(" ON ", 1)
            require(permissions == "GRANT USAGE" or permissions == "GRANT SELECT" or
                    target.startswith("`" + identity["schema"].upper() + "`.`DJANGO_SESSION` "))
    from .client import transport
    ready = transport("/ready", {})
    require(ready["isolated"] is False and ready["kind"] == "ordinary"
            and ready["schema"] == identity["schema"] and ready["server_uuid"] == identity["server_uuid"])
