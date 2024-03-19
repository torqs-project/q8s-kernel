# vscode-q8s-kernel
Kernel extension for executing quantum programs in simulators on q8s clusters

## Installation

Install the for project folder:
    
```bash
pip install .
```

## Development

### Prerequisites

The development environment requires the following tools to be installed:

- [Docker](https://www.docker.com/get-started)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)

### Setup

Install dependencies:

```pip install -r requirements.txt```

The jupyter kernel needs to be installed locally for jupyter notebook to find it. To install the q8s-kernel when using a virtual environment, run the following command:

```bash
jupyter kernelspec install . --name=q8s-kernel --sys-prefix
```

otherwise, run the following command:

```bash
jupyter kernelspec install . --name=q8s-kernel --user
```

Start the jupyter notebook server:

```bash
jupyter notebook
```

or the jupyter lab server:

```bash
jupyter lab
```
