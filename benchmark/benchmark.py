from testbook import testbook
from time import time
import csv

with open('results.csv', 'w', newline='') as csvfile:
    fieldnames = ['qubits', 'total', 'simulator']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for qubits in range(1, 5):
        @testbook('test.ipynb', execute=True)
        def test(tb):
            start = time()
            func = tb.get('test_function')

            simulator = func(qubits)
            writer.writerow({'qubits': qubits, 'total': time()-start, 'simulator': simulator})

        test()
