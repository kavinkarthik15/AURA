import unittest

from backend.ai.state_similarity import action_overlap, combined_similarity, cosine_similarity, goal_similarity, weighted_similarity


class StateSimilarityTests(unittest.TestCase):
    def test_cosine_and_weighted_similarity(self) -> None:
        self.assertAlmostEqual(cosine_similarity({"python": 3}, {"python": 3}), 1.0)
        self.assertGreater(weighted_similarity({"python": 50}, {"python": 55}), 0.8)

    def test_goal_and_action_similarity(self) -> None:
        self.assertGreater(goal_similarity("Python Growth", "Python Growth Plan"), 0.5)
        self.assertEqual(action_overlap(["Project", "DSA"], ["Project"]), 0.5)
        self.assertGreater(combined_similarity({"python": 50}, "Python Growth", ["Project"], {"python": 52}, "Python Growth", ["Project"]), 0.8)


if __name__ == "__main__":
    unittest.main()
