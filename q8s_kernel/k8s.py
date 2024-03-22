import os
from string import Template
import tempfile
import shutil
from time import sleep, time
import uuid
import logging

from python_on_whales import docker
import kubernetes

FORMAT = "[%(levelname)s %(asctime)-15s q8s_kernel] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)

TAG_TEMPLATE = Template("$image:$version")

dockerfile_content = """
FROM --platform=amd64 vstirbu/q8s-cuda12

# Set environment variables
# ARG DEVICE
# ENV DEVICE=${DEVICE}

# Set the working directory to /backend
# WORKDIR /backend

# RUN pip install --upgrade pip

COPY requirements.txt .
COPY entrypoint.sh .
RUN pip3 install -r requirements.txt

COPY main.py .

CMD ["./entrypoint.sh"]
"""

requirements_content = """
qiskit==1.0.0
qiskit-aer-gpu==0.13.3
qiskit_algorithms
numpy
networkx
"""

entrypoint_content = """
#!/bin/bash

python3 ./main.py
"""


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
    write_to_file(temp_dir + "/requirements.txt", requirements_content)
    write_to_file(temp_dir + "/entrypoint.sh", entrypoint_content)
    write_to_file(temp_dir + "/main.py", python_file_content)
    enable_executable(temp_dir + "/entrypoint.sh")


def print_nodes(api_instance):
    node_list = api_instance.list_node()

    # print("%s\t\t%s" % ("NAME", "LABELS"))
    # Patching the node labels
    for node in node_list.items:
        # print("%s\t\t%s" % (node.metadata.name, node.metadata.labels))
        print("%s\t\t%s" % ("NAME", node.metadata.name))

        print("%s\t\t%s" % ("LABEL", "VALUE"))
        for label, value in node.metadata.labels.items():
            print("%s\t\t%s" % (label, value))


def create_job_object(image, name="qiskit-aer-gpu"):
    # Configureate Pod template container
    container = kubernetes.client.V1Container(
        name=name,
        image=image,
        command=["python3"],
        args=["./main.py"],
        resources=kubernetes.client.V1ResourceRequirements(
            limits={"nvidia.com/gpu": "1"}, requests={"nvidia.com/gpu": "1"}
        ),
    )

    # Create and configurate a spec section
    template = kubernetes.client.V1PodTemplateSpec(
        metadata=kubernetes.client.V1ObjectMeta(labels={"app": name}),
        spec=kubernetes.client.V1PodSpec(
            containers=[container], restart_policy="Never"
        ),
    )

    # Create the specification of deployment
    spec = kubernetes.client.V1JobSpec(template=template)

    # Instantiate the job object
    job = kubernetes.client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=kubernetes.client.V1ObjectMeta(name=name),
        spec=spec,
    )

    return job


def create_job(job):
    api_instance = kubernetes.client.BatchV1Api()
    api_response = api_instance.create_namespaced_job(body=job, namespace="default")
    logging.info("Job created. status='%s'" % str(api_response.status))


def complete_and_get_job_status(name="qiskit-aer-gpu"):
    job_completed = False
    api_instance = kubernetes.client.BatchV1Api()

    while not job_completed:
        api_response = api_instance.read_namespaced_job_status(name, "default")

        if (
            api_response.status.succeeded is not None
            or api_response.status.failed is not None
        ):
            job_completed = True

        sleep(1)
        logging.info("Job status='%s'" % str(api_response.status))

    return api_response.status


def get_pods_in_job(name="qiskit-aer-gpu"):
    api_instance = kubernetes.client.CoreV1Api()
    api_response = api_instance.list_namespaced_pod(
        "default", label_selector="app=qiskit-aer-gpu"
    )
    logging.info("Pods in the job='%s'" % str(api_response.items[0].metadata.name))

    return api_response.items[0].metadata.name


def get_job_logs(name="qiskit-aer-gpu"):
    api_response = kubernetes.client.CoreV1Api().read_namespaced_pod_log(
        name=name, namespace="default"
    )
    logging.debug("Job logs='%s'" % str(api_response))
    return api_response


def delete_job(name="qiskit-aer-gpu"):
    stream = "stdout"
    api_response = kubernetes.client.BatchV1Api().delete_namespaced_job(
        name,
        "default",
        body=kubernetes.client.V1DeleteOptions(propagation_policy="Foreground"),
    )
    logging.info("Job deleted. status='%s'" % str(api_response.status))

    return api_response


def map_job_status_to_stream(status):
    if status.succeeded is not None:
        return "stdout"
    elif status.failed is not None:
        return "stderr"
    else:
        return "unknown"


def execute(code: str, temp_dir: str, docker_image: str) -> str:
    # docker_client = docker.APIClient(base_url='unix://var/run/docker.sock')
    kubernetes.config.load_kube_config()

    # list_containers(docker_client)

    # print(kubernetes.config.list_kube_config_contexts())

    # print_nodes(api_instance)

    tag = TAG_TEMPLATE.substitute(image=docker_image, version=uuid.uuid4())

    prepare_build_folder(temp_dir, code)
    image = docker.buildx.build(
        context_path=temp_dir,
        tags=[tag],
        labels={"qubernetes.cloud/mode": "development"},
    )

    logging.info("built new image: %s" % image)

    docker.image.push(tag)

    job = create_job_object(image=tag)

    create_job(job)

    status = complete_and_get_job_status()

    log = get_job_logs(get_pods_in_job())

    delete_job()

    stream = map_job_status_to_stream(status)

    logging.info(stream)

    # delete_directory(temp_dir)

    return log, stream
