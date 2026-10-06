# AURA Repository Cleanup Audit

**Audit date:** 2026-10-05  
**Mode:** Inventory and recommendations only  
**Research state:** 17.16B BLOCKED; no independent observed outcomes  
**Changes made:** This report and its JSON manifest only. No existing project file was deleted, moved, renamed, or modified.

## Executive Summary

AURA contains a substantial prototype, tests, historical research chain, generated experiment outputs, and a very dirty Git worktree. The correct immediate cleanup action is **none**: preserve the current state and review the manifest first.

Inventory snapshot:

- 782 non-cache/non-venv regular project files inventoried by area and path rules: 405 Python, 116 Markdown, 236 JSON, 13 TXT, and 12 other files.
- Git reports 257 tracked files, 43 modified tracked files, and 540 untracked files. The untracked set includes large portions of implementation, tests, research scripts, reports, and evidence; untracked does not mean disposable.
- 57,548 ignored files are present, dominated by `.venv` (56,139), `.mypy_cache` (991), and ignored `backend` cache files (405), with pytest/ruff caches and ignored root log/ZIP files making up the rest.
- The branch/status header is `phase13-memory...origin/phase13-memory`.
- Git internals are excluded from the project-file totals. Empty `frontend/` and `research/` directories have no files to classify.

The JSON manifest uses exact paths for protected exceptions and path-pattern groups for homogeneous inventories. Each group carries the required classification/status/recommendation/risk fields and a member count when available; more-specific rules override broad directory rules. Ignored tool/environment internals are represented as directory rollups, not tens of thousands of fabricated individual judgments.

## 1. Repository Overview

AURA is a Python 3.13+ prototype. The project README names `backend/main.py` as its basic entry point and `pytest backend/tests` as its test command. Packaging/tool settings live in `pyproject.toml`, with developer tools pinned in `requirements-dev.txt`. CI quality configuration is under `.github/workflows/quality.yml`.

The substantive implementation is under `backend/`: AI/reasoning, compatibility, config, consolidation, memory, models, planning, reports, services, and validation. `backend/experiments/` contains the versioned research runners, scripts, tests, and result artifacts. There is also a small root `experiments/` area with two experiment JSON outputs and a separate `experiment_runs/` smoke-run output directory. `docs/` contains architecture, specifications, ADRs, and research material; numerous phase-specific research documents also remain at repository root and under `backend/experiments/`.

The existing project has one root README, two experiment READMEs, and 116 Markdown files total. There is no one current index that clearly separates current architecture, frozen research evidence, historical research, and superseded planning notes.

## 2. Core AURA Files

| Responsibility | Important paths | Classification / recommendation |
|---|---|---|
| Entry/configuration | `backend/main.py`, `README.md`, `pyproject.toml`, `requirements-dev.txt`, `.github/workflows/quality.yml` | A/I. Keep; clarify runtime/quality commands in a later documentation pass. |
| State representation | `backend/models/user_state.py`, `backend/models/state_document.py`, `backend/models/simulated_state.py`, `backend/services/state_service.py`, `backend/services/state_diff.py` | A. Core state and persistence; high deletion risk. |
| Experience representation and ingestion | `backend/models/experience.py`, `backend/models/experience_log.py`, `backend/models/decision_outcome.py`, `backend/services/experience_service.py`, `backend/services/experience_processor.py`, `backend/services/experience_logger.py` | A/D. Core schemas/services plus logging contract; logger is test-driven and has no runtime call site found, but is not safe to classify obsolete. |
| Transition/base prediction | `backend/services/state_similarity.py`, `backend/services/transition_engine.py`, `backend/ai/transition_model.py`, `backend/ai/sequence_transition_model.py`, `backend/ai/model_configs.py` | A. Separate transition implementations serve different model paths; same-looking names are not duplicates. |
| Simulation/planning | `backend/services/simulation_engine.py`, `backend/services/digital_twin.py`, `backend/planning/`, `backend/services/beam_search_planner.py`, `backend/services/goal_plan_service.py` | A. Current simulation and planning path; high deletion risk. |
| MG mechanism | `backend/compatibility/mg_config.py`, `backend/compatibility/mg_compatibility.py` | A/B. Production integration and frozen MG implementation; preserve coefficients and code pending explicit authorization. |
| Evaluation/logging | `backend/services/prediction_error_evaluator.py`, `backend/services/closed_loop_validation.py`, `backend/services/experiment_recorder.py`, `backend/services/experiment_tracker.py`, `backend/services/experience_logger.py` | A/D. Used in evaluation/tests; `ExperimentTracker` is called by `goal_plan_service.py`. |
| Validation | `backend/validation/`, `backend/tests/`, `backend/experiments/test_*.py` | B/D/C. Distinguish current safety validation from historical research test harnesses; do not collapse by similar names. |
| Data | `backend/data/` | A/C/D/J depending on file. Includes active state/catalog/experience corpora, synthetic corpora, backups, and training data; provenance differs by file. Preserve pending data-owner review. |

