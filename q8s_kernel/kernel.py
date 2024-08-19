import os
from time import time
from ipykernel.kernelbase import Kernel
import logging
from .k8s import execute
from kubernetes import config

USE_KUBERNETES = True
FORMAT = "[%(levelname)s %(asctime)-15s q8s_kernel] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)

CODE = ["test_function", "import json; json.dumps(test_function)"]


class Q8sKernel(Kernel):
    implementation = "q8s-kernel"
    implementation_version = "0."
    language = "no-op"
    language_version = "0.1"
    language_info = {
        "name": "Any text",
        "mimetype": "text/plain",
        "file_extension": ".txt",
    }
    banner = "q8s"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.docker_image = os.environ.get("DOCKER_IMAGE", "vstirbu/benchmark-deps")
        kubeconfig = os.environ.get("KUBECONFIG", None)

        if kubeconfig is None:
            logging.error("KUBECONFIG not set")
            exit(1)

        config.load_kube_config(kubeconfig)

        logging.info("q8s kernel started")
        logging.info(f"docker image: {self.docker_image}")

    def do_execute(
        self,
        code,
        silent,
        store_history=True,
        user_expressions=None,
        allow_stdin=False,
    ):
        logging.info(f"Executing code:\n{code}")
        output, stream_name = execute(
            code,
            None,
            self.docker_image,
            registry_pat=os.environ.get("REGISTRY_PAT", None),
        )

        logging.debug(output)
        logging.debug(stream_name)

        stream_content = {
            "name": stream_name,
            "text": output,
        }
        self.send_response(self.iopub_socket, "stream", stream_content)

        return {
            "status": "ok",
            # The base class increments the execution count
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }


# handles the testbook get protocol
def do_execute(
    self: Kernel,
    code,
    silent,
    store_history=True,
    user_expressions=None,
    allow_stdin=False,
):

    logging.debug(f"Executing code:\n{code}")

    if code == "test_function":
        stream_content = {
            "name": "stdout",
            "text": "<function __main__.test_function()>",
        }
        self.send_response(self.iopub_socket, "stream", stream_content)
    elif code.startswith("\ntest_function("):
        logging.debug("execute test_function")
        start = time()
        output, stream_name = execute(
            self.code + "\nprint(" + code.strip() + ")",
            None,
            os.environ["DOCKER_IMAGE"],
        )

        logging.debug(output)
        logging.debug(stream_name)
        self.output = output

        stream_content = {
            "name": stream_name,
            # "text": output + f"\nExecution time: {time() - start:.2f} seconds",
            "text": output,
        }
        # self.send_response(self.iopub_socket, "stream", stream_content)
        self.send_response(
            self.iopub_socket,
            "execute_result",
            {
                "data": {
                    "application/json": {
                        "value": output,
                    }
                },
                "metadata": {},
                "execution_count": self.execution_count,
            },
        )
    elif code.startswith("\nimport json"):
        self.send_response(
            self.iopub_socket,
            "execute_result",
            {
                "data": {
                    "application/json": {
                        "value": float(self.output),
                    }
                },
                "metadata": {},
                "execution_count": self.execution_count,
            },
        )
    elif code.startswith("import json; json.dumps(test_function)"):
        stream_content = {
            "name": "stderr",
            "text": "TypeError: Object of type function is not JSON serializable",
        }
        self.send_response(self.iopub_socket, "stream", stream_content)
    else:
        self.code = code

        stream_content = {"name": "stdout", "text": "Code saved"}
        self.send_response(self.iopub_socket, "stream", stream_content)

    logging.info("Execution complete")
    return {
        "status": "ok",
        # The base class increments the execution count
        "execution_count": self.execution_count,
        "payload": [],
        "user_expressions": {},
    }


if os.environ.get("Q8S_BECHMARK") == "1":
    Q8sKernel.do_execute = do_execute
