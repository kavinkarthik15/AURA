# AURA Cleanup Classification Report

**PASS:** 2 - Candidate classification only  
**Date:** 2026-10-05  
**Actions performed:** Created this report and its JSON manifest only. No cleanup actions were executed.

## Decision Summary

| Classification | Candidates |
|---|---:|
| DELETE | 170 |
| ARCHIVE | 152 |
| KEEP | 31 |
| HUMAN_REVIEW | 27 |
| **Total exact candidate paths/cleanup units** | **380** |

The path-level manifest is [CLEANUP_CLASSIFICATION_MANIFEST.json](CLEANUP_CLASSIFICATION_MANIFEST.json). Each path is listed exactly once and inherits the rationale/reference/import/reproducibility/confidence details in its group. Directory paths such as cache roots are counted as one cleanup unit, not as each child file.

These labels are recommendations for a later approved pass, **not authorization to execute cleanup**. Nothing was deleted, moved, renamed, or overwritten. The research data, coefficients, and production code remain untouched.

## Worktree Status Changed Since PASS 1

Current Git status is on `phase13-memory` tracking `origin/phase13-memory` and now has 26 modified tracked paths, 17 deleted tracked docs, and 542 untracked paths. That is 43 tracked changes total, but unlike PASS 1, 17 of them are deletions. The earlier PASS 1 count (43 modified, 540 untracked) is stale.

The 17 deleted tracked docs have likely relocated counterparts under `docs/architecture/`, `docs/research/`, and `docs/specifications/`, but byte comparisons against Git `HEAD` showed all 17 pairs differ. They are **not exact duplicates** and cannot safely be called completed moves. They are `HUMAN_REVIEW`; this report does not restore them. The new counterparts are `KEEP` because they are untracked user work and contain differing content.

## Candidate Model Snapshots

There are 151 files named `backend/ai/candidate_model_<timestamp>.json`. All are 290 bytes and share SHA-256 `917161640cd08df2117133fec8238da246bbf07f77ef1b8b5e6884acd60a2858`.

The JSON contains model feature names, target names, estimator count, and random state; it does **not** contain fitted model weights. `ContinualTrainer` creates this timestamp filename using current UTC time and returns the path in memory. No static references to the 151 exact historical paths were found, and the inspected registry data does not name these snapshots. `DeployCandidate` can forward a candidate path during a live call, but no reader of the old files was found.

- **Authoritative canonical:** none found in code, registry, or manifest.
- **Preservation exemplar:** `backend/ai/candidate_model_20260723112406.json`, selected only as the earliest timestamped example. It is not an official canonical model.
- **Other 150 files:** classified `DELETE` candidates because their bytes are exact duplicates and their contents do not affect model execution or 17.x reproduction.
- **Timestamp/name meaning:** generated UTC creation time at one-second resolution; weak evidence of generation attempts, not a model version, experiment ID, or coefficient lineage. Removing a file loses its individual timestamp/path record.
- **Risk/confidence:** content redundancy is high-confidence; removal is not executed and external consumers cannot be disproved, so the later deletion action still needs the approved manifest and a final reference check.

All 151 exact paths and their distinct classifications appear in the manifest.

## Research Chain

Completed research evidence is classified `ARCHIVE`, meaning preserve it in a traceable historical location; it does not mean discard it. Reproduction scripts, input data, reports, and checkpoints should remain associated.

| Phase | Classification | Rationale |
|---|---|---|
| 17.13B | ARCHIVE | Frozen integration/coefficient evidence, implementation summaries, checklists, tests, and run results explain the MG integration lineage. |
| 17.13C | ARCHIVE | Manifest, preflight, frozen Run 1 result/report, execution log, checkpoint, and runner preserve generalization evidence. |
| 17.14A | ARCHIVE | Frozen instrumentation events, contract, safety analysis, decision gate, and runner establish instrumentation-only validation. |
| 17.15 | ARCHIVE | Frozen 2,400 events, report, forensic analysis, safety report, checkpoint, manifest, and validator are protected completed evidence. Preserve byte-for-byte. |
| 17.16A | ARCHIVE | Analysis script, results, summary, and checkpoint are descriptive mechanism-sensibility evidence; they do not prove predictive effectiveness. |
| 17.16B current | KEEP | `17_16B_ARCHITECTURE_AND_GROUND_TRUTH_ASSESSMENT.md` and `RESEARCH_CHECKPOINT_17_16B_DESIGN.json` establish that independent observed outcomes are missing and effectiveness analysis is blocked. |
| Earlier 17.16B proposal | ARCHIVE | The architecture-inspection/readiness docs and checkpoint contain invalid synthetic-ground-truth/fallback proposals. Retain as methodological history but do not follow them. |