The worktree has modifications in core state/simulation/retrieval/planning files. These are user changes and must not be reset or overwritten as part of cleanup.

## 3. Current and Historical Research Evidence

### Protected current research chain

These files form evidence or reproduction inputs and must be retained byte-for-byte unless the user separately authorizes a controlled correction. A future cleanup may archive them, but only with path mapping and checksums:

**17.13B/17.13C:**
- `RESEARCH_CHECKPOINT_17_13B_MG_INTEGRATION_VALIDATED.md`
- `EVIDENCE_PRESERVATION_17_13B.md`
- `RESEARCH_17_13_B_ENABLED_VERIFICATION.md`
- `RESEARCH_CHECKPOINT_17_13C_RUN1.md`
- `RESEARCH_PLAN_17_13C_SHADOW_VALIDATION.md`
- `17_13C_EXPERIMENT_MANIFEST.md`, pre-execution documents, `17_13C_RESULT_RUN1.json`, `17_13C_RESULT_RUN1.md`, `17_13C_EXECUTION_FINAL_REPORT.md`, and `17_13C_EXECUTION_LOG_RUN1.txt`
- `backend/experiments/results/research_17_13_b_*.json`, related `backend/experiments/research_17_13_b_*.json`, `backend/experiments/run_17_13_c_shadow_validation_run1.py`, and 17.13B verification/test scripts

**17.14A:**
- `17_14A_EXPERIMENT_MANIFEST.md`, `17_14A_OBSERVABILITY_CONTRACT.md`, pre-execution/verification/ready documents
- `17_14A_SHADOW_VALIDATION_EVENTS.json`, `17_14A_SHADOW_VALIDATION_REPORT.json`, `17_14A_SAFETY_ANALYSIS_RESULTS.json`, `17_14A_DECISION_GATE_RESULT.json`, verification-result JSON/MD
- `backend/validation/17_14a_shadow_validation.py`, `backend/validation/safety_analyzer.py`, `backend/validation/decision_gate.py`, and the supporting simulation/MG code as it existed for the run

**17.15:**
- `17_15_SHADOW_VALIDATION_EVENTS.json`
- `17_15_SHADOW_VALIDATION_REPORT.json`
- `17_15_FORENSIC_ANALYSIS_ROOT_CAUSE.md`
- `17_15_SAFETY_ANALYSIS_REPORT.md`
- `RESEARCH_CHECKPOINT_17_15_SAFETY_GATES_PASS.json`
- `17_15_EXPERIMENT_MANIFEST.md`, `17_15_PRE_EXECUTION_VERIFICATION.md`, `17_15_PRE_EXECUTION_SUMMARY.md`, `17_15_READY_FOR_EXECUTION.md`, `17_15_PLANNING_COMPLETE.md`, `17_15_PHASE_COMPLETE_SUMMARY.md`, `17_15_SHADOW_VALIDATION_COMPLETE.md`
- Reproduction inputs/code: `backend/validation/shadow_validator_17_15.py`, `backend/services/simulation_engine.py`, `backend/compatibility/mg_config.py`, `backend/compatibility/mg_compatibility.py`, relevant transition/experience data, dependencies, and test harnesses

