from __future__ import annotations

from pathlib import Path

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from backend.ai.transition_model import TransitionModel, load_training_dataset


def main() -> None:
    dataset = load_training_dataset()
    model = TransitionModel()
    features, targets = model._build_training_arrays(dataset)

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        targets,
        test_size=0.2,
        random_state=42,
    )

    model.model.fit(X_train, y_train)
    predictions = model.model.predict(X_test)

    report = {
        "mae": float(mean_absolute_error(y_test, predictions)),
        "mse": float(mean_squared_error(y_test, predictions)),
        "r2": float(r2_score(y_test, predictions)),
    }

    print(report)


if __name__ == "__main__":
    main()
