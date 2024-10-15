from json import loads
import logging
import random
import string
from dotenv import dotenv_values
from kubernetes import client, config

from .k8s import (
    complete_and_get_job_status,
    create_job_object,
    get_job_logs,
    get_pods_in_job,
)

FORMAT = "[%(levelname)s %(asctime)-15s q8s_kernel] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)


class K8sContext:
    container_image: str = "vsirbu/benchmark-deps"
    registry_pat: str = None

    def __init__(self, kubeconfig: str):
        config.load_kube_config(kubeconfig)
        logging.info("Kubeconfig loaded")

        _, active_context = config.list_kube_config_contexts(config_file=kubeconfig)

        self.namespace = active_context["context"]["namespace"]
        logging.info("Active namespace: %s" % self.namespace)

        self.core_api_instance = client.CoreV1Api()
        self.batch_api_instance = client.BatchV1Api()

        self.name = f"qubernetes-job-{K8sContext.get_id()}"

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

    def execute(self, code: str) -> tuple[str, str]:
        try:
            create_job_object(
                image=self.container_image,
                code=code,
                name=self.name,
                registry_pat=self.registry_pat,
            )

            stream = complete_and_get_job_status(name=self.name)

            jobs = get_pods_in_job(name=self.name)
            logs = self.__get_job_logs(jobs)

            return logs, stream
        except:
            logging.info("An error occurred.")
        finally:
            self.__delete_job()
