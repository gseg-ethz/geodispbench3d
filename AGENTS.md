# AGENTS.md

## Core principle

This project uses a dedicated Conda environment.

NEVER use system Python or the base Conda environment.

All Python commands MUST use:

    conda run -n iof3d_cosicorr3d-dev312 ...

## Python environment

- Environment name: `iof3d_cosicorr3d-dev312`
- Interpreter (reference): `/scratch/miniconda3/envs/iof3d_cosicorr3d-dev312/bin/python`

The same env that powers iof3D currently powers geodispbench3d development.
A leaner env (without iof3D's full stack) will exist once iof3D is on PyPI;
until then, develop here.

## Common commands

```
# Install the framework editable (no tool extras)
conda run -n iof3d_cosicorr3d-dev312 pip install -e .[dev]

# Install with iof3D adapter
conda run -n iof3d_cosicorr3d-dev312 pip install -e .[iof3d,dev]

# Run tests for one extra
conda run -n iof3d_cosicorr3d-dev312 pytest tests/core -v
conda run -n iof3d_cosicorr3d-dev312 pytest tests/f2s3 -v

# Run all tests (extras-aware; the iof3d/f2s3 dirs self-skip)
conda run -n iof3d_cosicorr3d-dev312 pytest

# Sanity-check an env
conda run -n iof3d_cosicorr3d-dev312 python -c "import sys; print(sys.executable)"
```

## Forbidden

- Do not call bare `python` / `pip` / `pytest`
- Do not install into the `base` env
- Do not assume implicit env activation
