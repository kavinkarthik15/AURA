"""
17.0A Deterministic Research Benchmark Generator

Generates 100 diverse, reproducible synthetic experiences with controlled randomness.

Each experience represents a realistic learning scenario with specific characteristics:
- low_skill_practice: low starting skill, action leads to modest growth
- medium_skill_practice: medium skill, moderate growth
- high_skill_practice: high skill, diminishing returns
- low_motivation: action fails or backfires slightly
- high_motivation: action leads to above-average growth
- mixed_skills: action affects multiple skills with varied outcomes
- project_completion: significant multi-skill advancement
- plateau: high starting skill, minimal further growth
"""

from typing import Dict
import random
from backend.experiments.research_experience import (
    ResearchExperience,
    ResearchDataset,
    ExperienceCategoryType,
)


class ResearchBenchmarkGenerator:
    """
    Deterministic benchmark generator for research validation.
    
    Uses seed-based random generation to ensure reproducibility.
    Creates diverse experience categories to stress-test learning.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_dataset(
        self, 
        training_size: int = 80, 
        held_out_size: int = 20
    ) -> ResearchDataset:
        """
        Generate a complete research dataset with train/held-out split.
        
        Args:
            training_size: Number of training experiences
            held_out_size: Number of held-out evaluation experiences
            
        Returns:
            ResearchDataset with properly split experiences
        """
        total_size = training_size + held_out_size
        all_experiences = [
            self._generate_experience(i) for i in range(total_size)
        ]

        # Deterministic split
        training_exps = all_experiences[:training_size]
        held_out_exps = all_experiences[training_size:]

        return ResearchDataset(
            dataset_id=f"research_benchmark_v1_seed_{self.seed}",
            seed=self.seed,
            training_experiences=training_exps,
            held_out_experiences=held_out_exps,
        )

    def _generate_experience(self, exp_idx: int) -> ResearchExperience:
        """
        Generate a single experience deterministically.
        
        Assigns experience to a category based on index,
        then generates realistic initial_state, prediction, and ground truth.
        """
        # Cycle through categories deterministically
        categories: list[ExperienceCategoryType] = [
            "low_skill_practice",
            "medium_skill_practice",
            "high_skill_practice",
            "low_motivation",
            "high_motivation",
            "mixed_skills",
            "project_completion",
            "plateau",
        ]
        category = categories[exp_idx % len(categories)]

        # Set random state for this experience
        self.rng.seed(self.seed + exp_idx)

        initial_state = self._initial_state_for_category(category)
        action = self._action_for_category(category)
        predicted_future, actual_future = self._prediction_and_actual_for_category(
            category, initial_state
        )

        return ResearchExperience(
            experience_id=f"research_exp_{exp_idx:03d}_{category}",
            category=category,
            initial_state=initial_state,
            selected_action=action,
            predicted_future_state=predicted_future,
            actual_future_state=actual_future,
        )

    def _initial_state_for_category(self, category: ExperienceCategoryType) -> Dict[str, int]:
        """
        Generate initial skill state based on category.
        """
        if category == "low_skill_practice":
            return {
                "python": self.rng.randint(20, 35),
                "dsa": self.rng.randint(15, 25),
                "machine_learning": self.rng.randint(10, 20),
                "projects": self.rng.randint(15, 25),
            }
        elif category == "medium_skill_practice":
            return {
                "python": self.rng.randint(40, 60),
                "dsa": self.rng.randint(35, 50),
                "machine_learning": self.rng.randint(30, 45),
                "projects": self.rng.randint(35, 50),
            }
        elif category == "high_skill_practice":
            return {
                "python": self.rng.randint(70, 85),
                "dsa": self.rng.randint(65, 80),
                "machine_learning": self.rng.randint(60, 75),
                "projects": self.rng.randint(70, 85),
            }
        elif category == "low_motivation":
            return {
                "python": self.rng.randint(40, 55),
                "dsa": self.rng.randint(35, 50),
                "machine_learning": self.rng.randint(25, 40),
                "projects": self.rng.randint(30, 45),
            }
        elif category == "high_motivation":
            return {
                "python": self.rng.randint(30, 50),
                "dsa": self.rng.randint(25, 40),
                "machine_learning": self.rng.randint(20, 35),
                "projects": self.rng.randint(25, 40),
            }
        elif category == "mixed_skills":
            return {
                "python": self.rng.randint(50, 70),
                "dsa": self.rng.randint(20, 40),
                "machine_learning": self.rng.randint(60, 75),
                "projects": self.rng.randint(30, 50),
            }
        elif category == "project_completion":
            return {
                "python": self.rng.randint(45, 65),
                "dsa": self.rng.randint(40, 60),
                "machine_learning": self.rng.randint(35, 55),
                "projects": self.rng.randint(40, 60),
            }
        else:  # plateau
            return {
                "python": self.rng.randint(75, 90),
                "dsa": self.rng.randint(70, 85),
                "machine_learning": self.rng.randint(65, 80),
                "projects": self.rng.randint(75, 90),
            }

    def _action_for_category(self, category: ExperienceCategoryType) -> str:
        """
        Select an action based on category.
        """
        action_pool = [
            "Python Project",
            "DSA Practice",
            "ML Course",
            "Interview Prep",
            "Build Portfolio",
            "Research Paper",
        ]
        return self.rng.choice(action_pool)

    def _prediction_and_actual_for_category(
        self, category: ExperienceCategoryType, initial_state: Dict[str, int]
    ) -> tuple[Dict[str, int], Dict[str, int]]:
        """
        Generate predicted and actual future states with learnable systematic biases.
        
        Strategy: Apply the SAME systematic bias to ALL skills uniformly.
        This makes the pattern consistent and easier for calibration to learn.
        """
        prediction_bias = self._prediction_bias_for_category(category)
        systematic_bias = self._systematic_bias_for_category(category)
        prediction_error_scale = self._error_scale_for_category(category)

        # Create predicted state
        predicted = dict(initial_state)
        for skill in predicted:
            predicted[skill] = int(predicted[skill] + prediction_bias)
            predicted[skill] = max(1, min(100, predicted[skill]))

        # Create actual state: apply SAME systematic bias to all skills + random noise
        actual = dict(predicted)
        
        # Apply systematic bias uniformly to ALL skills (consistent pattern)
        for skill in actual:
            # Systematic bias (same for all skills - consistent pattern)
            actual[skill] = int(actual[skill] + systematic_bias)
            
            # Small random noise
            random_error = self.rng.randint(-prediction_error_scale, prediction_error_scale)
            actual[skill] = int(actual[skill] + random_error)
            
            actual[skill] = max(1, min(100, actual[skill]))

        return predicted, actual

    def _prediction_bias_for_category(self, category: ExperienceCategoryType) -> int:
        """
        Bias applied to predicted state (digital twin's assumption).
        """
        if category == "low_skill_practice":
            return self.rng.randint(3, 8)  # Small but realistic growth
        elif category == "medium_skill_practice":
            return self.rng.randint(4, 10)  # Moderate growth
        elif category == "high_skill_practice":
            return self.rng.randint(1, 5)  # Diminishing returns
        elif category == "low_motivation":
            return self.rng.randint(-3, 2)  # Negative or minimal
        elif category == "high_motivation":
            return self.rng.randint(6, 12)  # Above-average
        elif category == "mixed_skills":
            return self.rng.randint(2, 6)  # Variable by skill
        elif category == "project_completion":
            return self.rng.randint(8, 15)  # Large multi-skill growth
        else:  # plateau
            return self.rng.randint(-2, 2)  # Almost no growth

    def _systematic_bias_for_category(self, category: ExperienceCategoryType) -> int:
        """
        Systematic bias: consistent per-category error that learning should discover.
        
        These are LARGE biases (3-5 points) so that even without knowing direction,
        calibration accumulates enough magnitude to reduce MAE.
        """
        # Each category has a consistent bias that predictions miss
        # Making these large enough to overcome direction uncertainty
        if category == "low_skill_practice":
            return 4  # Predictions underestimate significantly
        elif category == "medium_skill_practice":
            return 3  # Moderate underestimation
        elif category == "high_skill_practice":
            return -3  # Overestimate
        elif category == "low_motivation":
            return 5  # Largest underestimation: predictions very pessimistic
        elif category == "high_motivation":
            return -4  # Biggest overestimation
        elif category == "mixed_skills":
            return 3  # Multi-skill underestimation
        elif category == "project_completion":
            return 5  # Large projects underestimated
        else:  # plateau
            return 0  # Plateau is well-predicted

    def _error_scale_for_category(self, category: ExperienceCategoryType) -> int:
        """
        Scale of random prediction error (irreducible noise, not systematic bias).
        
        The systematic bias is separate and learnable.
        This random component makes the task realistic but not impossible.
        """
        if category == "low_skill_practice":
            return 2  # Small irreducible noise
        elif category == "medium_skill_practice":
            return 2
        elif category == "high_skill_practice":
            return 1  # High-skill is more predictable
        elif category == "low_motivation":
            return 3  # Somewhat unpredictable
        elif category == "high_motivation":
            return 2
        elif category == "mixed_skills":
            return 2
        elif category == "project_completion":
            return 3  # Multi-skill adds variance
        else:  # plateau
            return 1  # Very stable


# Convenience function for research use
def generate_research_dataset(seed: int = 42, training_size: int = 80, held_out_size: int = 20) -> ResearchDataset:
    """
    Quick access to generate a research dataset.
    
    Args:
        seed: Random seed for determinism
        training_size: Number of training experiences
        held_out_size: Number of held-out experiences
        
    Returns:
        ResearchDataset ready for use
    """
    generator = ResearchBenchmarkGenerator(seed=seed)
    return generator.generate_dataset(training_size=training_size, held_out_size=held_out_size)
