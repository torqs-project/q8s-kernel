import os
from time import time
from ipykernel.kernelbase import Kernel
import logging

from q8s.kernel import Q8sKernel

from .k8s import execute

CODE = ["test_function", "import json; json.dumps(test_function)"]


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


if os.environ.get("Q8S_BENCHMARK") == "1":
    Q8sKernel.do_execute = do_execute
