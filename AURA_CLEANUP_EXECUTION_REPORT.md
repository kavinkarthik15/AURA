# AURA Cleanup Execution Report

**Execution date:** 2026-10-06  
**Branch:** `pre-cleanup-snapshot`  
**Mode:** Authorized cleanup, stopped at first post-move path/reference break  
**Commit/push:** No cleanup commit was created; nothing was pushed.

## 1. Recovery checkpoint

- Recovery branch exists: `pre-cleanup-snapshot`.
- Verified recovery commit: `b5c81b0444c73c98915c8734044e19ddc128a010` (`chore: pre-cleanup repository safety snapshot`).
- Previous HEAD: `f98c99ab738358a6b51888e238f856d96afa50ba`.
- At the start of cleanup, the current branch was the recovery branch, the specified commit existed, the worktree was clean, and `CLEANUP_PROPOSED_ACTIONS.json` parsed successfully (388 records).
- The recovery commit is local only; no push occurred.

The snapshot preserves the state before cleanup. No cleanup had occurred before that snapshot.

## 2. Files deleted

The 150 approved duplicate candidate-model snapshot files were deleted from `backend/ai/`. The earliest exemplar was not deleted; it was moved to `archive/backend/ai/candidate_model_20260723112406.json`.

The 20 existing non-snapshot DELETE paths in the action JSON were deleted:

- `check_signature.py`
- `temp_show_results.py`
- `project_directory_listing.txt`
- `experiment_runs/cli_smoke.csv`
- `experiment_runs/cli_smoke.json`
- `experiment_runs/cli_smoke.jsonl`
- `.mypy_cache/`
- `.pytest_cache/`
- `.ruff_cache/`
- `backend/__pycache__/`
- `backend/ai/__pycache__/`
- `backend/compatibility/__pycache__/`
- `backend/config/__pycache__/`
- `backend/consolidation/__pycache__/`
- `backend/experiments/__pycache__/`
- `backend/memory/__pycache__/`
- `backend/models/__pycache__/`
- `backend/planning/__pycache__/`
- `backend/services/__pycache__/`
- `backend/tests/__pycache__/`

Owner decision applied: `.coverage` was deleted.

The 17 obsolete documentation paths in the DELETE list were already absent at the verified pre-cleanup state, so no filesystem deletion was performed for them in this pass. Their nested counterparts remain in place.

## 3. Files archived/moved

- 88 of 93 `ARCHIVE` actions were moved to their exact `destination_if_applicable` destinations. The per-path source, destination, and verification are recorded in `AURA_CLEANUP_EXECUTION_MANIFEST.json`.
- Owner decision applied: `AURA_v0.10_release.zip` was moved to `archive/releases/AURA_v0.10_release.zip`.
- The retained candidate-model exemplar was moved to `archive/backend/ai/candidate_model_20260723112406.json`.
- Five proposed archive actions were skipped because they may be protected research material or direct reproduction dependencies:
  - `17_16_SCHEMA_ANALYSIS_FINDING.md`
  - `backend/validation/safety_analyzer.py`
  - `backend/validation/decision_gate.py`
  - `backend/experiments/run_17_13_c_shadow_validation_run1.py`
  - `backend/experiments/test_mg_multi_lineage_check.py`

These remain at their original paths and are marked `SKIPPED_REQUIRES_REVIEW` in the execution manifest. The archive actions for generic 17.14A support modules were skipped because the source describes them as 17.14A safety/decision-gate implementation; the 17.13C runner and MG lineage test are explicit reproduction dependencies. The schema-analysis note was skipped conservatively due its ambiguous 17.16 provenance.

## 4. Files kept

- `database/aura_v1_schema.sql` exists and was left unchanged, per owner decision.
- `.venv/` and package markers/source helpers classified KEEP were not targeted.
- All `KEEP` and `NO_ACTION` paths in the proposed-actions file were left untouched, except the explicitly authorized owner overrides for `.coverage` and the release ZIP.
- The protected research files listed in section 7 remain at their original paths and match the recovery checkpoint contents.

## 5. Root-level structure before/after

**Before:** The root contained the expected project directories and configuration files, plus many historical research reports/manifests/results, experiment logs, test outputs, ad-hoc scripts, cleanup audit artifacts, and protected current research evidence.

