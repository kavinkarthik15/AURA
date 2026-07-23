from __future__ import annotations

from pathlib import Path

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from backend.ai.sequence_transition_model import SequenceTransitionModel, load_sequence_dataset
from backend.ai.transition_model import TransitionModel


V1_MODEL_PATH = Path("backend/ai/saved_models/aura_transition_v1.pkl")
V2_MODEL_PATH = Path("backend/ai/saved_models/sequence_model.pkl")


def evaluate() -> dict:
    dataset = load_sequence_dataset()
    model_v2 = SequenceTransitionModel()
    feature_vectors, target_vectors = model_v2._build_training_arrays(dataset)

    X_train, X_test, y_train, y_test = train_test_split(
        feature_vectors,
        target_vectors,
        test_size=0.2,
        random_state=42,
    )

    model_v2.model.fit(X_train, y_train)
    v2_predictions = model_v2.model.predict(X_test)

    v1_model = TransitionModel.load_model(V1_MODEL_PATH)
    v1_predictions = []
    for sample in X_test:
        state = {
            "python": sample[0],
            "machine_learning": sample[1],
            "dsa": sample[2],
            "projects": sample[3],
            "communication": sample[4],
        }
        action = "Build Python Project"
        v1_predictions.append(list(v1_model.predict(state, action).values()))

    v1_targets = y_test
    v1_mae = mean_absolute_error(v1_targets, v1_predictions)
    v1_mse = mean_squared_error(v1_targets, v1_predictions)
    v1_r2 = r2_score(v1_targets, v1_predictions)

    v2_mae = mean_absolute_error(y_test, v2_predictions)
    v2_mse = mean_squared_error(y_test, v2_predictions)
    v2_r2 = r2_score(y_test, v2_predictions)

    return {
        "v1": {
            "mae": float(v1_mae),
            "mse": float(v1_mse),
            "r2": float(v1_r2),
        },
        "v2": {
            "mae": float(v2_mae),
            "mse": float(v2_mse),
            "r2": float(v2_r2),
        },
    }


if __name__ == "__main__":
    print(evaluate())
