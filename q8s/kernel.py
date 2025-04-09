import os
from ipykernel.kernelbase import Kernel
from ipykernel.comm import CommManager
from rich.progress import Progress, SpinnerColumn, TextColumn
import logging

from q8s.enums import Target
from q8s.execution import K8sContext
from q8s.project import CacheNotBuiltException, Project, ProjectNotFoundException

FORMAT = "[%(levelname)s %(asctime)-15s q8s_kernel] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)

CODE = ["test_function", "import json; json.dumps(test_function)"]

kernel_comm_identifier = "dev.qubernetes.kernel"


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
    comm_manager: CommManager = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__initialize_comm_manager()

        self.docker_image = os.environ.get("DOCKER_IMAGE", None)
        kubeconfig = os.environ.get("KUBECONFIG", None)

        if kubeconfig is None:
            logging.error("KUBECONFIG not set")
            exit(1)

        if self.docker_image is None:
            logging.error("DOCKER_IMAGE not set")
            exit(1)

        self.k8s_context = K8sContext(
            kubeconfig,
            self.progress,
            Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                expand=True,
            ),
        )
        self.k8s_context.set_container_image(self.docker_image)
        self.k8s_context.set_registry_pat(os.environ.get("REGISTRY_PAT", None))

        logging.info("q8s kernel started")
        logging.info(f"docker image: {self.docker_image}")

    def __initialize_comm_manager(self):
        self.comm_manager = CommManager(
            kernel=self,
        )

        # Register a comm target
        self.comm_manager.register_target(kernel_comm_identifier, self._on_comm_open)

        # Register the comm_open handler
        self.shell_handlers["comm_open"] = self.comm_manager.comm_open
        self.shell_handlers["comm_msg"] = self.comm_manager.comm_msg
        self.shell_handlers["comm_close"] = self.comm_manager.comm_close

    def do_execute(
        self,
        code,
        silent,
        store_history=True,
        user_expressions=None,
        allow_stdin=False,
    ):
        logging.debug(f"Executing code:\n{code}")

        output, stream_name = self.k8s_context.execute(code)

        self.send_response(self.iopub_socket, "clear_output", {"wait": True})

        logging.debug(output)
        logging.debug(stream_name)

        for line in output.split("\n"):
            if line.startswith("data:image/png;base64,"):
                self.send_response(
                    self.iopub_socket,
                    "display_data",
                    {
                        "data": {"image/png": line[22:]},
                        "metadata": {},
                    },
                )
            elif line.startswith("data:image/jpeg;base64,"):
                self.send_response(
                    self.iopub_socket,
                    "display_data",
                    {
                        "data": {"image/jpeg": line[23:]},
                        "metadata": {},
                    },
                )
            elif line.startswith("data:image/svg+xml;base64,"):
                self.send_response(
                    self.iopub_socket,
                    "display_data",
                    {
                        "data": {"image/svg+xml": line[25:]},
                        "metadata": {},
                    },
                )
            else:
                self.send_response(
                    self.iopub_socket,
                    "display_data",
                    {
                        "data": {"text/plain": line},
                        "metadata": {},
                    },
                )

        return {
            "status": "ok",
            # The base class increments the execution count
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }

    def progress(self, msg):
        self.send_response(
            self.iopub_socket,
            "display_data",
            {
                "data": {"text/plain": msg},
                "metadata": {},
            },
        )

    def _on_comm_open(self, comm, msg):
        """Handle the frontend opening a Comm"""
        logging.info("Comm opened by frontend")
        logging.info(f"Comm ID: {comm.comm_id}")

        # Send a message to the frontend with the current state of the kernel
        comm.send(
            {
                "command": "init",
                "targets": Project().configuration.targets.keys(),
                "selected_target": self.k8s_context.target.name,
            }
        )

        @comm.on_msg
        def _recv(msg):
            data = msg["content"]["data"]
            logging.info(f"Received from frontend: {data}")

            # Respond to the frontend
            if data["command"] == "set_target":
                self.k8s_context.set_target(Target(data["payload"]["target"]))
                project = Project()
                image = project.cached_images(data["payload"]["target"])
                self.k8s_context.set_container_image(image)
                logging.info(f"Updated execution target to {data['payload']['target']}")
            else:
                logging.warning(f"Unknown command: {data['command']}")

        @comm.on_close
        def _closed(msg):
            logging.info("Comm closed by frontend")
