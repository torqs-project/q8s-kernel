from json import loads
import logging
import random
import string
from time import sleep
from dotenv import dotenv_values
from kubernetes import client, config

from .k8s import create_job_object


FORMAT = "[%(levelname)s %(asctime)-15s q8s_context] %(message)s"
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

    def execute(self, code: str) -> tuple[str, str]:
        try:
            create_job_object(
                image=self.container_image,
                code=code,
                name=self.name,
                registry_pat=self.registry_pat,
            )

            stream = self.__complete_and_get_job_status()

            job = self.__get_pods_in_job()
            logs = self.__get_job_logs(job)

            return logs, stream
        except:
            logging.info("An error occurred.")
        finally:
            self.__delete_job()
