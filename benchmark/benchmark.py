from testbook import testbook
from time import sleep
import timeit
import csv
import re
import mlflow
import os

TIMEOUT = 60000
SUITE = "QAOA"
KERNEL_NAME = "q8s-kernel"
# KERNEL_NAME = "python"
NOTEBOOK = f"test_{SUITE}.ipynb"
DEVICE = "GPU"
TARGET = "local"
TARGET = "puzl"
TARGET = "do"
ITERATIONS = 1
MEMORY = "16Gi"

os.environ["Q8S_BECHMARK"] = "1"

if TARGET == "local":
    os.environ["KUBECONFIG"] = (
        "/Users/stirbuvl/Documents/code/torqs/vscode-q8s-kernel/config.local"
    )
    os.environ["NAMESPACE"] = "default"
elif TARGET == "do":
    os.environ["KUBECONFIG"] = (
        "/Users/stirbuvl/Documents/code/torqs/vscode-q8s-kernel/config.do"
    )
    os.environ["NAMESPACE"] = "default"
else:
    os.environ["KUBECONFIG"] = (
        "/Users/stirbuvl/Documents/code/torqs/vscode-q8s-kernel/config.puzl"
    )
    os.environ["NAMESPACE"] = "76bb4952-43cd-4332-b24c-b45afd727d3c"
os.environ["MEMORY"] = MEMORY


test = re.search(r"test_(\w+).ipynb", NOTEBOOK).group(1)

# RESULTS = f"results/{test}.{KERNEL_NAME}.nou.csv"
RESULTS = f"result.csv"

# Set our tracking server uri for logging
mlflow.set_tracking_uri(uri="http://127.0.0.1:8080")

# Create a new MLflow Experiment
mlflow.set_experiment(f"{SUITE} - {KERNEL_NAME} - {TARGET}")

with mlflow.start_run():
    mlflow.log_param("kernel", KERNEL_NAME)
    mlflow.log_param("notebook", NOTEBOOK)
    mlflow.log_param("memory", MEMORY)
    mlflow.log_param("iterations", ITERATIONS)
    mlflow.log_param("device", DEVICE)
    mlflow.log_param("target", TARGET)

    with open(RESULTS, "w", newline="") as csvfile:
        fieldnames = ["iteration", "qubits", "overhead", "simulator"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        @testbook(NOTEBOOK, execute=True, timeout=TIMEOUT, kernel_name=KERNEL_NAME)
        def warm_up(tb):
            pass

        warm_up()

        for qubits in range(3, 4):
            for iteration in range(1, ITERATIONS + 1):
                print(f"Starting iteration {iteration} for {qubits} qubits.")
                sleep(5)

                @testbook(
                    NOTEBOOK, execute=True, timeout=TIMEOUT, kernel_name=KERNEL_NAME
                )
                def test(tb):
                    start = timeit.default_timer()
                    func = tb.get("test_function")

                    simulator = func(qubits, device=DEVICE)
                    now = timeit.default_timer()
                    writer.writerow(
                        {
                            "iteration": iteration,
                            "qubits": qubits,
                            "overhead": now - start - simulator,
                            "simulator": simulator,
                        }
                    )
                    csvfile.flush()

                    return now - start

                res = test()
                print(
                    f"Finished iteration {iteration} for {qubits} qubits in {res} seconds."
                )

    mlflow.log_artifact(RESULTS)
