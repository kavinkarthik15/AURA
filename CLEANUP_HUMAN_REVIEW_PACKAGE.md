# AURA Cleanup: Final Human-Review Package

**Prepared:** 2026-10-06  
**Purpose:** Decision preparation only. This package does not authorize cleanup. No existing project file was changed, restored, moved, deleted, or overwritten. The only new files requested for this pass are this package and `CLEANUP_PROPOSED_ACTIONS.json`.

## 1. Executive summary

The PASS 2 manifest represents 380 unique candidate paths exactly once: 170 `DELETE`, 152 `ARCHIVE`, 31 `KEEP`, and 27 `HUMAN_REVIEW`.

The 150 candidate-model files proposed for duplicate removal are byte-for-byte identical JSON metadata snapshots. They are not fitted model weights. The earliest snapshot, `backend/ai/candidate_model_20260723112406.json`, is the proposed retained exemplar. The other 150 remain recommendations only.

The 17 deleted tracked documentation files have same-title counterparts at nested `docs/` paths. Comparing `HEAD` text with current UTF-8 counterparts found identical nonblank lines, headings, claims, and implementation descriptions for all 17. Their relationship is `CLEAN_RELOCATION`; approve old-path deletion only after checking any external links and the unresolved worktree state.

The worktree currently has **26 modified tracked files, 17 deleted tracked files, 544 untracked files, and 57,548 ignored files**. Multiple modified files are active backend code, tests, research registries/data, and an experiment manifest. Cleanup execution is therefore **BLOCKED**. This document is not permission to execute any action.

Scientific status is unchanged: **17.16B = BLOCKED** because there is no verified independent observed-outcome cohort suitable for effectiveness evaluation. Synthetic experiences, simulated states, legacy predictions, and hard-coded `actual_state` values are not independent ground truth. The 17.16B assessment and design checkpoint remain protected.

## 2. Candidate-model duplicate decision

| Check | Result |
|---|---|
| Total timestamped candidate-model JSON files | 151 |
| Exact duplicate candidates | 150 |
| Proposed retained archival exemplar | `backend/ai/candidate_model_20260723112406.json` |
| Duplicate filename timestamp range | `20260723112849` through `20260813043640` (timestamp filenames are generation seconds; gaps are present) |
| Size and common SHA-256 | 290 bytes each; `917161640cd08df2117133fec8238da246bbf07f77ef6b8b5e6884acd60a2858` |
| Identical payload | Yes; all 151 files have the same bytes and the same parsed JSON values |
| Payload fields | `feature_names`, `target_names`, `n_estimators`, `random_state` |
| Trained weights | None. These are configuration/metadata snapshots, not fitted model artifacts. |
| Exact historical filename references | No literal timestamped filename reference was found in source/docs/tests. The trainer creates names dynamically; its returned path is passed in memory. |
| Code impact of removing duplicates | No in-repository loader or consumer of those exact historical paths was found. The registry records model records, not these snapshot paths. |
| Research reproduction impact | No effect on model execution or reproduction of the reviewed research conclusions; no weights or distinct payloads are lost. |
| Residual risk | Each removed filename preserves a generation-time breadcrumb. External tooling or copies outside this repository cannot be ruled out. |
| Recommendation | **APPROVE_DELETE** for the 150 byte-identical copies, subject to owner approval and a future clean-worktree cleanup pass. Keep the exemplar as **ARCHIVE**. |

This recommendation concerns duplication only. It does not claim the retained exemplar is an application-designated canonical model.

## 3. Remaining non-snapshot DELETE candidates

Each item below was reviewed separately. The six smoke-run artifacts are each listed independently; cache directories are also separate cleanup units. Static reference checks found no in-repository consumers for these exact generated paths. Python scripts are manually runnable, but are not imported or called by the application/test suite.