**17.16A/17.16B:**
- `17_16A_BEHAVIORAL_ANALYSIS_RESULTS.json`, `17_16A_BEHAVIORAL_ANALYSIS_SUMMARY.md`, `RESEARCH_CHECKPOINT_17_16A_MECHANISM_SENSIBILITY.json`, `backend/validation/behavioral_analysis_17_16a.py`, and frozen 17.15 event input
- `17_16B_ARCHITECTURE_AND_GROUND_TRUTH_ASSESSMENT.md` and `RESEARCH_CHECKPOINT_17_16B_DESIGN.json` are the current blocked assessment

The files `17_16B_ARCHITECTURE_INSPECTION.md`, `17_16B_OUTCOME_GENERATION_READY.md`, and `RESEARCH_CHECKPOINT_17_16B_ARCHITECTURE_READY.json` are retained historical artifacts but **superseded for planning**: they incorrectly treated synthetic/unverified `state_after` data as available ground truth and proposed an invalid legacy-prediction fallback. Do not use them as the current status. No 17.16B effectiveness experiment should begin while blocked.

Earlier 17.0–17.12 result JSON, seed datasets, scripts, manifests, and reports in `backend/experiments/` are historical research evidence. Their age is not a deletion criterion. Preserve them with the generator/configuration needed to interpret the data.

## 4. Documentation Inventory and Clutter

### Documentation families

- **Root README and entry docs:** `README.md`, `experiments/README.md`, `backend/experiments/README.md`. All relevant to separate scopes; keep. The root README should eventually describe the current research status and distinguish executable app surfaces from research-only prototypes.
- **Phase documents at root:** `17_13*`, `17_14A*`, `17_15*`, `17_16*`, `RESEARCH_CHECKPOINT_*`, `RESEARCH_PLAN_*`, `EVIDENCE_PRESERVATION_*`, `PHASE_*`, and `RESEARCH_*`. Keep as historical evidence. Some pre-execution/ready/planning summaries overlap in purpose, but are not byte-identical and may preserve decisions made before execution. Archive only after a research index links each to its run/result.
- **Architecture and specifications under `docs/`:** current and historical architecture variants, ADRs, roadmap, state/experience, digital twin, execution, quality, and sprint specifications. Keep; mark superseded design docs rather than delete. The multiple `AURA_*ARCHITECTURE*` documents need an owner-designated canonical version.
- **Research docs under `docs/research/`, `docs/archive/`, and `backend/experiments/`:** historical findings and benchmark results. Keep. The archive directory is appropriate but not exhaustive; moving additional material needs link and reproduction updates.
- **17.15 report cluster:** `17_15_PHASE_COMPLETE_SUMMARY.md`, `17_15_SHADOW_VALIDATION_COMPLETE.md`, and `17_15_SAFETY_ANALYSIS_REPORT.md` overlap in summary but have distinct content and roles. Keep all for now; future consolidate navigation, not evidence.
- **17.16B conflicting documents:** current assessment/checkpoint supersede prior “architecture ready” docs. Keep all versions, label prior ones superseded in a future index.
- **`what each files are used for.md`:** informal inventory note; unknown freshness and unstructured. Human review; do not delete based on title.

A full Markdown path-pattern group is in the manifest. The 116 Markdown files fall into root phase/research artifacts, `docs/**`, `backend/experiments/**`, and the three READMEs. Recommendation is keep/archive by research phase, not merge or delete in place.

## 5. Duplicate and Redundant Files

### Exact duplicates found

A content-hash scan found two notable identical-content groups outside caches:

1. **151 files** matching `backend/ai/candidate_model_*.json` are byte-identical. They contain only `SequenceTransitionModel.to_dict()` metadata (`feature_names`, `target_names`, `n_estimators`, `random_state`), not learned model weights or training data. `ContinualTrainer` writes timestamp-named JSON snapshots. No code reader for those individual snapshots was found; `DeployCandidate` can pass through a `model_path`, so deletion risk remains medium. Recommendation: preserve/hold for review; if approved later, archive one representative plus an index/checksum and remove duplicates only after confirming no external consumer.
2. **Five zero-byte files** (`backend/__init__.py`, `backend/compatibility/__init__.py`, `backend/experiments/__init__.py`, `backend/services/__init__.py`, `database/aura_v1_schema.sql`) share the empty-file hash. Empty Python package markers can be intentional; the SQL schema being empty is an apparent incomplete artifact. Do not delete; review package/import compatibility and schema intent.

