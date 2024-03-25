from testbook import testbook
from time import time
import csv

with open("results.csv", "w", newline="") as csvfile:
    fieldnames = ["iteration", "qubits", "overhead", "simulator"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    @testbook("test.ipynb", execute=True)
    def warm_up(tb):
        pass

    warm_up()

    for qubits in range(1, 21):
        for iteration in range(1, 11):

            @testbook("test.ipynb", execute=True, timeout=600)
            def test(tb):
                start = time()
                func = tb.get("test_function")

                simulator = func(qubits)
                writer.writerow(
                    {
                        "iteration": iteration,
                        "qubits": qubits,
                        "overhead": time() - start - simulator,
                        "simulator": simulator,
                    }
                )

            test()
            print(f"Finished iteration {iteration} for {qubits} qubits")