| Exact path | Status / type | Purpose and DELETE rationale | Reproducible / referenced / unique | What deletion loses; risk | Confidence; recommendation |
|---|---|---|---|---|---|
| `check_signature.py` | Untracked; Python script | One-off `inspect.signature` print helper for `SimulationEngine.simulate_action`; not a maintained test or application entry point. | Re-runnable; no path consumer; no unique evidence. | Loses this convenience script; low risk. | Medium; **APPROVE_DELETE** |
| `temp_show_results.py` | Untracked; Python script | One-off display script reading the retained 17.2A mechanism result JSON; not an application entry point. | Re-runnable while result JSON exists; no path consumer; no unique evidence. | Loses a presentation helper, not the underlying result; low risk. | Medium; **APPROVE_DELETE** |
| `project_directory_listing.txt` | Untracked; text inventory (about 4.6 MB) | Generated directory listing, redundant with the current filesystem and stale by construction. | Reproducible; no consumer; no unique evidence established. | Loses a point-in-time file listing; low risk. | Medium; **APPROVE_DELETE** |
| `experiment_runs/cli_smoke.csv` | Untracked; CSV | Output from a reproducible CLI smoke run, not a research outcome. | Reproducible; no consumer; no unique evidence. | Loses one smoke-run rendering; low risk. | Medium; **APPROVE_DELETE** |
| `experiment_runs/cli_smoke.json` | Untracked; JSON | Same smoke run represented as JSON. | Reproducible; no consumer; no unique evidence. | Loses one smoke-run rendering; low risk. | Medium; **APPROVE_DELETE** |
| `experiment_runs/cli_smoke.jsonl` | Untracked; JSONL | Same smoke run represented as JSONL. | Reproducible; no consumer; no unique evidence. | Loses one smoke-run rendering; low risk. | Medium; **APPROVE_DELETE** |
| `.mypy_cache/` | Ignored; cache directory | Regenerable type-check cache. | Regenerable; not an input; not unique. | Cache warm-up time only; very low risk. | High; **APPROVE_DELETE** |
| `.pytest_cache/` | Ignored; cache directory | Regenerable pytest cache. | Regenerable; not an input; not unique. | Cache warm-up time only; very low risk. | High; **APPROVE_DELETE** |
| `.ruff_cache/` | Ignored; cache directory | Regenerable lint cache. | Regenerable; not an input; not unique. | Cache warm-up time only; very low risk. | High; **APPROVE_DELETE** |
| `backend/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/ai/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/compatibility/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/config/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/consolidation/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/experiments/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/memory/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/models/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/planning/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/services/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |
| `backend/tests/__pycache__/` | Ignored; bytecode-cache directory | Regenerable Python bytecode. | Regenerable; not an input; not unique. | Recompilation only; very low risk. | High; **APPROVE_DELETE** |

## 4. The 17 tracked documentation deletions

The old paths are currently tracked deletions (`D`); each is a Markdown file with a same-title counterpart under a nested documentation directory. UTF-8 content comparison found **no heading-only-in-old/new, information-only-in-old/new, research-claim change, or implementation-detail change** for any pair. For each pair, no unique content is lost, there is no effect on code execution or current research reproduction, and no protected current research result is implicated. Deletion risk is broken inbound links to the old path; retaining/restoring an old path would create a duplicate/stale alternative beside the identical nested document. Line endings/serialization may differ; semantic text and headings match. Inbound references to legacy paths should still be checked before any future cleanup execution.

| Original tracked path (currently deleted) | Current counterpart | Content/semantic findings | Relationship | Recommendation |
|---|---|---|---|---|
| `docs/AURA_ARCHITECTURE_V1.md` | `docs/architecture/AURA_ARCHITECTURE_V1.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/AURA_ARCHITECTURE_V2.md` | `docs/architecture/AURA_ARCHITECTURE_V2.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/AURA_DOCUMENTATION.md` | `docs/architecture/AURA_DOCUMENTATION.md` | All 24 section headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/AURA_SYSTEM_ARCHITECTURE.md` | `docs/architecture/AURA_SYSTEM_ARCHITECTURE.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/MILESTONE_SPRINT9_1.md` | `docs/specifications/MILESTONE_SPRINT9_1.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/PLANNING_ARCHITECTURE_V1.md` | `docs/research/PLANNING_ARCHITECTURE_V1.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/POLICY_BENCHMARK_v1.md` | `docs/research/POLICY_BENCHMARK_v1.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/archive/META_REASONING_BENCHMARK.md` | `docs/research/META_REASONING_BENCHMARK.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/archive/META_REASONING_BENCHMARK_v1.md` | `docs/research/META_REASONING_BENCHMARK_v1.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/archive/POLICY_DASHBOARD.md` | `docs/research/POLICY_DASHBOARD.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/archive/PROJECT_METRICS.md` | `docs/research/PROJECT_METRICS.md` | Headings and substantive lines identical, including metric values; no changed research claims. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/archive/RETRIEVAL_BENCHMARK.md` | `docs/research/RETRIEVAL_BENCHMARK.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/archive/SPRINT_11_REVIEW.md` | `docs/research/SPRINT_11_REVIEW.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/milestone_sprint5.md` | `docs/specifications/milestone_sprint5.md` | Headings and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/milestone_sprint8.md` | `docs/specifications/milestone_sprint8.md` | Headings and substantive lines identical, including reported metrics; no changed research claims. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/model_benchmark_v1.md` | `docs/research/model_benchmark_v1.md` | Headings and substantive lines identical, including reported metrics; no changed research claims. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |
| `docs/research_notes.md` | `docs/research/research_notes.md` | Heading and substantive lines identical; no unique old/new information or changed claims/details. | A. `CLEAN_RELOCATION` | `APPROVE_OLD_PATH_DELETION` |

## 5. Remaining HUMAN_REVIEW items

### Deleted tracked documentation

The 17 paths above account for 17 of 27 `HUMAN_REVIEW` candidates. They are not independently safe to restore over the current nested counterparts; the content comparison supports old-path deletion. Recommendation per item is `APPROVE_OLD_PATH_DELETION`, with owner approval and a link check before any future execution. They are documentation, not imported or executed. Current deletion status is a user worktree change and must remain untouched in this pass.

### Other 10 candidates

| Exact path | Current Git status / type | References or execution | Uniqueness and research/reproduction relevance | Risks | Recommended action |
|---|---|---|---|---|---|
| `.venv/` | Ignored; local Python environment directory. | Not a repository input path; may be the active environment. | Environment state may not be reconstructible exactly; potentially relevant to running tests/reproductions. | Delete risk: lose selected interpreter/dependency state. Retain risk: consumes local disk and is ignored clutter. | **KEEP** |
| `AURA_v0.10_release.zip` | Ignored; ZIP release archive (650,958 bytes). | No repository path consumer established; archive contents/provenance were not inspected. | Potentially unique release artifact; reproduction relevance unknown. | Delete risk: lose a release snapshot. Retain risk: root clutter and unclear provenance. | **OWNER_DECISION** |
| `.coverage` | Tracked and clean; coverage data file (69,632 bytes). | Tool output, not application input. | Unique test-run coverage state, not research evidence. | Delete risk: lose current coverage measurement. Retain risk: stale binary in repository. | **OWNER_DECISION** |
| `what each files are used for.md` | Untracked; Markdown note (451 bytes). | No code execution; no links established. | Contains unique informal project-structure context; not research evidence. | Delete risk: lose the only copy of this note. Retain risk: informal/possibly stale root documentation. | **KEEP** |
| `backend/services/state_history.py` | Tracked and clean; Python source (394 bytes). | No static callers beyond its own definition found; not imported/executed by known code paths. | Unique helper source, not research evidence; reproducibility impact low. | Delete risk: remove an available API/helper or future integration point. Retain risk: dead/unreferenced source surface. | **KEEP** |
| `backend/__init__.py` | Tracked and clean; empty Python package marker. | Participates in package/import semantics. | Not research evidence; relevant to import/package behavior. | Delete risk: alter package discovery/import behavior. Retain risk: negligible. | **KEEP** |
| `backend/compatibility/__init__.py` | Untracked; empty Python package marker. | Participates in package/import semantics. | Not research evidence; relevant to import/package behavior. | Delete risk: alter package discovery/import behavior. Retain risk: negligible. | **KEEP** |
| `backend/experiments/__init__.py` | Untracked; empty Python package marker. | Participates in package/import semantics. | Not evidence itself; may affect experiment/test package discovery. | Delete risk: alter package/test discovery. Retain risk: negligible. | **KEEP** |
| `backend/services/__init__.py` | Tracked and clean; empty Python package marker. | Participates in package/import semantics. | Not research evidence; relevant to import/package behavior. | Delete risk: alter package discovery/import behavior. Retain risk: negligible. | **KEEP** |
| `database/aura_v1_schema.sql` | Tracked and clean; empty SQL file. | No SQL consumer established. | No schema content to reproduce, but intent is ambiguous; not research evidence. | Delete risk: discard a reserved/unfinished schema path. Retain risk: misleading empty schema artifact. | **OWNER_DECISION** |

The release ZIP was deliberately not unpacked or modified. The `.coverage` file was not deleted or regenerated. The entire `.venv/` remains untouched.

## 6. Root-level clutter review

Exact per-path proposed actions and destinations are recorded in `CLEANUP_PROPOSED_ACTIONS.json`. Root content should be treated by role, not by extension or untracked status.

| Destination decision | Root-level content |
|---|---|
| **A. Remain in root** | `README.md`, `pyproject.toml`, `requirements-dev.txt`, `.gitignore`; current phase evidence/checkpoints that are explicitly protected must remain at their present paths in this pass. Keep `.venv/` provisionally pending environment-owner review. |
| **B. Research, later and only for unprotected material** | Historical reports/manifests/results tied to 17.2A, 17.4C, 17.5A, 17.8A, and 17.8C can be grouped under phase folders with `reports/`, `results/`, `scripts/`, and `logs/`. Current 17.13B, 17.13C, 17.14A, 17.15, 17.16A, and 17.16B evidence is protected and is **not** proposed for movement. |
| **C. `experiments/`** | Experiment inputs/runs belong here only when they are active reproducible experiments. Existing `experiments/ablation_seed_7/experiment.json` is tracked and modified; do not move or alter it. The disposable CLI smoke outputs are separately proposed for deletion, not archival. |
| **D. `docs/`** | Architecture material belongs under `docs/architecture/`, specifications under `docs/specifications/`, and legacy benchmarks/research notes under `docs/research/`. All 17 existing nested counterparts are text-equivalent to the deleted old paths. |
| **E. `archive/`** | Historical one-off logs, test outputs, obsolete run scripts, and prior cleanup reports may be archived after review. Do not use archival as a way to relocate or reinterpret protected research evidence. |
| **F. Delete, after approval** | Generated cache directories, duplicate candidate-model snapshots, the generated directory listing, one-off signature/display helpers, and the three reproducible CLI smoke output formats. The detailed path-by-path entries are in the JSON package. |

Additional root-level files not included in the 380-path PASS 2 manifest were explicitly reviewed and added to the proposed-actions JSON: `17_14A_SHADOW_VALIDATION_COMPLETE.md` is `NO_ACTION` as protected evidence; `PHASE_17_4C_COMPLETION_SUMMARY.md`, `PHASE_17_5A_COMPLETION_SUMMARY.md`, `PHASE_17_5A_QUICK_REFERENCE.md`, `RESEARCH_17_2_A_MECHANISM_ANALYSIS.md`, `RESEARCH_17_8_A_PREDICTIVE_STATE_DIMENSIONS.md`, `RESEARCH_17_8_C_MINIMAL_STRUCTURE.md`, and `RESEARCH_BASELINE_v0.10.md` are proposed `ARCHIVE` destinations under their historical research phases. These seven are not proposed for deletion. Root-level cleanup/audit manifests and reports remain available during this decision process.

Recommended eventual research layout (proposal only):

```text
research/
  17.13B/
    reports/  results/  checkpoints/  scripts/  manifests/  logs/
  17.13C/
    reports/  results/  checkpoints/  scripts/  manifests/  logs/
  17.14A/
    reports/  results/  checkpoints/  scripts/  manifests/  logs/
  17.15/
    reports/  results/  checkpoints/  scripts/  manifests/  logs/
  17.16A/
    reports/  results/  checkpoints/  scripts/  manifests/  logs/
  17.16B/
    reports/  results/  checkpoints/  scripts/  manifests/  logs/
