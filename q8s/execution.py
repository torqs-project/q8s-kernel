import base64
from json import JSONEncoder, loads
import logging
import os
import random
import string
from time import sleep
from dotenv import dotenv_values
from kubernetes import client, config, watch
import pluggy
from rich.progress import Progress

from q8s.constants import WORKSPACE
from q8s.enums import Target
from q8s.plugins.job_template_spec import JobTemplatePluginSpec
from q8s.plugins.cpu_job import CPUJobTemplatePlugin
from q8s.plugins.cuda_job import CUDAJobTemplatePlugin
from q8s.utils import extract_non_none_value


def load_env():
    env = dotenv_values(".env.q8s")

    return env


class K8sContext:
    container_image: str | None = None
    registry_pat: str | None = None
    jupyter_logger: None
    target: Target = Target.gpu
    jm: pluggy.PluginManager = pluggy.PluginManager("q8s")
    __progress: Progress | None

    def __init__(self, kubeconfig: str, logger=None, progress: Progress = None):
        """
        Initialize the Kubernetes context.
        """
        self.__progress = progress

        self.jm.add_hookspecs(JobTemplatePluginSpec)
        self.jm.register(CPUJobTemplatePlugin())
        self.jm.register(CUDAJobTemplatePlugin())

        task_config = self.__progress.add_task(
            "[cyan]Loading configuration...", total=1
        )

        config.load_kube_config(kubeconfig)
        self.__progress.console.print("Cluster configuration loaded")
        self.__progress.update(task_config, completed=True)

        _, active_context = config.list_kube_config_contexts(config_file=kubeconfig)

        try:
            self.namespace = active_context["context"]["namespace"]
        except KeyError:
            self.namespace = "default"
        self.__progress.console.print(f"Active namespace: {self.namespace}")

        self.core_api_instance = client.CoreV1Api()
        self.batch_api_instance = client.BatchV1Api()

        self.name = f"qubernetes-job-{K8sContext.get_id()}"

        self.__env = load_env()

        self.jupyter_logger = logger

    @staticmethod
    def get_id():
        """
        Generate a random ID.
        """
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

    def set_container_image(self, image: str):
        self.container_image = image

    def set_registry_pat(self, pat: str):
        self.registry_pat = pat

    def set_target(self, target: Target):
        self.target = target

    def create_job_object(self, code: str) -> client.V1Job:
        return None

    def __registry_credentials_secret_name(self):
        return f"{self.name}-regcred"

    def __create_job_object(self, code: str):
        """
        Create a job object with the given code.
        """
        prepare_task = self.__progress.add_task("[cyan]Prepare job...", total=1)
        env = self.__prepare_environment()

        self.jm.hook.prepare(
            target=self.target, name=self.name, namespace=self.namespace, env=self.__env
        )

        template = extract_non_none_value(
            self.jm.hook.makejob(
                code=code,
                env=env,
                container_image=self.container_image,
                target=self.target,
                registry_credentials_secret_name=self.__registry_credentials_secret_name(),
                name=self.name,
                registry_pat=self.registry_pat,
            )
        )

        # Create the specification of deployment
        spec = client.V1JobSpec(template=template)  # , ttl_seconds_after_finished=10

        # Instantiate the job object
        job_spec = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=self.name,
                namespace=self.namespace,
                labels={"qubernetes.dev/job.type": "jupyter"},
            ),
            spec=spec,
        )

        job = self.batch_api_instance.create_namespaced_job(
            body=job_spec, namespace=self.namespace
        )
        self.__progress.console.print("Job created")

        self.__create_config_map_object(code, job)
        self.__progress.console.print("Application code created")
        self.__create_environment_secret()
        self.__progress.console.print("Environment variables created")

        if self.registry_pat:
            self.__create_registry_credentials_secret()

        self.__progress.advance(prepare_task, 1)
        return job

    def __create_config_map_object(self, code: str, job: client.V1Job):
        """
        Create a ConfigMap object with the given code.
        """
        # Configureate ConfigMap from a local file
        configmap = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            data={"main.py": code},
            metadata=client.V1ObjectMeta(
                name=self.name,
                owner_references=[
                    client.V1OwnerReference(
                        api_version="batch/v1",
                        kind="Job",
                        name=job.metadata.name,
                        uid=job.metadata.uid,
                        # block_owner_deletion=True,
                        # controller=True,
                    )
                ],
            ),
        )

        self.core_api_instance.create_namespaced_config_map(
            namespace=self.namespace, body=configmap
        )

    def __create_environment_secret(self):
        """
        Create a Secret object with the environment variables.
        """
        data = {}

        for key in self.__env.keys():
            data[key] = base64.b64encode(self.__env[key].encode()).decode()

        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            type="Opaque",
            immutable=True,
            data=data,
            metadata=client.V1ObjectMeta(
                name=self.name,
                namespace=self.namespace,
                # owner_references=[
                #     client.V1OwnerReference(
                #         api_version="v1",
                #         kind="Job",
                #         name=job.metadata.name,
                #         uid=job.metadata.uid,
                #         # block_owner_deletion=True,
                #         # controller=True,
                #     )
                # ],
            ),
        )

        self.core_api_instance.create_namespaced_secret(
            namespace=self.namespace, body=secret
        )

    def __create_registry_credentials_secret(self):
        """
        Create a Secret object with the registry credentials.
        """
        segments = self.container_image.split("/")
        # Find user name for images on Docker Hub
        username = segments[0] if len(segments) == 2 else segments[1]
        registry = segments[0] if len(segments) == 3 else "https://index.docker.io/v1/"

        config = {
            "auths": {
                registry: {
                    "auth": base64.b64encode(
                        f"{username}:{self.registry_pat}".encode()
                    ).decode(),
                }
            }
        }

        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            type="kubernetes.io/dockerconfigjson",
            immutable=True,
            metadata=client.V1ObjectMeta(
                name=self.__registry_credentials_secret_name(),
                namespace=self.namespace,
            ),
            data={
                ".dockerconfigjson": base64.b64encode(
                    JSONEncoder().encode(config).encode()
                ).decode(),
            },
        )

        self.core_api_instance.create_namespaced_secret(
            namespace=self.namespace, body=secret
        )

    def __delete_job(self):
        """
        Delete the job and its associated resources.
        """
        cleanup_task = self.__progress.add_task("[cyan]Cleaning up...", total=1)

        if self.registry_pat:
            self.core_api_instance.delete_namespaced_secret(
                self.__registry_credentials_secret_name(), self.namespace
            )
            self.__progress.console.print("Registry credentials removed")

        self.core_api_instance.delete_namespaced_secret(self.name, self.namespace)
        self.__progress.console.print("Environment variables removed.")

        self.core_api_instance.delete_namespaced_config_map(
            self.name,
            self.namespace,
            body=client.V1DeleteOptions(propagation_policy="Foreground"),
        )
        self.__progress.console.print("Application code removed.")

        self.jm.hook.cleanup(name=self.name, namespace=self.namespace)

        api_response = self.batch_api_instance.delete_namespaced_job(
            self.name,
            self.namespace,
            body=client.V1DeleteOptions(propagation_policy="Foreground"),
            _preload_content=False,
        )

        try:
            data = loads(api_response.data)

            self.__progress.console.print(
                f"Job removed. status='{data['status']['conditions'][0]['type']}'"
            )
        except:
            self.__progress.console.print(
                f"Job removed. status='{str(api_response.status)}'"
            )
        finally:
            self.__progress.advance(cleanup_task, 1)

    def __get_job_logs(self, name="qiskit-aer-gpu"):
        """
        Get the logs of the job.
        """
        api_response = self.core_api_instance.read_namespaced_pod_log(
            name=name, namespace=self.namespace
        )
        logging.debug("Job logs='%s'" % str(api_response))
        return api_response

    def __get_pods_in_job(self):
        """
        Get the pods in the job.
        """
        pods = self.core_api_instance.list_namespaced_pod(
            self.namespace, label_selector=f"app={self.name}"
        )

        pod_name = pods.items[0].metadata.name

        return pod_name

    def __complete_and_get_job_status(self):
        """
        Wait for the job to complete and get its status.
        """
        result = "stdout"

        execute_task = self.__progress.add_task("[cyan]Executing job...", total=1)

        w = watch.Watch()

        for event in w.stream(
            self.batch_api_instance.list_namespaced_job,
            namespace=self.namespace,
            label_selector=f"qubernetes.dev/job.type=jupyter",
        ):
            if event["object"].metadata.name == self.name:

                # Job execution completed
                if event["object"].status.active is None:
                    # Failed
                    if event["object"].status.conditions is None:
                        message = "Failed"
                        color = "red"
                        w.stop()
                        result = "stderr"

                    # Succeeded
                    else:
                        message = event["object"].status.conditions[-1].type
                        color = "green"

                        if event["object"].status.conditions[-1].type == "Complete":
                            w.stop()
                # Job schedukled
                elif event["type"] == "ADDED":
                    message = "Scheduled"
                    color = "orange3"
                # Job running
                else:
                    message = "Running"
                    color = "yellow"

                if self.jupyter_logger is None:
                    self.__progress.update(
                        execute_task,
                        description=f"[cyan]Executing job... [{color}]{message}",
                    )
                else:
                    self.jupyter_logger(f"Pod status: {message}")

        self.__progress.advance(execute_task, 1)

        return result

    def __prepare_environment(self):
        """
        Prepare the environment variables.
        """
        env = []

        for key in self.__env.keys():
            env.append(
                client.V1EnvVar(
                    name=key,
                    value_from=client.V1EnvVarSource(
                        secret_key_ref=client.V1SecretKeySelector(
                            name=self.name, key=key
                        )
                    ),
                )
            )

        return env

    def execute(self, code: str) -> tuple[str, str]:
        """
        Execute the given code.
        """

        try:
            self.__create_job_object(code=code)

            if self.jupyter_logger is not None:
                self.jupyter_logger(f"Job {self.name} created")

            stream = self.__complete_and_get_job_status()

            job = self.__get_pods_in_job()
            logs = self.__get_job_logs(job)
            self.__progress.console.print("Fetched job logs")

            return logs, stream
        except KeyboardInterrupt:
            return "Task interrupted by user", "stderr"
        except:
            return "An error occurred.", "stderr"
        finally:
            self.__delete_job()
            pass

    def abort(self):
        """
        Abort the execution.
        """
        self.__delete_job()
