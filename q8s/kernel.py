import os
from ipykernel.kernelbase import Kernel
import logging

from q8s.execution import K8sContext

USE_KUBERNETES = True
FORMAT = "[%(levelname)s %(asctime)-15s q8s_kernel] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)

CODE = ["test_function", "import json; json.dumps(test_function)"]


class Q8sKernel(Kernel):
    implementation = "q8s-kernel"
    implementation_version = "0.1.0"
    language = "no-op"
    language_version = "0.1"
    language_info = {
        "name": "Any text",
        "mimetype": "text/x-python",
        "pygments_lexer": "ipython%d" % 3,
        "file_extension": ".py",
        "nbconvert_exporter": "python",
    }
    banner = "q8s"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.docker_image = os.environ.get("DOCKER_IMAGE", "vstirbu/benchmark-deps")
        kubeconfig = os.environ.get("KUBECONFIG", None)

        if kubeconfig is None:
            logging.error("KUBECONFIG not set")
            exit(1)

        self.k8s_context = K8sContext(kubeconfig, self.progress)
        self.k8s_context.set_container_image(self.docker_image)
        self.k8s_context.set_registry_pat(os.environ.get("REGISTRY_PAT", None))

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

        output, stream_name = self.k8s_context.execute(code)

        self.send_response(self.iopub_socket, "clear_output", {"wait": True})

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

    def progress(self, msg):
        self.send_response(
            self.iopub_socket, "stream", {"name": "stdout", "text": f"{msg}\n"}
        )
