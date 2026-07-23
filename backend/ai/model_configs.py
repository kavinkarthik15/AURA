MODEL_VERSION = "v1"

FEATURES = [
    "python",
    "machine_learning",
    "dsa",
    "projects",
    "communication",
]

TARGETS = [
    "python_growth",
    "machine_learning_growth",
    "dsa_growth",
    "project_growth",
]

ACTION_ID_MAP = {
    "build python project": 0,
    "python project": 0,
    "hackathon": 1,
    "participate in hackathon": 1,
    "internship": 2,
    "complete internship": 2,
    "course": 3,
    "python course": 3,
    "dsa course": 3,
    "machine learning course": 3,
    "mock interview": 4,
    "attend mock interview": 4,
    "research paper": 5,
    "read research paper": 5,
    "research paper review": 5,
}

TARGET_ALIASES = {
    "python_growth": "python",
    "machine_learning_growth": "machine_learning",
    "dsa_growth": "dsa",
    "project_growth": "projects",
}
