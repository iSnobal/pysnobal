# Copilot Instructions for PySnobal

## Repository Description
PySnobal is the Python wrapper for the **Snobal** snow mass and energy balance models.
It provides the interface for running the C-based logic, translating high-level data structures
into the low-level formats required by the physics engine. It is a core component of the
**Automated Water Supply Model (iSnobal/awsm)** ecosystem.

## Repository Structure
The project follows a modular Python package structure with a deeply integrated C/Cython physics core:
- `pysnobal/`: Main package directory.
  - `pysnobal.py`: Entry point for **1D Point Modeling**. Contains CLI and API for running Snobal at a single location.
  - `ipysnobal.py`: Entry point for **2D Spatial Modeling**. Orchestrates grid-based simulations.
  - `c_snobal/`: Core physics engine and bindings.
    - `snobal.pyx`: Main Cython wrapper defining the Python-to-C interface.
    - `libsnobal/`: Extensive collection of C source files (e.g., `_e_bal.c`, `_mass_bal.c`, `init_snow.c`) implementing the snowpack physics.
    - `h/`: C header files defining model structures and constants.
  - `utils.py`: Unit conversion and mathematical helpers.
- `tests/`: Unit and integration tests (using `pytest`).
- `config/`: Sample YAML configuration files for point model runs.
- `notebooks/`: Documentation and workflow examples in Jupyter format.
- `pyproject.toml` & `Makefile`: Build system automation and task management.
- `setup.py`: Build instructions for compiling the Cython and C extensions.

## Key Guidelines

### 1. Code Style & Standards
Adhere to the specialized iSnobal organization agents defined in **`iSnobal/.github`**:
- **Python Style**: Follow `@iSnobal/.github/instructions/python-style-agent.md` for Ruff formatting and mandatory type hints.
- **Legacy Migration**: Consult `@iSnobal/.github/instructions/legacy-migrator-agent.md` when refactoring core model wrappers.
- **Documentation**: Follow `@iSnobal/.github/instructions/documentation-agent.md` for NumPy-style docstrings.
- **Dependencies**: Consult `@iSnobal/.github/instructions/dependency-modernization-agent.md` for Conda-based management. Note: Requires `numpy<1.23`.
- **Performance & C/Cython**: Use `@iSnobal/.github/instructions/performance-cython-agent.md` for C/Cython optimizations and memory management.
- **Snow Physics**: Defer to `@iSnobal/.github/instructions/snow-physics-agent.md` for physical correctness in energy/mass balance logic.

### 2. Domain Context
- **Dual Modeling Entry Points**: 
    1. **Point Model (1D)**: Handled via `pysnobal.py` for local simulations.
    2. **Spatial Model (2D)**: Handled via `ipysnobal.py` for grid-based simulations (orchestrated by AWSM).
- **Core Engine Integration**: Both entry points interface with the same underlying C physics engine. The primary responsibility of the Python layer is the transformation and orchestration of high-level data structures (e.g. NumPy arrays) into memory-compatible inputs for the model.
- **Physical Consistency**: Maintains standard units and physical constants across forcing inputs and model states. This includes required unit scaling and translations (e.g. Celsius to Kelvin) to satisfy the physics engine requirements.
- **Ecosystem Role**:
    - **AWSM** (Orchestrator) → calls **PySnobal** (Wrapper/Engine) → which uses **SMRF** (Forcing Data).

### 3. Review Style
- **Conciseness**: Be short and concise; explain the "why" behind recommendations.
- **Clarification**: Ask clarifying questions when code intent is unclear.
- **Efficiency**: Do not repeat comments that were previously resolved on new pushes.
- **Context**: Do not repeat any information that was already in the PR description.
- **Prioritization**: Focus on logic and physical correctness over purely technical changes.

### 4. Testing & Build
Follow the specialized `@iSnobal/.github/instructions/testing-coverage-agent.md`:
- **Framework**: Use `pytest` for all tests.
- **Location**: Place new tests in `tests/`.
- **Execution**:
  - Build extensions and run all tests: `make build tests`
  - Clean build artifacts: `make clean`
  - Generate docs: `make docs`