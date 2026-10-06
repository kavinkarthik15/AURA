from backend.experiments.research_predictive_state_dimensions_17_8_a import (
    CANDIDATE_DIMENSIONS,
    PredictiveStateDimensionAnalyzer,
    ResearchPhase17_8_A,
)


def test_dimension_analysis_exposes_expected_candidates():
    analyzer = PredictiveStateDimensionAnalyzer(seed=42)
    dataset = analyzer.generator.generate_dataset(training_size=80, held_out_size=20)
    result = analyzer.analyze_seed()

    assert len(result.measurements) == len(CANDIDATE_DIMENSIONS)
    assert {entry.dimension for entry in result.measurements} == set(CANDIDATE_DIMENSIONS)
    assert all(entry.variation_score >= 0.0 for entry in result.measurements)
    assert all(entry.delta_r2 is not None for entry in result.measurements)


def test_phase_runs_and_saves_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    phase = ResearchPhase17_8_A(seeds=[42])
    result = phase.run()

    assert 42 in result.seed_results
    assert result.seed_results[42].seed == 42
    assert result.seed_results[42].measurements