```

This structure is **not** permission to move any file. Specifically, do not reorganize protected evidence or change the blocked scientific status of 17.16B.

## 7. Current Git/worktree risk

Read-only Git inspection reports:

- **Tracked modified (26):** `backend/ai/evaluate_retrieval.py`, `backend/ai/experience_reasoner.py`, `backend/ai/experience_retriever.py`, `backend/ai/integration_coverage.json`, `backend/ai/meta_learning.json`, `backend/ai/meta_reasoner.py`, `backend/ai/model_registry.json`, `backend/ai/policy_registry.json`, `backend/ai/reasoning_registry.json`, `backend/ai/research_registry.json`, `backend/ai/system_registry.json`, `backend/data/experience_dataset.json`, `backend/models/__init__.py`, `backend/models/user_state.py`, `backend/services/beam_search_planner.py`, `backend/services/digital_twin.py`, `backend/services/goal_plan_service.py`, `backend/services/goal_planner.py`, `backend/services/simulation_engine.py`, `backend/services/state_diff.py`, `backend/tests/test_beam_search.py`, `backend/tests/test_goal_plan_service.py`, `backend/tests/test_retrieval_planner.py`, `backend/tests/test_simulation_engine.py`, `docs/architecture.md`, and `experiments/ablation_seed_7/experiment.json`.
- **Tracked deleted (17):** exactly the old documentation paths in section 4.
- **Untracked (546):** includes substantial research evidence, scripts, reports, result data, tests, cleanup audits/manifests, and the two new decision package files. Untracked does not mean disposable.
- **Ignored (57,548):** principally `.venv` (about 56,135 entries), `.mypy_cache` (991), backend bytecode/cache files (405), pytest/ruff caches, plus ignored root `.coverage`-adjacent/ZIP/log artifacts. `.coverage` itself is tracked and clean.

The modified implementation, tests, registries, dataset, and experiment file do not appear to be disposable cleanup outputs; their intent is unresolved and they are unrelated to executing cleanup. They must not be overwritten. The 17 deleted docs are already user-worktree deletions and must not be restored or otherwise altered in this pass.

**Decision: cleanup execution is BLOCKED.** The working tree contains unresolved changes and far more untracked material than the cleanup candidate set. No delete/archive/move/restore/commit is safe to execute as part of this task.

## 8. Proposed repository organization

1. Keep root-level project entry points and tooling configuration in place.
2. Keep documentation organized under the existing `docs/architecture/`, `docs/specifications/`, and `docs/research/` areas. The 17 old deleted doc paths need no content merge; check links before accepting their already-present path changes.
3. Only after owner review, place non-protected historical research by phase under `research/<phase>/{reports,results,checkpoints,scripts,manifests,logs}/`.
4. Leave protected 17.13B/17.13C/17.14A/17.15/17.16A evidence untouched at current paths. Preserve `17_16B_ARCHITECTURE_AND_GROUND_TRUTH_ASSESSMENT.md` and `RESEARCH_CHECKPOINT_17_16B_DESIGN.json` untouched.
5. Keep the `.venv/`, release ZIP, `.coverage`, and empty SQL schema pending their owners' decisions.
6. Remove generated caches/smoke outputs/duplicate snapshots only during a separate, explicitly approved cleanup with a clean worktree and exact-path review.

## 9. Proposed exact cleanup actions

`CLEANUP_PROPOSED_ACTIONS.json` contains one object for each of the 380 manifest candidate paths plus the eight additional unclassified root-level research files above, with `path`, `current_classification`, `proposed_action`, `destination_if_applicable`, `reason`, `confidence`, `risk`, and `requires_owner_approval`.

Proposals are not executed. `ARCHIVE` destinations are suggestions only and do not authorize moving files. Protected research paths use `NO_ACTION`; the 17 relocated documentation paths propose old-path `DELETE` only because their current counterparts are text-identical. Human-review items with an unresolved owner decision use `NO_ACTION` in JSON and are explicitly marked `OWNER_DECISION` in this package.

## 10. Items requiring repository-owner decision

- Resolve the dirty worktree and confirm the 26 modified tracked files and 17 existing tracked deletions are intentional before any cleanup operation.
- Approve or reject deletion of the 150 duplicate candidate-model metadata snapshots after considering any external consumers of timestamp filenames.
- Confirm inbound links to the 17 relocated documentation paths before accepting old-path deletion.
- Decide whether to retain the ignored release ZIP and whether it is an authoritative/reproducible release artifact.
- Decide whether the tracked `.coverage` file should remain versioned, be archived, or be removed in a separate authorized change.
- Decide the intended role of the empty `database/aura_v1_schema.sql`.
- Keep the environment and note decisions conservative until the environment owner confirms `.venv/` and the informal note are disposable.
- Do not weaken or revise the 17.16B blocked status absent a verified independent observed-outcome cohort. Synthetic experiences, simulated states, legacy predictions, and hard-coded `actual_state` values are not ground truth.

### Decision totals

- `APPROVE_DELETE`: 187 (150 duplicate snapshots, 20 remaining non-snapshot DELETE candidates, and 17 cleanly relocated old documentation paths).
- Proposed `ARCHIVE`/`MOVE`: 93 archival candidates, including the seven additional historical root research files; protected phase evidence is `NO_ACTION`, not a move.
- `KEEP`: 38 (31 manifest KEEP candidates plus 7 non-document HUMAN_REVIEW candidates recommended to keep provisionally).
- `RESTORE`/`MERGE`: 0.
- Unresolved `OWNER_DECISION`: 3.
- Cleanup execution: **BLOCKED**.
