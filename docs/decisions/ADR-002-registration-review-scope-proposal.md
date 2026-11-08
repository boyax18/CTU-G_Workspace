# ADR-002 — Registration-Review Permission Scope (Proposal)

**Project:** CTU-G Workspace  
**Status:** PROPOSED — **NOT ADOPTED / NO PERMISSION ACTIVATION**  
**Date:** 2026-11-08

## Context

The first local Workspace `Admin` was created and audited independently of the Django framework Superuser. The V2 catalogue planner found 105 proposed missing service/permission definitions, four matching active base roles, and 108 deferred role/permission items. No services, permissions or grants were activated. The AR-6A1 registration review domain service has passing isolated tests, but it intentionally remains disabled for live use.

## Proposed decision

Make **registration review** the first bounded, permission-governed Workspace Admin workflow, without activating unrelated modules or granting every V2 default. Adopt, subject to independent owner approval and tests, an exact three-permission Admin scope:

- `accounts.registration_requests.read`: eligible pending registration list/details, redacted and object-scoped.
- `accounts.registration_requests.approve`: only eligible pending Student/Instructor base role; authenticated reviewer must be different from target; full audit.
- `accounts.registration_requests.reject`: same safeguards plus allowlisted non-sensitive rejection reasons; full audit.

No proposed read or decision code grants technical privilege, Admin/G membership, Treasurer or Advisor appointment, framework Superuser rights, finance access, or unreviewed service activation. Reviewer identity, effective permission including Deny, scope eligibility and audit are enforced server-side for each request.

This ADR is **not an approval of the pinned full v2.0-review-1 catalogue**. A narrower activation must have an independently versioned, approved exact manifest/profile and must not silently edit the V2 proposal. Both `accounts` and `access_control` services are required active by the current review domain service, which needs its own reviewed activation sequencing.

## Alternatives considered

| Option | Assessment |
| --- | --- |
| Activate all 95 permission definitions, 106 role defaults and 10 services together | **Not acceptable now:** unresolved V2-01..V2-10 gates and feature-readiness concerns. |
| Add three permissions and grants manually to MySQL without a versioned plan | **Not acceptable:** bypasses catalogue approval, audit and repeatable migrations/activation controls. |
| Review full V2 metadata separately, then activate a limited exact registration profile | **Preferred candidate**, only after authoritative approval, static/isolated-MySQL validation and read-only impact review. |
| Keep registration review blocked until all system modules are implemented | Safe but unnecessarily couples unrelated features; not required if an independently reviewed narrow activation profile can satisfy the applicable governance gates. |

## Implementation and verification consequences

1. Preserve existing pinned V2 proposal, manifest, and source hash; do not modify live database in AR-6B1.
2. First Admin assignment is not evidence of catalogue initializer authority or approval of service/grant mutations.
3. Future API must independently enforce session/CSRF, the exact permission, record eligibility, self-review restrictions, body validation, rate limits, and no stale permission cache.
4. Registration review uses atomic audit and base-role assignment. Negative and concurrency tests must pass with isolated MySQL before any live deployment.
5. Future profile requires an explicit reversible audit-backed activation runbook and verified separation between Django Superuser and Workspace governance.

## Owner decision required

- [ ] Accept these three permission codes and object-scope policies.
- [ ] Approve the versioned registration-review activation profile and exact manifest digest.
- [ ] Identify accountable owner and independent reviewer/executor as required by the governance policy.
- [ ] Approve and verify relevant security gates, negative tests, audit behavior, and rollback.
- [ ] Record dated acceptance. Only then change this ADR from PROPOSED to ADOPTED.

**Until accepted, no catalogue initialization, grants, service activation, or review API activation is authorized.**
