import base64
from json import JSONEncoder, loads
import logging
import os
import random
import string
from time import sleep
from dotenv import dotenv_values
from kubernetes import client, config


FORMAT = "[%(levelname)s %(asctime)-15s q8s_context] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)

MEMORY = os.environ.get("MEMORY", "32Gi")


def load_env():
    env = dotenv_values(".env.q8s")

    # for key in env.keys():
    #     logging.info(f"{key} = {env[key]}")

    return env


class K8sContext:
    container_image: str = "vsirbu/benchmark-deps"
    registry_pat: str | None = None

    def __init__(self, kubeconfig: str):
        config.load_kube_config(kubeconfig)
        logging.info("Kubeconfig loaded")

        _, active_context = config.list_kube_config_contexts(config_file=kubeconfig)

        self.namespace = active_context["context"]["namespace"]
        logging.info("Active namespace: %s" % self.namespace)

        self.core_api_instance = client.CoreV1Api()
        self.batch_api_instance = client.BatchV1Api()

        self.name = f"qubernetes-job-{K8sContext.get_id()}"

        self.__env = load_env()

    @staticmethod
    def get_id():
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

    def set_container_image(self, image: str):
        self.container_image = image

    def set_registry_pat(self, pat: str):
        self.registry_pat = pat

    def create_job_object(self, code: str) -> client.V1Job:
        return None

    def __registry_credentials_secret_name(self):
        return f"{self.name}-regcred"

    def __create_job_object(self, code: str):
        env = self.__prepare_environment()

        # Configureate Pod template container
        container = client.V1Container(
            name=self.name,
            image=self.container_image,
            env=env,
            command=["python3"],
            args=["./app/main.py"],
            resources=client.V1ResourceRequirements(
                limits={
                    "cpu": "2",
                    "ephemeral-storage": "50Gi",
                    # "memory": "64Gi",
                    "memory": MEMORY,
                    "nvidia.com/gpu": "1",
                    # "qubernetes.dev/qpu": "1",
                },
                requests={
                    "cpu": "2",
                    "ephemeral-storage": "0",
                    # "memory": "32Gi",
                    "memory": MEMORY,
                    "nvidia.com/gpu": "1",
                    # "qubernetes.dev/qpu": "1",
                },
            ),
            volume_mounts=[
                client.V1VolumeMount(
                    name="app-volume", mount_path="/app", read_only=True
                )
            ],
        )

        # Create and configurate a spec section
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": self.name}),
            spec=client.V1PodSpec(
                containers=[container],
                image_pull_secrets=(
                    [
                        client.V1LocalObjectReference(
                            name=self.__registry_credentials_secret_name()
                        )
                    ]
                    if self.registry_pat
                    else []
                ),
                runtime_class_name="nvidia",
                restart_policy="Never",
                volumes=[
                    client.V1Volume(
                        name="app-volume",
                        config_map=client.V1ConfigMapVolumeSource(name=self.name),
                    )
                ],
            ),
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
        logging.info("Job created")

        self.__create_config_map_object(code, job)
        self.__create_environment_secret()
        if self.registry_pat:
            self.__create_registry_credentials_secret()

        return job

    def __create_config_map_object(self, code: str, job: client.V1Job):
        # Configureate ConfigMap from a local file
        configmap = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            data={"main.py": code},
            metadata=client.V1ObjectMeta(
                name=self.name,
                owner_references=[
                    client.V1OwnerReference(
                        api_version="v1",
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

        logging.info("ConfigMap created.")

    def __create_environment_secret(self):
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

        logging.info("Environment created.")

    def __create_registry_credentials_secret(self):
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

        logging.info("Registry credentials created.")

    def __delete_job(self):
        if self.registry_pat:
            self.core_api_instance.delete_namespaced_secret(
                self.__registry_credentials_secret_name(), self.namespace
            )
            logging.info("Registry credentials removed")

        self.core_api_instance.delete_namespaced_secret(self.name, self.namespace)
        logging.info("Environment removed.")

        self.core_api_instance.delete_namespaced_config_map(
            self.name,
            self.namespace,
            body=client.V1DeleteOptions(propagation_policy="Foreground"),
        )

        api_response = self.batch_api_instance.delete_namespaced_job(
            self.name,
            self.namespace,
            body=client.V1DeleteOptions(propagation_policy="Foreground"),
            _preload_content=False,
        )

        try:
            data = loads(api_response.data)

            logging.info(
                "Job removed. status='%s'"
                % str(data["status"]["conditions"][0]["type"])
            )
        except:
            logging.info(api_response.status)
            logging.info("Job removed. status='%s'" % str(api_response.status))

    def __get_job_logs(self, name="qiskit-aer-gpu"):
        api_response = self.core_api_instance.read_namespaced_pod_log(
            name=name, namespace=self.namespace
        )
        logging.debug("Job logs='%s'" % str(api_response))
        return api_response

    def __get_pods_in_job(self):
        pods = self.core_api_instance.list_namespaced_pod(
            self.namespace, label_selector=f"app={self.name}"
        )

        pod_name = pods.items[0].metadata.name

        logging.info("Pods in the job='%s'" % str(pod_name))

        return pod_name

    def __complete_and_get_job_status(self):
        pod_name = None
        job_completed = False

        while not job_completed:
            api_response = self.batch_api_instance.read_namespaced_job_status(
                self.name, self.namespace
            )

            logging.debug("Job status='%s'" % str(api_response.status.start_time))

            if (
                api_response.status.succeeded is not None
                or api_response.status.failed is not None
            ):
                job_completed = True
            elif api_response.status.active is not None:
                if pod_name is None:
                    pod_name = self.__get_pods_in_job()

                s = self.core_api_instance.read_namespaced_pod_status(
                    name=pod_name,
                    namespace=self.namespace,
                )

                try:
                    if s.status.container_statuses[0].state.terminated is not None:
                        if (
                            s.status.container_statuses[0].state.terminated.exit_code
                            == 0
                        ):
                            job_completed = True
                except TypeError:
                    pass
                finally:
                    logging.info("Pod status='%s'" % str(s.status.phase))

            sleep(1)

        return self.__map_job_status_to_stream(api_response.status)

    def __map_job_status_to_stream(self, status):
        logging.debug("Job status='%s'" % str(status))
        if status.succeeded is not None:
            return "stdout"
        elif status.failed is not None:
            return "stderr"
        else:
            return "unknown"

    def __prepare_environment(self):
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
        try:
            self.__create_job_object(code=code)

            stream = self.__complete_and_get_job_status()

            job = self.__get_pods_in_job()
            logs = self.__get_job_logs(job)

            return logs, stream
        except KeyboardInterrupt:
            return "Task interrupted by user", "stderr"
        except:
            logging.info("An error occurred.")
            return "An error occurred.", "stderr"
        finally:
            self.__delete_job()

    def abort(self):
        self.__delete_job()
