from enum import Enum


class Target(str, Enum):
    cpu = "cpu"
    gpu = "gpu"
    qpu = "qpu"