The exact artifact and support-code paths are in the manifest. Current supporting implementation/data kept for interpretation includes the MG compatibility layer/config, simulation and transition engines, experience schema/service, tests, and their input corpora. Synthetic experience data remains synthetic; it is not ground truth.

Historical 17.0-17.12 result JSON, seeded benchmark data, and research reports are also classified `ARCHIVE`. Their age is not a deletion reason, and the generated benchmark data must not be described as observed outcomes.

## DELETE Candidates

The 170 DELETE-classified units are:

- **150** redundant timestamped candidate-model metadata copies listed exactly in the manifest. One earliest-timestamp exemplar is classified ARCHIVE; no authoritative canonical exists.
- **One-off/reproducible clutter:** `check_signature.py`, `temp_show_results.py`, `project_directory_listing.txt`.
- **Smoke output from one CLI run:** `experiment_runs/cli_smoke.csv`, `experiment_runs/cli_smoke.json`, and `experiment_runs/cli_smoke.jsonl`.
- **Regenerable caches:** `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, and the 11 exact `backend/**/__pycache__/` directories listed in the manifest.

No deletion was performed. The smoke outputs/cache directories are grouped only as one cleanup unit per exact directory/file path; deleting the virtual environment is not included.

## ARCHIVE Candidates

The 152 ARCHIVE candidates include:

- The single preservation exemplar for identical candidate metadata.
- Root research/debug runner wrappers that invoke retained phase scripts/tests.
- Saved pytest/analysis output and the phase-linked 17.13C/17.4C execution logs.
- Completed 17.13B, 17.13C, 17.14A, 17.15, and 17.16A artifacts and reproduction code.
- Earlier 17.0-17.12 result datasets, research reports, and seed inputs.
- Superseded 17.16B schema/readiness notes and PASS 1 cleanup audit files, retained as dated history. The readiness proposal is explicitly invalidated by the current blocked assessment.

## KEEP Candidates

The 31 KEEP paths include:

- Current 17.16B blocked assessment/checkpoint.
- Current nested architecture/research/specification docs that differ from deleted tracked versions.
- Core MG, transition, simulation, experience, state, data, and test paths needed to interpret or reproduce AURA behavior.

## HUMAN_REVIEW Candidates

The 27 HUMAN_REVIEW units are:

- The 17 tracked docs already deleted in the worktree. Their nested counterparts are not byte-identical; restoration or acceptance of these deletions is the owner's decision.
- `.venv/`, which may be the active Python environment.
- `AURA_v0.10_release.zip`, whose contents and provenance have not been audited.
- `.coverage`, currently tracked generated coverage data.
- `what each files are used for.md`, an informal note with uncertain freshness/ownership.
- `backend/services/state_history.py`, whose helper has no static references but may have external/dynamic use.
- Empty package markers and `database/aura_v1_schema.sql`; empty does not prove unnecessary, and package markers can affect import behavior.

The manifest includes the full exact path set and per-group details. No file is classified solely from a filename or age.

## Biggest Risks

1. **Current Git deletions:** 17 docs are already deleted in the worktree; nested replacements differ. Do not restore or remove without owner review.
2. **Research evidence loss:** deleting any 17.13B–17.16A data/report/checkpoint or its runner breaks the explanation/reproduction chain.
3. **Snapshot timestamp provenance:** 150 files have no unique content but do have distinct generation timestamps. Their deletion is low-risk for runtime but loses those timestamp records.
4. **Mislabelled outcomes:** historical/synthetic `state_after` fields are not independently observed ground truth; do not turn them into effectiveness evidence.
5. **Local environment/release artifacts:** `.venv` and the v0.10 ZIP may be needed outside tracked source context.
6. **Dirty, partly untracked repository:** the working tree is not a clean baseline; never bulk-clean using `git clean` or broad path patterns.

## Must Not Delete

- Frozen 17.15 events/report/forensic/safety/checkpoint and their reproducing validator/MG/simulation code.
- 17.16A script/results/summary/checkpoint and the frozen 17.15 input.
- Current 17.16B blocked assessment/checkpoint.
- 17.13B/17.13C/17.14A reports, checkpoints, results, seeds, runners, and tests needed to explain the completed chain.
- Current MG coefficients/configuration and production simulation code.
- The 17 deleted documentation paths until the user decides whether the current deletions are intended.
- The 542 untracked files or 26 modified tracked files as a whole; the untracked set includes source, tests, docs, and evidence.

## Ready for Cleanup?

**Ready for human review, not execution.** The classification manifest is path-specific and internally unique. A later cleanup pass should execute only exact DELETE paths the user approves; ARCHIVE should preserve checksums and provenance; HUMAN_REVIEW must remain untouched until decided. No classification in this report authorizes changing the Git worktree.
