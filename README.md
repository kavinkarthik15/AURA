# AURA

AURA is an adaptive personal intelligence system focused on reasoning, planning, memory, and continual learning. The project explores how an agent can improve over time by capturing experiences, evaluating policies, and refining its decision-making process.

## Overview

AURA combines several research-oriented components:

- Experience-based learning and memory
- Planning and policy evaluation
- Retrieval-augmented reasoning
- Counterfactual and contradiction analysis
- Benchmarking and experiment tracking

The repository is organized as a prototype platform with backend services, AI modules, tests, documentation, and experiment artifacts.

## Project Structure

- backend/ – core services, AI reasoning modules, and tests
- docs/ – architecture notes, design documents, and research writeups
- experiments/ – experiment definitions and outputs
- database/ – schema and database design artifacts
- frontend/ – frontend assets (if present in future iterations)

## Requirements

- Python 3.13+
- pip

## Quickstart

1. Clone the repository
   ```bash
   git clone https://github.com/kavinkarthik15/AURA.git
   cd AURA
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements-dev.txt
   ```

4. Run the basic backend entry point
   ```bash
   python backend/main.py
   ```

## Testing

Run the test suite with:

```bash
pytest backend/tests
```

## Development Notes

The project uses:

- pytest for tests
- ruff for linting
- black for formatting
- mypy for typing checks

## Documentation

Additional documentation is available in the docs/ directory, including architecture and research notes.

## License

This repository does not currently specify a license. If you plan to share or distribute it publicly, consider adding an explicit license file.
