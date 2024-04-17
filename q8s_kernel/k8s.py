import os
from string import Template
import tempfile
import shutil
from time import sleep, time
import logging
import string
import random

from python_on_whales import docker
from kubernetes import client

FORMAT = "[%(levelname)s %(asctime)-15s q8s_kernel] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)

TAG_TEMPLATE = Template("$image:$version")
NAMESPACE = os.environ.get("NAMESPACE", "default")
MEMORY = os.environ.get("MEMORY", "32Gi")

dockerfile_content = """
FROM --platform=amd64 vstirbu/benchmark-deps

COPY main.py .

CMD ["./entrypoint.sh"]
"""

# requirements_content = """
# qiskit==1.0.0
# qiskit-aer-gpu==0.13.3
# qiskit_algorithms
# qiskit_ibm_runtime
# numpy
# networkx
# """

# entrypoint_content = """
# #!/bin/bash

# python3 ./main.py
# """


def list_containers(client):
    print(client.containers.list())


def create_temp_directory() -> str:
    temp_dir = tempfile.mkdtemp()
    logging.debug("Temporary directory created:", temp_dir)

    return temp_dir


def delete_directory(directory_path):
    shutil.rmtree(directory_path)
    print("Directory deleted:", directory_path)


def write_to_file(file_path: str, content: str):
    with open(file_path, "w") as file:
        file.write(content)
    print("Content written to file:", file_path)


def enable_executable(file_path: str):
    os.chmod(file_path, 0o755)
    print("Executable flag enabled for file:", file_path)


def prepare_build_folder(temp_dir: str, python_file_content: str):
    write_to_file(temp_dir + "/Dockerfile", dockerfile_content)
    # write_to_file(temp_dir + "/requirements.txt", requirements_content)
    # write_to_file(temp_dir + "/entrypoint.sh", entrypoint_content)
    write_to_file(temp_dir + "/main.py", python_file_content)
    # enable_executable(temp_dir + "/entrypoint.sh")


def create_config_map_object(code: str, name="app-config"):
    # Configureate ConfigMap from a local file
    configmap = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        data={"main.py": code},
        metadata=client.V1ObjectMeta(name=name),
    )

    result = client.CoreV1Api().create_namespaced_config_map(
        namespace=NAMESPACE, body=configmap
    )

    logging.info("ConfigMap created.")


def create_job_object(image, code: str, name="qiskit-aer-gpu"):
    create_config_map_object(code, name=name)

    # print(client.V1ConfigMapKeySelector(name="main.py"))

    # Configureate Pod template container
    container = client.V1Container(
        name=name,
        image=image,
        command=["python3"],
        args=["./app/main.py"],
        resources=client.V1ResourceRequirements(
            limits={
                "cpu": "2",
                "ephemeral-storage": "50Gi",
                # "memory": "64Gi",
                "memory": MEMORY,
                "nvidia.com/gpu": "1",
            },
            requests={
                "cpu": "2",
                "ephemeral-storage": "0",
                # "memory": "32Gi",
                "memory": MEMORY,
                "nvidia.com/gpu": "1",
            },
        ),
        volume_mounts=[
            client.V1VolumeMount(name="app-volume", mount_path="/app", read_only=True)
        ],
    )

    # Create and configurate a spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": name}),
        spec=client.V1PodSpec(
            containers=[container],
            runtime_class_name="nvidia",
            restart_policy="Never",
            volumes=[
                client.V1Volume(
                    name="app-volume",
                    config_map=client.V1ConfigMapVolumeSource(name=name),
                )
            ],
        ),
    )

    # Create the specification of deployment
    spec = client.V1JobSpec(template=template)

    # Instantiate the job object
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=name),
        spec=spec,
    )

    return job


def create_job(job: client.V1Job):
    api_instance = client.BatchV1Api()
    api_instance.create_namespaced_job(body=job, namespace=NAMESPACE)
    logging.info("Job created")


def complete_and_get_job_status(name="qiskit-aer-gpu"):
    job_name = None
    job_completed = False
    api_instance = client.BatchV1Api()

    while not job_completed:
        api_response = api_instance.read_namespaced_job_status(name, NAMESPACE)

        logging.debug("Job status='%s'" % str(api_response.status.start_time))

        if (
            api_response.status.succeeded is not None
            or api_response.status.failed is not None
        ):
            job_completed = True
        elif api_response.status.active is not None:
            if job_name is None:
                job_name = get_pods_in_job(name)

            s = client.CoreV1Api().read_namespaced_pod_status(
                name=job_name,
                namespace=NAMESPACE,
            )

            try:
                if s.status.container_statuses[0].state.terminated is not None:
                    if s.status.container_statuses[0].state.terminated.exit_code == 0:
                        job_completed = True
            except TypeError:
                pass
            finally:
                logging.info("Pod status='%s'" % str(s.status.phase))

        sleep(1)

    return map_job_status_to_stream(api_response.status)


def get_pods_in_job(name="qiskit-aer-gpu"):
    api_instance = client.CoreV1Api()
    api_response = api_instance.list_namespaced_pod(
        NAMESPACE, label_selector=f"app={name}"
    )
    logging.info("Pods in the job='%s'" % str(api_response.items[0].metadata.name))

    return api_response.items[0].metadata.name


def get_job_logs(name="qiskit-aer-gpu"):
    api_response = client.CoreV1Api().read_namespaced_pod_log(
        name=name, namespace=NAMESPACE
    )
    logging.debug("Job logs='%s'" % str(api_response))
    return api_response


def delete_job(name="qiskit-aer-gpu"):
    api_response = client.BatchV1Api().delete_namespaced_job(
        name,
        NAMESPACE,
        body=client.V1DeleteOptions(propagation_policy="Foreground"),
    )

    client.CoreV1Api().delete_namespaced_config_map(
        name,
        NAMESPACE,
        body=client.V1DeleteOptions(propagation_policy="Foreground"),
    )

    logging.info("Job cleanup. status='%s'" % str(api_response.status))

    return api_response


def map_job_status_to_stream(status):
    if status.succeeded is not None:
        return "stdout"
    elif status.failed is not None:
        return "stderr"
    else:
        return "unknown"


def execute(code: str, temp_dir: str, docker_image: str) -> tuple[str, str]:
    # tag = TAG_TEMPLATE.substitute(image=docker_image, version=uuid.uuid4())

    # prepare_build_folder(temp_dir, code)
    # image = docker.buildx.build(
    #     context_path=temp_dir,
    #     tags=[tag],
    #     labels={"qubernetes.cloud/mode": "development"},
    # )

    # logging.info("built new image: %s" % image)

    # docker.image.push(tag)

    id = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

    name = f"qiskit-aer-gpu-{id}"

    job = create_job_object(image=docker_image, code=code, name=name)

    create_job(job)

    stream = complete_and_get_job_status(name=name)

    log = get_job_logs(get_pods_in_job(name=name))

    delete_job(name=name)

    logging.info(stream)

    # delete_directory(temp_dir)

    return log, stream
