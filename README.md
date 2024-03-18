# vscode-q8s-kernel
Kernel extension for executing quantum programs in simulators on q8s clusters

## Development

Install dependencies:

```pip install -r requirements.txt```

The jupyter kernel needs to be installed locally for jupyter notebook to find it. To install the q8s-kernel use the following command from the q8s-kernel directory:

```jupyter kernelspec install ./kernels --name=q8s-kernel --user```
