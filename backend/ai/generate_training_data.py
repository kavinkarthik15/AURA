from backend.ai.dataset_builder import builder


def main() -> None:
    dataset = builder.build_training_dataset()
    builder.save_training_dataset(dataset)
    print(f"Generated {len(dataset)} transition samples")


if __name__ == "__main__":
    main()
