from __future__ import annotations

from backend.services.simulation_engine import simulation_engine


def test_branching_tree_basic():
    engine = simulation_engine
    root = engine.make_snapshot({"python": 0}, simulation_id="sim1", step=0, snapshot_id="root", parent_snapshot_id=None)
    actions = ["learn python"]
    tree = engine.simulate_branching_trajectory(root, actions, context=None, max_branches=None)

    assert not tree.stopped_early
    assert tree.root.snapshot is root

    children = tree.root.children
    # Probabilistic model returns 3 branches by default
    assert len(children) == 3

    total = sum(c.probability_from_parent for c in children)
    assert abs(total - 1.0) < 1e-6

    for c in children:
        assert c.snapshot.parent_snapshot_id == root.snapshot_id
        assert c.action_from_parent == "learn python"
        assert c.cumulative_probability() == c.probability_from_parent

    leaves = tree.leaves()
    assert len(leaves) == 3


def test_branching_tree_two_steps_and_cumulative():
    engine = simulation_engine
    root = engine.make_snapshot({"python": 0}, simulation_id="sim2", step=0, snapshot_id="root2", parent_snapshot_id=None)
    actions = ["learn python", "learn python"]
    tree = engine.simulate_branching_trajectory(root, actions, context=None, max_branches=None)

    # Depth 2 leaves count should be 3 * 3 = 9
    leaves = tree.leaves()
    assert len(leaves) == 9

    # pick first leaf and verify cumulative probability is product of edge probabilities
    first_child = tree.root.children[0]
    first_grandchild = first_child.children[0]
    expected = first_child.probability_from_parent * first_grandchild.probability_from_parent
    assert abs(first_grandchild.cumulative_probability() - expected) < 1e-9


def test_invalid_action_stops_early():
    engine = simulation_engine
    root = engine.make_snapshot({"python": 0}, simulation_id="sim3", step=0, snapshot_id="root3", parent_snapshot_id=None)
    # empty action should be considered invalid
    actions = [""]
    tree = engine.simulate_branching_trajectory(root, actions, context=None, max_branches=None)
    assert tree.stopped_early
    # no children should have been created
    assert not tree.root.children
