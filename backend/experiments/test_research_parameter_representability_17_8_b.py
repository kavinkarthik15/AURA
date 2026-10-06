from backend.experiments.research_parameter_representability_17_8_b import (
    PREDICTIVE_DIMENSIONS,
    ParameterRepresentabilityAnalyzer,
    ResearchPhase17_8_B,
)


def test_representability_matrix_has_expected_dimensions():
    analyzer = ParameterRepresentabilityAnalyzer(seed=42)
    result = analyzer.analyze_seed()

    assert set(result.matrix) == set(PREDICTIVE_DIMENSIONS)
    assert result.total_events == 80

    motivation = result.matrix["motivation"]
    goals = result.matrix["goals"]
    behavior = result.matrix["behavior"]

    assert motivation.can_influence_prediction is False
    assert goals.can_influence_prediction is False
    assert behavior.can_influence_prediction in {True, False}

    assert motivation.classification in {
        "represented",
        "representable_but_disconnected",
        "not_representable",
        "indirectly_representable",
    }


def test_phase_runs_and_saves_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    phase = ResearchPhase17_8_B(seeds=[42])
    result = phase.run()

    assert 42 in result.seed_results
    assert result.seed_results[42].seed == 42
    assert set(result.seed_results[42].matrix) == set(PREDICTIVE_DIMENSIONS)
