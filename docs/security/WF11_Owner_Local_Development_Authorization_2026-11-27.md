# Owner local-development authorization: Permission Catalogue v2.1, v2.2 and v2.3

**Date:** 27 November 2026. **Authority:** the project owner, within project-level governance.
**Recorded by:** the implementing agent (Claude Opus 5.5), transcribing the owner's written instruction of
this date. The owner may countersign below.

**This is not an independent security approval.**

## Policy amendment (owner decision)

- Independent HDAC approval remains mandatory for production release.
- Local development activation may proceed under explicit project-owner authorization.
- The authorization covers the prepared v2.1, v2.2 and v2.3 permission changes in the existing Academic
  Settings development plan.
- Independent approval records stay OPEN until genuinely approved. Owner-authorized local activation is
  never represented as independent security approval.
- Mandatory institutional requirements are preserved. The independent-approval safeguard is not removed
  or disabled.

## Runtime record

`validation_v2_3.require_local_development_authorization()` reads this file. Only the local-only
`provision_academic_settings_v2_3_local_dev` command accepts it; production settings refuse it. It never
satisfies `require_independent_approval()`.

Owner local-development authorization: catalogue v2.1, v2.2 and v2.3
Scope: local development only
Independent approval: OPEN

| Pinned artifact | SHA-256 |
| --- | --- |
| `review_only/academic_settings_v2_3/v2_3_delta.json` | `4aef40877a90c7e9b6ec8b2560402be0acf3435ff524881260100ecf98204640` |
| `review_only/academic_settings_v2_3/ADDENDUM_PROPOSED.md` | `e9c3d4f094a465cf946c7ab89167b84a367a9d122957c71a7f130914a315e552` |
| `review_only/academic_settings_v2_3/runtime_changes_PROPOSED.patch` (applied) | `13782a2588187f703d9e080f2cd29e52b0c249d860623b8b660eb644e26b54f2` |

Base: catalogue v2.2, effective digest `192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d`.
v2.1 and v2.2 are used as their pinned, validated chain. The D-101 independent review stays OPEN, as does the
[sequential handoff](WF11_Catalogue_Sequential_Independent_Review_Handoff_2026-11-27.md).

Owner countersignature (optional): ____________________
