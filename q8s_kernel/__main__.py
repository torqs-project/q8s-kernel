from . import Q8sKernel

from ipykernel.kernelapp import IPKernelApp
IPKernelApp.launch_instance(kernel_class=Q8sKernel)