**After:** Root still contains `.github/`, `backend/`, `database/`, `docs/`, `experiment_runs/`, `experiments/`, `frontend/`, `research/`, `archive/`, and core project files (`README.md`, `pyproject.toml`, `requirements-dev.txt`, `.gitignore`). Protected current-phase evidence and cleanup decision inputs remain at root. Historical material proposed for archiving has been moved under `archive/` or `research/` as specified. No further root cleanup was attempted after the path/reference stop condition.

The 17 deleted old documentation paths remain absent; the current nested counterparts are still present.

## 6. Candidate-model deduplication result

- Before cleanup: **151** timestamped `backend/ai/candidate_model_*.json` files.
- After cleanup: **1** file matching `candidate_model_*.json` in the repository.
- Retained exemplar: `archive/backend/ai/candidate_model_20260723112406.json`.
- Original common SHA-256: `917161640cd08df2117133fec8238da246bbf07f77ef6b8b5e6884acd60a2858`.
- Retained exemplar SHA-256: `917161640cd08df2117133fec8238da246bbf07f77ef6b8b5e6884acd60a2858`.
- Result: expected count and hash verified.

## 7. Protected research verification

The following required evidence files exist after cleanup:

- 17.13B: `RESEARCH_CHECKPOINT_17_13B_MG_INTEGRATION_VALIDATED.md`, `EVIDENCE_PRESERVATION_17_13B.md`, `RESEARCH_17_13_B_ENABLED_VERIFICATION.md`
- 17.13C: `RESEARCH_CHECKPOINT_17_13C_RUN1.md`, `17_13C_RESULT_RUN1.json`, `17_13C_EXECUTION_FINAL_REPORT.md`
- 17.14A: `RESEARCH_CHECKPOINT_17_14A_DECISION_GATE_COMPLETE.md`, `17_14A_SHADOW_VALIDATION_EVENTS.json`, `17_14A_SHADOW_VALIDATION_REPORT.json`
- 17.15: `RESEARCH_CHECKPOINT_17_15_SAFETY_GATES_PASS.json`, `17_15_SHADOW_VALIDATION_EVENTS.json`, `17_15_SHADOW_VALIDATION_REPORT.json`
- 17.16A: `RESEARCH_CHECKPOINT_17_16A_MECHANISM_SENSIBILITY.json`, `17_16A_BEHAVIORAL_ANALYSIS_RESULTS.json`
- 17.16B: `17_16B_ARCHITECTURE_AND_GROUND_TRUTH_ASSESSMENT.md`, `RESEARCH_CHECKPOINT_17_16B_DESIGN.json`

Additional protected validation scripts/support were checked and remain in place, including `backend/validation/behavioral_analysis_17_16a.py`, `backend/validation/17_14a_shadow_validation.py`, `backend/validation/shadow_validator_17_15.py`, `backend/validation/safety_analyzer.py`, `backend/validation/decision_gate.py`, and `backend/experiments/run_17_13_c_shadow_validation_run1.py`.

The 22 checked protected paths match their Git blobs in the recovery commit; no protected file was modified. 17.16B remains **BLOCKED** (`BLOCKED_INDEPENDENT_OUTCOME_DATA_REQUIRED`): no verified independent observed-outcome cohort exists. Synthetic experiences, simulated states, legacy predictions, and hard-coded `actual_state` values were not promoted to ground truth.

## 8. Test/import verification

**Not run.** The reference scan found likely path breaks caused by the approved archival moves. Per the instruction to stop if cleanup causes a path/reference break, Python import checks, research-script import checks, and the automated test suite were not run. No code or references were repaired.

## 9. Broken references found

The post-move scan found **35 exact old-path reference lines** in current non-archive source/document files. Some are historical mentions; the following are concrete unresolved path references:

### Existing research scripts/tests point to result files moved under `archive/`