### Similar names, not safe duplicates

- `README.md` appears at root, `experiments/`, and `backend/experiments/`; each has a different scope.
- `experience_replay.py` exists in `backend/ai/` and `backend/services/`; different types/roles and separate usages/tests.
- `state_similarity.py` exists in AI and services; distinct model/retrieval responsibilities.
- `transition_model.py` exists in AI and planning; distinct implementations.
- `planner_config.py` exists in config and services; inspect imports before consolidation.
- Two `research_17_13_b_enabled_verification.json` files exist in `backend/experiments/` and its `results/`; hash comparison says they differ. Preserve both until their generation/provenance is reconciled.
- `experiment.json` occurs in two root experiment directories; they are separate runs.
- Benchmark docs with `_v1` suffix are not byte-identical to their unsuffixed counterparts.

No validation script should be removed solely because it resembles another phase's runner. 17.14A, generic `shadow_validator.py`, and 17.15 have different run parameters and research roles.

## 6. Temporary and Generated Material

Potential cleanup candidates, **not safe to delete in this checkout**:

- 151 repeated timestamped `backend/ai/candidate_model_*.json` metadata snapshots (untracked/generated; archive/review first).
- Root debugging/one-off scripts: `check_signature.py`, `debug_seed_789.py`, `temp_show_results.py`, `run_phase4_test.py`, `run_phase4_fixed.py`, `run_enabled_verification.py`, `run_17_2_a_tests.py`, `run_17_4_a.py`, `run_17_4_b.py`, `run_17_4_c.py`, `test_import.py`, `test_reload.py`, `test_17_13_b_basic.py`, plus tracked `tmp_verify_sprint6.py`. Several are standalone and have no import references; some reproduce older research/debugging. Archive after identifying ownership and purpose.
- `experiment_runs/cli_smoke.{json,csv,jsonl}`: generated smoke-run data, untracked. Keep until run is confirmed disposable.
- Root `pytest_*.txt`, `test_results.txt`, `test_17_5_a.txt`, `analysis_output.txt`, `first_fail.txt`, `kr_out*.txt`, and `project_directory_listing.txt`: likely command/debug output. `17_13C_EXECUTION_LOG_RUN1.txt` is research evidence and must not be confused with disposable logs.
- `AURA_v0.10_release.zip`: ignored by `*.zip`, likely release snapshot. Human decision; do not remove or extract over current tree.
- `.coverage` is tracked even though it is generated test output; `.gitignore` currently does not ignore it. Fixing tracking/ignore status requires an approved Git change.
- `.venv/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, ignored logs, and any ignored bytecode are rebuildable/generated in general, but the virtual environment may contain the user's active Python setup. Do not remove them without approval.

## 7. Dead-Code Candidates (No Automatic Removal)

| Candidate | References/imports/tests | Assessment and deletion risk |
|---|---|---|
| `backend/services/state_history.py` (`build_state_history`) | Workspace search found only the function definition; no import or test usage. | Strong dead-code candidate, but low-confidence purpose/history; medium risk. Human review before archive/removal. |
| Root helpers listed above | Direct executable scripts; no references from other source files found for most. `debug_seed_789.py` imports a historical research runner; phase runner helpers invoke specific tests. | Not runtime imports, but may be ad-hoc reproducibility aids. Archive/review; medium research-history risk. |
| `backend/validation/shadow_validator.py` | Standalone runner; similar purpose to the phase-specific 17.14A/17.15 runners, but independently executable. | Possible superseded generic runner, not proven dead. Preserve until output/artifact links are known; high evidence risk. |
| `backend/services/experience_logger.py` | Repository call sites are tests; no production call site found. Test and integration coverage exists and it persists caller-supplied `actual_state`. | Potentially a feature/API not yet wired into production, not dead. Keep pending product decision; medium risk. |
| `backend/services/snapshot_validation.py` | Called by `backend/tests/test_simulated_state.py`; no production caller found. | Test-supported contract utility; keep unless snapshot-chain feature is retired. Medium risk. |
| `backend/validation/safety_analyzer.py`, `decision_gate.py` | Standalone `__main__` run paths; tied to 17.14A artifacts, not general imports. | Research reproduction tools, not dead; preserve. High evidence risk. |
| `backend/services/experiment_tracker.py` | Imported and called by `backend/services/goal_plan_service.py`; also tested. | Active; do not label dead. |
| `backend/ai/experience_replay.py` vs service replay | AI buffer imported by continual learning and tests; service replay separately tested. | Distinct implementations; do not consolidate by filename. |

These are static reference findings, not a proof of no dynamic imports or external scripts.

## 8. Git Status and Ignore Audit

Git status is not clean. The following **43 tracked paths are modified** and must be preserved as user work:

`backend/ai/evaluate_retrieval.py`, `backend/ai/experience_reasoner.py`, `backend/ai/experience_retriever.py`, `backend/ai/integration_coverage.json`, `backend/ai/meta_learning.json`, `backend/ai/meta_reasoner.py`, `backend/ai/model_registry.json`, `backend/ai/policy_registry.json`, `backend/ai/reasoning_registry.json`, `backend/ai/research_registry.json`, `backend/ai/system_registry.json`, `backend/data/experience_dataset.json`, `backend/models/__init__.py`, `backend/models/user_state.py`, `backend/services/beam_search_planner.py`, `backend/services/digital_twin.py`, `backend/services/goal_plan_service.py`, `backend/services/goal_planner.py`, `backend/services/simulation_engine.py`, `backend/services/state_diff.py`, `backend/tests/test_beam_search.py`, `backend/tests/test_goal_plan_service.py`, `backend/tests/test_retrieval_planner.py`, `backend/tests/test_simulation_engine.py`, `docs/AURA_ARCHITECTURE_V1.md`, `docs/AURA_ARCHITECTURE_V2.md`, `docs/AURA_DOCUMENTATION.md`, `docs/AURA_SYSTEM_ARCHITECTURE.md`, `docs/MILESTONE_SPRINT9_1.md`, `docs/PLANNING_ARCHITECTURE_V1.md`, `docs/POLICY_BENCHMARK_v1.md`, `docs/architecture.md`, `docs/archive/META_REASONING_BENCHMARK.md`, `docs/archive/META_REASONING_BENCHMARK_v1.md`, `docs/archive/POLICY_DASHBOARD.md`, `docs/archive/PROJECT_METRICS.md`, `docs/archive/RETRIEVAL_BENCHMARK.md`, `docs/archive/SPRINT_11_REVIEW.md`, `docs/milestone_sprint5.md`, `docs/milestone_sprint8.md`, `docs/model_benchmark_v1.md`, `docs/research_notes.md`, `experiments/ablation_seed_7/experiment.json`.

There are **540 untracked files**. Many are complete backend modules/tests/research artifacts, 17.13C/17.14A/17.15 records, and 17.16 assessment files. Treat the entire untracked set as human-owned until explicitly reviewed; do not stage, move, or delete it as cleanup.

`.gitignore` currently ignores `__pycache__/`, bytecode, `*.log`, `.pytest_cache/`, `.venv/`, `.env`, `*.sqlite3`, and `*.zip`. It does not ignore `.coverage`, `.mypy_cache/`, or `.ruff_cache/`, although those cache directories/files currently appear ignored by global/editor rules. Confirm effective ignore source before changing `.gitignore`. Candidate-model JSON and experiment-run outputs are not ignored, so they accumulate as untracked files.

## 9. Files That Must Not Be Deleted or Modified

At minimum, preserve the protected 17.13B–17.16B artifacts listed above and their reproducing code/data. More generally, no file is approved for deletion during this audit. In particular, preserve:

- Frozen 17.15 event/report/forensic/safety/checkpoint files and the validator, MG config/layer, simulation engine, and inputs needed to interpret/reproduce the run.
- All 17.16A results, summary, checkpoint, analysis script, and frozen input.
- Current 17.16B blocked assessment/checkpoint; preserve prior superseded readiness documents as history.
- 17.13B/17.13C and 17.14A manifests, parameters/coefficients, test scripts, execution logs, datasets, reports, and results.
- Historical research result JSON, seed datasets, and scripts under `backend/experiments/`.
- All 43 modified tracked files and all 540 untracked files until user review.
- `backend/data/` files, backup snapshots, model pickle files, and release ZIP pending data/model-owner confirmation.

Reproduction also depends on the Python version/dependencies, deterministic seeds/configs, and the exact source/data snapshot. The current Git dirt means a clean source revision cannot be reconstructed from branch state alone.

## 10. Safe-to-Delete / Safe-to-Archive / Human Approval

**Safe to delete now:** None.

**Potential archive candidates after explicit review:** one-off test/debug scripts, command output logs, smoke-run artifacts, exact duplicate candidate metadata snapshots, and superseded planning/ready summaries. Archive with checksums and provenance; do not archive away raw research inputs or phase-specific runners.

**Human approval required:** all tracked modifications, all untracked files, release ZIP, environment/cache removal, candidate-model snapshots, data and model files, empty/incomplete schema placeholders, the old readiness docs, and any move/rename that affects scripts or reproduction links.

A file being ignored, generated, unreferenced by static search, old, or byte-identical does not make it safe to delete in this dirty checkout.

## 11. Recommended Final Structure

Do not reorganize automatically. A compatible future target is:

```text
AURA/
  README.md
  pyproject.toml
  requirements-dev.txt
  .github/
  backend/
    ai/ compatibility/ config/ consolidation/ memory/
    models/ planning/ reports/ services/ validation/ tests/
    data/
    experiments/            # runners and reproducibility code only
  research/
    17.0-17.12/             # preserved historical chain
    17.13B/ 17.13C/ 17.14A/ 17.15/
    17.16A/ 17.16B/         # blocked design kept separate from results
  docs/
    architecture/ adr/ specifications/ current/ archive/
  database/
  experiments/              # decide whether this existing output area stays
  experiment_runs/           # generated, gitignored run outputs
