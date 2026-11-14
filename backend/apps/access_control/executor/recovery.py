"""Dedicated recovery credential: hold, or root-approved epoch/incarnation rotation.

No application DML, retry, audit deletion, privileged demotion or automatic resume.
This API is deliberately absent from the network dispatcher.
"""
from django.db import connection, transaction
from apps.access_control.protected_requests import canonical, digest, require, _hex
from .trust import TrustStore, definition_hash


class RecoveryControl:
    def __init__(self, config):
        self.config = config

    def _identity(self):
        require(not connection.in_atomic_block)
        with connection.cursor() as c:
            c.execute("SELECT DATABASE(),CURRENT_USER(),@@server_uuid")
            require(c.fetchone() == (self.config["schema"], self.config["principal"], self.config["server_uuid"]))

    def hold(self, reason_hash):
        self._identity()
        require(_hex(reason_hash))
        with transaction.atomic(durable=True):
            with connection.cursor() as c:
                c.execute("SELECT epoch FROM wex_control WHERE id=1 FOR UPDATE")
                old = c.fetchone()[0]
                c.execute("UPDATE wex_control SET halted=1 WHERE id=1")
                c.execute("INSERT INTO wex_recovery_events(action,previous_epoch,next_epoch,reason_hash,evidence) VALUES('HOLD',%s,%s,%s,%s)",
                          (old, old, reason_hash, canonical({"reason_hash": reason_hash})))

    def rotate(self, reason_hash):
        self._identity()
        require(_hex(reason_hash))
        with transaction.atomic(durable=True):
            with connection.cursor() as c:
                c.execute("SELECT epoch,incarnation,halted FROM wex_control WHERE id=1 FOR UPDATE")
                old_epoch, old_incarnation, halted = c.fetchone()
                roster, trust, _ = TrustStore(self.config).load()
                require(halted == 1 and trust.epoch > old_epoch and trust.incarnation != old_incarnation)
                c.execute("UPDATE wex_control SET epoch=%s,incarnation=%s,roster_hash=%s,fence_hash=%s,recovery_hash=%s,release_hash=%s,definition_hash=%s,roster_expires=%s,halted=0 WHERE id=1",
                          (trust.epoch, trust.incarnation, digest(roster), trust.fence_hash, trust.recovery_hash, trust.release_hash, definition_hash(roster), roster["expires"]))
                c.execute("INSERT INTO wex_recovery_events(action,previous_epoch,next_epoch,reason_hash,evidence) VALUES('ROTATE',%s,%s,%s,%s)",
                          (old_epoch, trust.epoch, reason_hash, canonical(TrustStore(self.config).archive(roster))))

    def refresh(self, reason_hash):
        """Root-signed TTL renewal, without changing trust, clearing holds or replay state."""
        self._identity()
        require(_hex(reason_hash))
        with transaction.atomic(durable=True):
            with connection.cursor() as c:
                c.execute("SELECT epoch,incarnation,definition_hash,roster_expires,halted FROM wex_control WHERE id=1 FOR UPDATE")
                epoch, incarnation, definition, expires, halted = c.fetchone()
                roster, trust, _ = TrustStore(self.config).load()
                require(halted == 0 and (trust.epoch, trust.incarnation, definition_hash(roster)) == (epoch, incarnation, definition)
                        and roster["expires"] > expires)
                c.execute("UPDATE wex_control SET roster_hash=%s,roster_expires=%s WHERE id=1", (digest(roster), roster["expires"]))
                c.execute("INSERT INTO wex_recovery_events(action,previous_epoch,next_epoch,reason_hash,evidence) VALUES('REFRESH',%s,%s,%s,%s)",
                          (epoch, epoch, reason_hash, canonical(TrustStore(self.config).archive(roster))))