| Moved result path (old path no longer exists) | Surviving reference |
|---|---|
| `backend/experiments/results/research_17_5_b_error_distribution_sequence.json` | `backend/experiments/test_research_error_distribution_sequence_17_5_b.py:367` |
| `backend/experiments/results/research_17_5_c_feature_coupling_temporal.json` | `backend/experiments/test_research_feature_coupling_temporal_17_5_c.py:126` |
| `backend/experiments/results/research_17_6_a_state_transition_calibration.json` | `backend/experiments/test_research_state_transition_calibration_17_6_a.py:102` |
| `backend/experiments/results/research_17_6_b_objective_alignment.json` | `backend/experiments/test_research_objective_alignment_17_6_b.py:97` |
| `backend/experiments/results/research_17_6_c_state_representation_identifiability.json` | `backend/experiments/test_research_state_representation_identifiability_17_6_c.py:74` |
| `backend/experiments/results/research_17_10_a_compatibility_layer.json` | `backend/experiments/research_compatibility_layer_17_10_a.py:177` |
| `backend/experiments/results/research_17_10_b_compatibility_integration.json` | `backend/experiments/research_compatibility_integration_17_10_b.py:338` |
| `backend/experiments/results/research_17_10_c_behavior_diagnostics.json` | `backend/experiments/research_behavior_diagnostics_17_10_c.py:500` and `backend/experiments/test_research_behavior_diagnostics_17_10_c.py:24` |
| `backend/experiments/results/research_17_10_d_mapping_equivalence.json` | `backend/experiments/research_mapping_equivalence_17_10_d.py:482` and `backend/experiments/test_research_mapping_equivalence_17_10_d.py:22` |
| `backend/experiments/results/research_17_11_mg_validation.json` | `backend/experiments/research_mg_validation_17_11.py:451` and `backend/experiments/test_research_mg_validation_17_11.py:25` |
| `backend/experiments/results/research_17_12_mg_shadow_integration.json` | `backend/experiments/research_mg_shadow_integration_17_12.py:541` and `backend/experiments/test_research_mg_shadow_integration_17_12.py:57` |

### Documentation/report paths no longer resolve at their prior locations

- `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md` refers to the moved `run_17_4_c.py`, multiple moved 17.4 result JSON files, and reports now under `research/17.4C/`.
- `research/17.5A/reports/PHASE_17_5A_COMPLETION_SUMMARY.md` and `research/17.5A/reports/RESEARCH_17_5_A_ERROR_SIGNAL_PROVENANCE.md` refer to result/report paths moved out of `backend/experiments/`.
- `research/17.8C/reports/RESEARCH_17_8_C_MINIMAL_STRUCTURE.md` refers to its result at the former `backend/experiments/results/` location.
- The protected 17.13B documents `backend/experiments/RESEARCH_17_13_B_STATUS_AND_ROADMAP.md`, `17_13_B_IMPLEMENTATION_COMPLETE.md`, and `17_13_B_VALIDATION_CHECKLIST.md` reference `backend/experiments/RESEARCH_17_13_A_PRODUCTION_INTEGRATION_DESIGN.md` and/or `RESEARCH_17_13_A_SUMMARY.md`, which were moved to `archive/backend/experiments/`.

These references were not repaired. Cleanup execution stopped here as directed.

## 10. Final Git status

- Branch remains `pre-cleanup-snapshot`.
- No cleanup commit was created; no push occurred.
- Worktree is **not clean**: with `git status --short --untracked-files=all`, there are **244 tracked deletions and 89 untracked paths**, including archive/research destinations and the execution report/manifest. There are **0 staged paths** and **0 remaining unstaged modifications** (the tracked worktree differences are deletions from moves/removals).
- Default `git status --short` collapses untracked directories; it reported 244 deleted paths plus 4 untracked directory entries. Use `git status --short --untracked-files=all` for the exact per-path view.
- No cleanup changes have been staged or committed.

## 11. Remaining cleanup issues

1. Resolve the broken old-path references before running imports/tests or resuming cleanup. Do not repair them without an explicit follow-up instruction.
2. Five archive proposals remain at their original paths as `SKIPPED_REQUIRES_REVIEW`.
3. The 17 obsolete tracked documentation paths were already absent before cleanup; no new deletion was made for those.
4. Full tests, Python imports, research-script imports, and broad documentation/link checks remain unverified because the stop condition was reached.
5. Other KEEP/NO_ACTION actions remain unapplied.

## 12. Research resumption decision

**Not ready to resume research verification yet.** Research evidence checked here remains unchanged, and 17.16B remains blocked. However, archival moves caused unresolved references and tests/imports were intentionally not run. First review the execution manifest and broken-reference list; any correction requires a separate explicit instruction. No methodology, scientific conclusion, or MG coefficient was changed.

## 13. REFERENCE_REPAIR_PASS

This section supersedes the pre-repair test/reference status in sections 8–9. Only path references caused by approved archive moves were addressed. No research claims, interpretation, model logic, or MG coefficients changed.

