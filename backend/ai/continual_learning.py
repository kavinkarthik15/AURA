from typing import Any, Dict, List

from backend.ai.benchmark_candidate import BenchmarkCandidate
from backend.ai.continual_trainer import ContinualTrainer
from backend.ai.deploy_candidate import DeployCandidate
from backend.ai.experience_replay import ExperienceReplayBuffer
from backend.ai.model_registry import ModelRegistry
from backend.models.experience_log import ExperienceLog


class ContinualLearningPipeline:
    def __init__(self) -> None:
        self.replay_buffer = ExperienceReplayBuffer()
        self.trainer = ContinualTrainer()
        self.benchmark = BenchmarkCandidate()
        self.deploy = DeployCandidate()
        self.registry = ModelRegistry()

    def ingest_experiences(self, experiences: List[ExperienceLog]) -> None:
        self.replay_buffer.load_experiences(experiences)

    def _build_merge_metadata(self, base_dataset: List[Dict[str, Any]] | None, replay: List[ExperienceLog]) -> Dict[str, Any]:
        base_count = len(base_dataset or [])
        experience_count = len(replay)
        return {
            "base_dataset": base_count,
            "experience_dataset": experience_count,
            "merged_dataset": base_count + experience_count,
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }

    def _build_report(self, candidate: Dict[str, Any], benchmark: Dict[str, Any], deployment: Dict[str, Any], merge_meta: Dict[str, Any]) -> str:
        decision = "Accepted" if deployment.get("deployed") else "Rejected"
        return "\n".join([
            "Continual Learning Cycle",
            "",
            f"Base Dataset: {merge_meta['base_dataset']}",
            "",
            f"Replay Experiences: {merge_meta['experience_dataset']}",
            "",
            f"Merged Dataset: {merge_meta['merged_dataset']}",
            "",
            f"Candidate Model: {candidate.get('model_version')}",
            "",
            "Benchmark:",
            f"MAE: {benchmark.get('candidate_score', 0.0)}",
            f"MSE: {benchmark.get('candidate_score', 0.0)}",
            f"R²: {max(0.0, 1.0 - benchmark.get('candidate_score', 0.0))}",
            "",
            f"Decision: {decision}",
            "",
            f"Reason: {deployment.get('reason', 'n/a')}",
        ])

    def run(self, experiences: List[ExperienceLog], base_dataset: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        self.ingest_experiences(experiences)
        replay = self.replay_buffer.sample(batch_size=max(1, len(experiences)))
        stats = self.replay_buffer.get_statistics()
        merge_meta = self._build_merge_metadata(base_dataset, replay)
        candidate = self.trainer.train_candidate(replay, base_dataset=base_dataset)

        baseline = self.registry.get_latest_model()
        benchmark = self.benchmark.benchmark(candidate, baseline=baseline)
        deployment = self.deploy.deploy(candidate, benchmark)
        candidate_registered = None

        if deployment.get("deployed"):
            candidate_registered = self.registry.register_model(
                model_version=candidate["model_version"],
                algorithm="RandomForestRegressor",
                dataset_size=candidate["dataset_size"],
                mae=benchmark.get("candidate_score", 0.0),
                mse=benchmark.get("candidate_score", 0.0),
                r2=max(0.0, 1.0 - max(benchmark.get("candidate_score", 0.0), 0.0)),
                training_data_hash=candidate.get("dataset_hash"),
                dataset_version="v1",
                parent_model=baseline.get("model_version") if baseline else None,
                training_source="experience_replay",
                experience_count=len(replay),
                accepted=True,
                benchmark={
                    "mae": benchmark.get("candidate_score", 0.0),
                    "mse": benchmark.get("candidate_score", 0.0),
                    "r2": max(0.0, 1.0 - max(benchmark.get("candidate_score", 0.0), 0.0)),
                },
            )
        else:
            candidate_registered = self.registry.register_model(
                model_version=candidate["model_version"],
                algorithm="RandomForestRegressor",
                dataset_size=candidate["dataset_size"],
                mae=benchmark.get("candidate_score", 0.0),
                mse=benchmark.get("candidate_score", 0.0),
                r2=max(0.0, 1.0 - max(benchmark.get("candidate_score", 0.0), 0.0)),
                training_data_hash=candidate.get("dataset_hash"),
                dataset_version="v1",
                parent_model=baseline.get("model_version") if baseline else None,
                training_source="experience_replay",
                experience_count=len(replay),
                accepted=False,
                benchmark={
                    "mae": benchmark.get("candidate_score", 0.0),
                    "mse": benchmark.get("candidate_score", 0.0),
                    "r2": max(0.0, 1.0 - max(benchmark.get("candidate_score", 0.0), 0.0)),
                },
            )

        return {
            "candidate": candidate,
            "benchmark": benchmark,
            "deployment": deployment,
            "registered": candidate_registered,
            "merge_metadata": merge_meta,
            "replay_stats": stats,
            "report": self._build_report(candidate, benchmark, deployment, merge_meta),
        }
