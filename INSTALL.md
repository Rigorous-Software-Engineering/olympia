# Installation

## Requirements

- Linux
- Python 3.7+ (with `pip` and optionally `venv`)
- Z3 solver

Additionally, to run the supported fuzzers on the generated benchmarks, the
following requirement should be fulfilled:

- Docker

## Clone repository

To start building Olympia, first clone the git repository:

```bash
$ git clone https://github.com/Rigorous-Software-Engineering/olympia
$ cd olympia
```

## Installing Dependencies

To install dependencies we use `pip` (the package installer for Python).
Our recommendation is to generate a virtual environment before installing the
dependencies:

```bash
$ python3 -m venv ./env
$ source ./env/bin/activate
```

Now after optionally activating the local python environment (indicated by the `(env)` prefix), run the following
command inside the `olympia` directory:

```bash
(env) $ python3 -m pip install -r ./requirements.txt
```

Additionally, you will need to have the Z3 solver installed for handling `.smt2` files from CVEs.
Below are the instructions for installing the Z3 solver using pySMT's
install command.
Note, that pySMT should have been installed in the previous step as one of the dependencies for Olympia.

```bash
$ pysmt-install --z3
```

To check that the solver was installed correctly, you can use the following
command:

```bash
$ pysmt-install --check
```

## Building Docker Images

To run the fuzzers on the generated benchmark, you must first build the
corresponding docker images:

```bash
$ ./scripts/build_all_dockers.sh
```

Note that this may take a few hours depending on your machine.

-----

To see if everything was installed correctly try to run the [basic example](README.md#basic-usage-example)
from the provided `README.md`.
