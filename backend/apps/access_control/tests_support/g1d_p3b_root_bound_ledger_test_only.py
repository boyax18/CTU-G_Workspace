"""G1D-P3B: adapter around EXISTING disposable-only MySQL ledger, TEST ONLY.

This is not used by production services or commands. The existing ledger still
owns durable admission, one-use claiming, consumption, and audit rollback.
The adapter cannot establish a real privileged-writer fence or identity trust.
"""

from . import g1d_p1_authorization_design_test_only as auth
from . import g1d_p1_ledger_transaction_test_only as ledger
from . import g1d_p3a_root_endorsed_registry_test_only as roots
from .g1d_p3b_root_bound_executor_test_only import verify_root_bound_executor


class RootBoundDisposableLedger:
    def __init__(self, database, *, registry, pinned_roots, expected):
        auth.require(type(database) is ledger.DisposableLedger)
        database.guard()  # checks settings and connected schema before any SQL work
        self.database = database
        self.registry = registry
        self.pinned_roots = pinned_roots
        self.expected = expected

    def _checked(self, bundle, *, now):
        self.database.guard()
        receipt = verify_root_bound_executor(
            self.registry, self.pinned_roots, bundle,
            expected=self.expected, now=now,
        )
        auth.require(receipt.trust_epoch == self.registry.trust.epoch)
        auth.require(self.database.schema == self.expected.schema)
        return receipt

    def admit(self, bundle, *, now):
        proof = self._checked(bundle, now=now)
        request_id = self.database.admit(
            bundle, self.registry.trust,
            now=now,
            actor_id=proof.actor_id,
            challenge=self.expected.challenge,
        )
        auth.require(request_id == proof.request_id)
        return request_id

    def claim(self, bundle, *, now):
        proof = self._checked(bundle, now=now)
        return self.database.claim(proof.request_id, self.registry.trust, now=now)

    def execute(self, bundle, claim, *, clock, simulate_fenced_writers=False):
        auth.require(type(claim) is ledger.TestClaim)
        auth.require(callable(clock))
        proof = self._checked(bundle, now=clock())
        auth.require(claim.request_id == proof.request_id)
        # The ledger's own guarded transaction rechecks the *stored* signed
        # bundle, account eligibility, control epoch and one-use claim.
        # simulate_fenced_writers=True is a TEST assumption, NOT a real fence.
        return self.database.execute(
            claim, self.registry.trust, clock=clock,
            simulate_fenced_writers=simulate_fenced_writers,
        )

    def reconcile(self, request_id, *, now):
        """Read-only ambiguity resolution; does NOT retry uncertain writes.

        Historic signing evidence may have expired; rechecking only the root
        registry here does not make an old execution attempt live again.
        """
        self.database.guard()
        auth.require(type(request_id) is str and auth.uuid_value(request_id))
        trust = roots.verify_root_endorsed_registry(
            self.registry, self.pinned_roots,
            expected_schema=self.expected.schema,
            expected_incarnation=self.expected.incarnation,
            minimum_epoch=self.expected.minimum_epoch,
            now=now,
        )
        auth.require(auth.digest(roots.roster_bytes(trust)) == self.expected.roster_sha256)
        auth.require(self.database.schema == self.expected.schema)
        return self.database.resolve(request_id, trust)
