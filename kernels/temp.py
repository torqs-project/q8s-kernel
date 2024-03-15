import pennylane as qml
from pennylane import numpy as np

dev = qml.device("default.qubit", wires=2, shots=100)

@qml.qnode(dev)
def circuit():
    qml.Hadamard(wires=0)
    qml.CNOT(wires=[0, 1])
    return qml.sample(qml.PauliZ(0)), qml.sample(qml.PauliZ(1))

result = circuit()
isBell = np.all(result[0] == result[1])

print(isBell)
# Count occurrences of "00" and "11"
count_00 = np.sum(result[0] == 1)
count_11 = np.sum(result[1] == -1)

print("Count of '00':", count_00)
print("Count of '11':", count_11)