### Exact reference inventory found before repair

The scan found 35 moved-path occurrences in surviving non-archive code/evidence/documentation. **34 were stale references caused by cleanup; one was already a valid sibling-relative reference after relocation.** The 35 occurrences are listed below with their pre-repair line numbers, exact referenced paths, current archive/research destinations, file types, and dispositions.

| Referencing file:line | Exact old referenced path | Destination at scan time | Type/category | Resolution |
|---|---|---|---|---|
| `17_13_B_IMPLEMENTATION_COMPLETE.md:218` | `backend/experiments/RESEARCH_17_13_A_PRODUCTION_INTEGRATION_DESIGN.md` | `archive/backend/experiments/RESEARCH_17_13_A_PRODUCTION_INTEGRATION_DESIGN.md` | `.md`, A. protected research evidence | Restored artifact to original path; protected document unchanged. |
| `17_13_B_VALIDATION_CHECKLIST.md:92` | `backend/experiments/RESEARCH_17_13_A_PRODUCTION_INTEGRATION_DESIGN.md` | `archive/backend/experiments/RESEARCH_17_13_A_PRODUCTION_INTEGRATION_DESIGN.md` | `.md`, A. protected research evidence | Restored artifact to original path; protected document unchanged. |
| `17_13_B_VALIDATION_CHECKLIST.md:93` | `backend/experiments/RESEARCH_17_13_A_SUMMARY.md` | `archive/backend/experiments/RESEARCH_17_13_A_SUMMARY.md` | `.md`, A. protected research evidence | Restored artifact to original path; protected document unchanged. |
| `backend/experiments/RESEARCH_17_13_B_STATUS_AND_ROADMAP.md:261` | `backend/experiments/RESEARCH_17_13_A_PRODUCTION_INTEGRATION_DESIGN.md` | `archive/backend/experiments/RESEARCH_17_13_A_PRODUCTION_INTEGRATION_DESIGN.md` | `.md`, A. protected 17.13B record | Restored artifact to original path; source document unchanged. |
| `backend/experiments/RESEARCH_17_13_B_STATUS_AND_ROADMAP.md:262` | `backend/experiments/RESEARCH_17_13_A_SUMMARY.md` | `archive/backend/experiments/RESEARCH_17_13_A_SUMMARY.md` | `.md`, A. protected 17.13B record | Restored artifact to original path; source document unchanged. |
| `backend/experiments/test_research_behavior_diagnostics_17_10_c.py:24` | `backend/experiments/results/research_17_10_c_behavior_diagnostics.json` | `archive/backend/experiments/results/research_17_10_c_behavior_diagnostics.json` | `.py`, C. test code | Restored JSON to expected result path. |
| `backend/experiments/test_research_error_distribution_sequence_17_5_b.py:367` | `backend/experiments/results/research_17_5_b_error_distribution_sequence.json` | `archive/backend/experiments/results/research_17_5_b_error_distribution_sequence.json` | `.py`, C. test code | Restored JSON to expected result path. |
| `backend/experiments/test_research_feature_coupling_temporal_17_5_c.py:126` | `backend/experiments/results/research_17_5_c_feature_coupling_temporal.json` | `archive/backend/experiments/results/research_17_5_c_feature_coupling_temporal.json` | `.py`, C. test code | Restored JSON to expected result path. |
| `backend/experiments/test_research_mapping_equivalence_17_10_d.py:22` | `backend/experiments/results/research_17_10_d_mapping_equivalence.json` | `archive/backend/experiments/results/research_17_10_d_mapping_equivalence.json` | `.py`, C. test code | Restored JSON to expected result path. |
| `backend/experiments/test_research_mg_shadow_integration_17_12.py:57` | `backend/experiments/results/research_17_12_mg_shadow_integration.json` | `archive/backend/experiments/results/research_17_12_mg_shadow_integration.json` | `.py`, C. test code | Restored JSON to expected result path. |
| `backend/experiments/test_research_mg_validation_17_11.py:25` | `backend/experiments/results/research_17_11_mg_validation.json` | `archive/backend/experiments/results/research_17_11_mg_validation.json` | `.py`, C. test code | Restored JSON to expected result path. |
| `backend/experiments/test_research_objective_alignment_17_6_b.py:97` | `backend/experiments/results/research_17_6_b_objective_alignment.json` | `archive/backend/experiments/results/research_17_6_b_objective_alignment.json` | `.py`, C. test code | Restored JSON to expected result path. |
| `backend/experiments/test_research_state_representation_identifiability_17_6_c.py:74` | `backend/experiments/results/research_17_6_c_state_representation_identifiability.json` | `archive/backend/experiments/results/research_17_6_c_state_representation_identifiability.json` | `.py`, C. test code | Restored JSON to expected result path. |
| `backend/experiments/test_research_state_transition_calibration_17_6_a.py:102` | `backend/experiments/results/research_17_6_a_state_transition_calibration.json` | `archive/backend/experiments/results/research_17_6_a_state_transition_calibration.json` | `.py`, C. test code | Restored JSON to expected result path. |
| `backend/experiments/research_behavior_diagnostics_17_10_c.py:500` | `backend/experiments/results/research_17_10_c_behavior_diagnostics.json` | `archive/backend/experiments/results/research_17_10_c_behavior_diagnostics.json` | `.py`, D. research runner/script | Restored JSON to expected output path. |
| `backend/experiments/research_compatibility_integration_17_10_b.py:338` | `backend/experiments/results/research_17_10_b_compatibility_integration.json` | `archive/backend/experiments/results/research_17_10_b_compatibility_integration.json` | `.py`, D. research runner/script | Restored JSON to expected output path. |
| `backend/experiments/research_compatibility_layer_17_10_a.py:177` | `backend/experiments/results/research_17_10_a_compatibility_layer.json` | `archive/backend/experiments/results/research_17_10_a_compatibility_layer.json` | `.py`, D. research runner/script | Restored JSON to expected output path. |
| `backend/experiments/research_mapping_equivalence_17_10_d.py:482` | `backend/experiments/results/research_17_10_d_mapping_equivalence.json` | `archive/backend/experiments/results/research_17_10_d_mapping_equivalence.json` | `.py`, D. research runner/script | Restored JSON to expected output path. |
| `backend/experiments/research_mg_shadow_integration_17_12.py:541` | `backend/experiments/results/research_17_12_mg_shadow_integration.json` | `archive/backend/experiments/results/research_17_12_mg_shadow_integration.json` | `.py`, D. research runner/script | Restored JSON to expected output path. |
| `backend/experiments/research_mg_validation_17_11.py:451` | `backend/experiments/results/research_17_11_mg_validation.json` | `archive/backend/experiments/results/research_17_11_mg_validation.json` | `.py`, D. research runner/script | Restored JSON to expected output path. |
| `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md:42` | `run_17_4_c.py` | `research/17.4C/scripts/run_17_4_c.py` | `.md`, E. ordinary documentation | Path-only update to `../scripts/run_17_4_c.py`. |
| `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md:122` | `run_17_4_c.py` | `research/17.4C/scripts/run_17_4_c.py` | `.md`, E. ordinary documentation | Path-only update to `../scripts/run_17_4_c.py`. |
| `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md:125` | `backend/experiments/RESEARCH_17_4_B_COMPLETE_REPORT.md` | `archive/backend/experiments/RESEARCH_17_4_B_COMPLETE_REPORT.md` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md:126` | `backend/experiments/RESEARCH_17_4_C_RESULTS_ANALYSIS.md` | `research/17.4C/results/RESEARCH_17_4_C_RESULTS_ANALYSIS.md` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md:127` | `backend/experiments/RESEARCH_17_4_FINAL_SUMMARY.md` | `archive/backend/experiments/RESEARCH_17_4_FINAL_SUMMARY.md` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md:128` | `backend/experiments/RESEARCH_17_4_ABC_COMPREHENSIVE_REPORT.md` | `archive/backend/experiments/RESEARCH_17_4_ABC_COMPREHENSIVE_REPORT.md` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md:131` | `backend/experiments/results/research_17_4_a_sign_aware_robustness.json` | `archive/backend/experiments/results/research_17_4_a_sign_aware_robustness.json` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md:132` | `backend/experiments/results/research_17_4_b_sign_aware_refinement.json` | `archive/backend/experiments/results/research_17_4_b_sign_aware_refinement.json` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.4C/reports/PHASE_17_4C_COMPLETION_SUMMARY.md:133` | `backend/experiments/results/research_17_4_c_clipped_confidence_gated.json` | `research/17.4C/reports/research_17_4_c_clipped_confidence_gated.json` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.4C/results/RESEARCH_17_4_C_RESULTS_ANALYSIS.md:350` | `backend/experiments/results/research_17_4_c_clipped_confidence_gated.json` | `research/17.4C/reports/research_17_4_c_clipped_confidence_gated.json` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.5A/reports/PHASE_17_5A_COMPLETION_SUMMARY.md:23` | `backend/experiments/results/research_17_5_a_error_signal_provenance.json` | `research/17.5A/reports/research_17_5_a_error_signal_provenance.json` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.5A/reports/PHASE_17_5A_COMPLETION_SUMMARY.md:30` | `backend/experiments/RESEARCH_17_5_A_ERROR_SIGNAL_PROVENANCE.md` | `research/17.5A/reports/RESEARCH_17_5_A_ERROR_SIGNAL_PROVENANCE.md` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.5A/reports/RESEARCH_17_5_A_ERROR_SIGNAL_PROVENANCE.md:250` | `backend/experiments/results/research_17_5_a_error_signal_provenance.json` | `research/17.5A/reports/research_17_5_a_error_signal_provenance.json` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.8C/reports/RESEARCH_17_8_C_MINIMAL_STRUCTURE.md:62` | `backend/experiments/results/research_17_8_c_minimal_structure.json` | `research/17.8C/reports/research_17_8_c_minimal_structure.json` | `.md`, E. ordinary documentation | Path-only update. |
| `research/17.5A/reports/PHASE_17_5A_QUICK_REFERENCE.md:18` | `PHASE_17_5A_COMPLETION_SUMMARY.md` | `research/17.5A/reports/PHASE_17_5A_COMPLETION_SUMMARY.md` | `.md`, E. ordinary documentation | Not stale: the summary is now a sibling in the same directory; relative reference remains valid. |

### Repairs and verification

- **Stale references found:** 34; 35 total moved-path occurrences were inspected, including the one valid same-directory reference above.
- **Artifacts restored:** 13 unique files by moving them back (2 documents needed by protected 17.13B records and 11 JSON result artifacts needed by research tests/runners). There are no divergent duplicate copies at the former archive destinations.
- **Documentation paths updated:** 14 references in 5 ordinary documentation files. Edits were path-only; no claims or interpretations changed.
- **Items skipped for review in this reference-repair pass:** 0. Five archive proposals from the earlier execution remain `SKIPPED_REQUIRES_REVIEW` as already recorded in the manifest; they were not part of this repair.
- **Final unresolved exact references:** 0. The final boundary-aware scan covered 563 surviving text files; all 20 remaining exact old-path occurrences resolve at their restored original paths or to a valid same-directory relative target.
- **Imports:** 22 modules checked, 22 passed, 0 failed. This imported the application entry point, affected research runners/tests, and protected validation modules; no research experiment function was executed.
- **Automated tests:** `python -m pytest` collected 389; 389 passed, 0 failed, 177 warnings (66.38 seconds).
- **Markdown local-link scan:** 100 Markdown files scanned; 15 unresolved local links remain across `17_13_B_IMPLEMENTATION_COMPLETE.md`, `17_14A_SHADOW_VALIDATION_COMPLETE.md`, and `backend/experiments/RESEARCH_17_13_B_IMPLEMENTATION_SUMMARY.md`. These source files match their recovery-checkpoint blobs exactly, and representative missing link targets were also absent at the checkpoint. They are pre-existing, not caused by cleanup. Protected documents were not edited to address them.

### Candidate-model post-test discrepancy and final status

The initial cleanup result was 1 retained exemplar. The test suite subsequently created three untracked candidate-model metadata files:

- `backend/ai/candidate_model_20261006173253.json`
- `backend/ai/candidate_model_20261006173254.json`
- `backend/ai/candidate_model_20261006173255.json`

At the time this first post-test report section was written, the retained exemplar and all three generated files had the expected common SHA-256 `917161640cd08df2117133fec8238da246bbf07f77ef6b8b5e6884acd60a2858`, and the observed count was four. The targeted `TEST_SIDE_EFFECT_CLEANUP` pass below verified and removed exactly those three test-generated files; it did not touch any other candidate-model path. The current count is again **1**, with the approved archived exemplar intact and matching the expected hash.

The test run also left 12 tracked data/registry files modified:

`backend/ai/meta_learning.json`, `backend/ai/model_registry.json`, `backend/ai/policy_registry.json`, `backend/ai/reasoning_registry.json`, `backend/ai/reflection_memory.json`, `backend/ai/reflection_registry.json`, `backend/ai/research_registry.json`, `backend/consolidation/knowledge_registry.json`, `backend/consolidation/pattern_registry.json`, `backend/data/experience_dataset.json`, `backend/memory/memory_registry.json`, and `experiments/ablation_seed_7/experiment.json`.

They were subsequently restored path-by-path to the recovery commit in `TEST_SIDE_EFFECT_CLEANUP`. No other cleanup changes were staged or committed.

Final Git status at report preparation: branch `pre-cleanup-snapshot`, HEAD `aeae3008b9951c1840a3827cb096a85406a81265`; `git status --short --untracked-files=all` reported 230 deleted paths, 12 modified tracked paths, and 79 untracked paths (321 entries total). Nothing is staged.

At the time of this initial post-test report, the decision was **STILL_BLOCKED** because the test-generated candidate snapshots and tracked test side effects had not yet been resolved. The later `TEST_SIDE_EFFECT_CLEANUP` section records their resolution and supersedes that interim decision.

## 14. TEST_SIDE_EFFECT_CLEANUP

This pass removed only verification side effects. The full test suite and imports were **not rerun**; the historical results remain 389/389 tests passed and 22/22 imports passed.

- **Generated candidate files removed (3):**
  - `backend/ai/candidate_model_20261006173253.json`
  - `backend/ai/candidate_model_20261006173254.json`
  - `backend/ai/candidate_model_20261006173255.json`
- Before removal, each file was confirmed absent from recovery commit `b5c81b0444c73c98915c8734044e19ddc128a010`, untracked, created during the test run, hash-identical to `917161640cd08df2117133fec8238da246bbf07f77ef6b8b5e6884acd60a2858`, and payload-identical to the exemplar. Repository search found mentions only in the execution report/manifest as audit records; no source, test, or research consumer referenced them.
- **Tracked files restored (12) to source recovery commit `b5c81b0444c73c98915c8734044e19ddc128a010`:** `backend/ai/meta_learning.json`, `backend/ai/model_registry.json`, `backend/ai/policy_registry.json`, `backend/ai/reasoning_registry.json`, `backend/ai/reflection_memory.json`, `backend/ai/reflection_registry.json`, `backend/ai/research_registry.json`, `backend/consolidation/knowledge_registry.json`, `backend/consolidation/pattern_registry.json`, `backend/data/experience_dataset.json`, `backend/memory/memory_registry.json`, and `experiments/ablation_seed_7/experiment.json`. Each now matches the recovery commit blob exactly.
- Candidate-model file count after this pass: **1**. Retained exemplar: `archive/backend/ai/candidate_model_20260723112406.json`; SHA-256: `917161640cd08df2117133fec8238da246bbf07f77ef6b8b5e6884acd60a2858`.
- Protected research comparison: **0 mismatches across 22 checked paths**. `17_16B_ARCHITECTURE_AND_GROUND_TRUTH_ASSESSMENT.md` and `RESEARCH_CHECKPOINT_17_16B_DESIGN.json` remain unchanged. 17.16B remains **BLOCKED** (`BLOCKED_INDEPENDENT_OUTCOME_DATA_REQUIRED`).
- Final exact cleanup-path scan: **0 unresolved references**.
- Test/import verification: prior result **389/389 tests passed** and **22/22 imports passed**; not rerun in this pass to avoid recreating side effects.
- Test side effects remaining: **0**. No files outside the three named generated candidates and 12 listed tracked paths were removed/restored in this pass.

### Final Git status and commit readiness

- Branch: `pre-cleanup-snapshot`.
- HEAD: `aeae3008b9951c1840a3827cb096a85406a81265`.
- `git status --short --untracked-files=all`: **230 tracked deletions, 0 tracked modifications, 76 untracked paths, 0 staged paths** (306 entries).
- A path audit confirmed every remaining deletion maps to a recorded cleanup action and every remaining untracked path maps to a recorded archive destination or one of the execution report/manifest. No test-side-effect path remains in status.
- No commit was created; nothing was pushed.

**Decision: SAFE_TO_COMMIT.** The worktree is intentionally not clean because approved cleanup and reference-repair changes remain uncommitted. This is a readiness assessment only; this task does not authorize creating a commit.
