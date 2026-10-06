from backend.experiments.research_parameter_expressiveness_17_7_a import ParameterExpressivenessAnalyzer, ResearchPhase17_7_A


def test_expected_state_bias_has_clear_sweep_response():
    analyzer = ParameterExpressivenessAnalyzer(seed=42)
    dataset = analyzer.generator.generate_dataset(training_size=80, held_out_size=20)
    experience = dataset.training_experiences[0]
    summary = analyzer._sweep_expected_state_bias_for_experience(experience)

    assert summary.response_curve
    assert summary.expressiveness_ratio >= 0.0
    assert summary.monotonic_direction >= 0.0
    assert summary.required_correction >= 0.0
    assert summary.achievable_correction >= 0.0


def test_sensitivity_matrix_includes_all_parameter_slots():
    analyzer = ParameterExpressivenessAnalyzer(seed=42)
    dataset = analyzer.generator.generate_dataset(training_size=80, held_out_size=20)
    matrix = analyzer._parameter_sensitivity_matrix(dataset)
    parameter_names = {entry.parameter for entry in matrix}

    assert {"expected_state_bias", "transition_probability_bias", "risk_bias", "uncertainty", "confidence"}.issubset(parameter_names)
    assert len(matrix) == 5


def test_research_phase_runs_and_saves_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = ResearchPhase17_7_A(seeds=[42]).run()
    assert 42 in result.seed_results
    assert result.seed_results[42].expected_state_bias_mean_ratio >= 0.0
    assert result.seed_results[42].sensitivity_matrix
