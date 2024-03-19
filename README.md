# vscode-q8s-kernel
Kernel extension for executing quantum programs in simulators on q8s clusters

## Development

### Prerequisites

The development environment requires the following tools to be installed:

- [Docker](https://www.docker.com/get-started)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)

### Setup

Install dependencies:

```pip install -r requirements.txt```

The jupyter kernel needs to be installed locally for jupyter notebook to find it. To install the q8s-kernel use the following command from the q8s-kernel directory:

```jupyter kernelspec install . --name=q8s-kernel --user```

Start the jupyter notebook server:

```jupyter notebook```

or the jupyter lab server:

```jupyter lab```
