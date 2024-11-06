# q8s

Toolset for executing quantum jobs on [Qubernetes](https://www.qubernetes.dev).

## Installation

Install the for project folder:

```bash
pip install q8s
```

## Usage

### CLI

Sumbit a job to the Qubernetes cluster:

```bash
q8sctl execute app.py --kubeconfig /path/to/kubeconfig
```

For more options, run:

```bash
q8sctl execute --help
```

### Jupyter Notebook

Install the `q8s-kernel`:

```bash
q8sctl jupyter --install
```

Start the jupyter notebook server:

```bash
jupyter notebook
```

or the jupyter lab server:

```bash
jupyter lab
```

Select the `Q8s kernel` when creating a new notebook.

## Development

### Prerequisites

The development environment requires the following tools to be installed:

- [Docker](https://www.docker.com/get-started)

### Setup

Install the project in editable mode:

```bash
pip install -e .
```

If the project is installed in a virtual environment, the `q8s-kernel` can be installed by running the following command:

```bash
q8sctl jupyter --install
```
