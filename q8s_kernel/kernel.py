import os
from time import time
from ipykernel.kernelbase import Kernel
import logging
import subprocess
from .k8s import execute

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

        logging.info("q8s kernel starting")
        # logging.info(kwargs)
        if True:
            self.temp_dir = (
                # "/var/folders/8n/b8xghht90n19tx0nqqx9qlk80000gp/T/tmp8hytthj6"
                "/Users/stirbuvl/Documents/code/torqs/vscode-q8s-kernel/benchmark/.docker"
            )
        else:
            self.temp_dir = create_temp_directory()
            print(self.temp_dir)
            exit(1)

    def do_execute(
        self,
        code,
        silent,
        store_history=True,
        user_expressions=None,
        allow_stdin=False,
    ):

        if USE_KUBERNETES:
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
                    self.temp_dir,
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
        else:
            if not silent:
                # Write the code to a new Python file
                with open("temp.py", "w") as f:
                    f.write(code)

            # Use subprocess to execute the file and capture the output and possible errors
            result = subprocess.run(
                ["python", "temp.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            output = result.stdout.decode("utf-8")
            errors = result.stderr.decode("utf-8")

            stream_content = {"name": "stdout", "text": output}
            self.send_response(self.iopub_socket, "stream", stream_content)

            if errors:
                error_content = {"name": "stderr", "text": errors}
                self.send_response(self.iopub_socket, "stream", error_content)

            # Log the output and errors to the console and write them to a file
            logging.info(output)
            logging.error(errors)
            with open("output.txt", "a") as f:
                print(output, file=f)
                if errors:
                    print(errors, file=f)

        logging.info("Execution complete")
        return {
            "status": "ok",
            # The base class increments the execution count
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }
