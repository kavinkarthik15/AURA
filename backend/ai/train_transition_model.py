from __future__ import annotations

import hashlib
from pathlib import Path

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from backend.ai.model_registry import register_model_record
from backend.ai.transition_model import TransitionModel, load_training_dataset


MODEL_OUTPUT_PATH = Path(__file__).resolve().parent / "saved_models" / "aura_transition_v1.pkl"


def main() -> None:
    dataset = load_training_dataset()
    model = TransitionModel()
    model.train(dataset)

    feature_vectors, target_vectors = model._build_training_arrays(dataset)
    X_train, X_test, y_train, y_test = train_test_split(
        feature_vectors,
        target_vectors,
        test_size=0.2,
        random_state=42,
    )
    model.model.fit(X_train, y_train)
    predictions = model.model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)
    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    dataset_hash = hashlib.sha256(Path("backend/data/training_data.json").read_bytes()).hexdigest()

    output_path = model.save_model(MODEL_OUTPUT_PATH)
    register_model_record(
        model_version="v1",
        algorithm="RandomForestRegressor",
        dataset_size=len(dataset),
        mae=float(mae),
        mse=float(mse),
        r2=float(r2),
        training_data_hash=dataset_hash,
        dataset_version="v1",
    )
    print(f"Trained TransitionModel V1 and saved to {output_path}")


if __name__ == "__main__":
    main()