```

Keep research scripts close to their evidence until path dependencies are mapped. The top-level `research/` and `frontend/` directories are currently empty; their existence does not imply current implementation. Before moving anything, add a research index and a path/checksum manifest, update hard-coded paths, and verify all reproduction commands.

## 12. Recommended Cleanup Sequence

1. **Freeze the audit snapshot:** save this report/manifest, capture `git diff`, untracked path list, and checksums; do not reset or stage work.
2. **Owner triage:** review the 43 modified paths and 540 untracked paths; mark files as active, evidence, generated, or personal scratch.
3. **Evidence map:** assign each research artifact an experiment ID, input/script/config/result links, provenance, and checksum. Keep superseded drafts labeled, not removed.
4. **Generated outputs:** identify owner/rebuildability for candidate model snapshots, smoke outputs, logs, `.coverage`, caches, and release ZIP. Archive uncertain outputs before changing ignore rules.
5. **Documentation index:** designate current architecture docs; link each research phase manifest/result; label stale readiness text and the invalid 17.16B proposal as superseded.
6. **Small approved archive/move batch:** do one phase at a time, retain a path migration map, update scripts, then reproduce that phase's checks.
7. **Deletion only in a separately approved task:** verify backup/checksum and no runtime, test, research, external, or user dependency. Do not infer approval from this audit.
8. **Final validation:** run focused tests/reproduction, inspect Git status, and confirm the frozen artifacts/checksums remain unchanged.

## 13. Audit Boundary

This audit did not run the full test suite, remove generated files, inspect `.git` internals, or inspect each of the 57,548 ignored environment/cache files individually. Those files are included as ignored directory rollups with counts. Static usage searches cannot prove absence of dynamic/external references. The manifest documents these limits and uses broad path rules where a per-file judgment would be false precision.
