from testbook import testbook
from time import time
import csv

with open("results.csv", "w", newline="") as csvfile:
    fieldnames = ["iteration", "reps", "overhead", "simulator"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    @testbook("test_QAOA_depth.ipynb", execute=True)
    def warm_up(tb):
        pass

    warm_up()

    for reps in range(2, 30):
        for iteration in range(1, 11):

            @testbook("test_QAOA_depth.ipynb", execute=True, timeout=1000)
            def test(tb):
                start = time()
                func = tb.get("test_function")

                simulator = func(reps)
                writer.writerow(
                    {
                        "iteration": iteration,
                        "reps": reps,
                        "overhead": time() - start - simulator,
                        "simulator": simulator,
                    }
                )

            test()
            print(f"Finished iteration {iteration} for {reps} reps")