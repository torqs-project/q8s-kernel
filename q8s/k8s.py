import base64
from json import JSONEncoder, loads
import os
from string import Template
import tempfile
import shutil
from time import sleep
import logging
import string
import random

from dotenv import dotenv_values
from python_on_whales import docker
from kubernetes import client

from .deps.parser import Parser

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
    parser = Parser()
    deps = parser.parse(python_file_content)

    requirements_content = parser.toRequirements(deps)
    write_to_file(temp_dir + "/Dockerfile", dockerfile_content)
    write_to_file(temp_dir + "/requirements.txt", requirements_content)
    # write_to_file(temp_dir + "/entrypoint.sh", entrypoint_content)
    # write_to_file(temp_dir + "/main.py", python_file_content)
    # enable_executable(temp_dir + "/entrypoint.sh")


def whoami() -> str:
    whoami = client.AuthenticationV1Api().create_self_subject_review(body={})

    return whoami.status.user_info.username.split(":")[-1]


def load_env():
    env = dotenv_values(".env.q8s")

    # for key in env.keys():
    #     logging.info(f"{key} = {env[key]}")

    return env


def create_environment_secret(
    # job: client.V1Job,
    name: str = "app-environment",
):
    env = load_env()

    data = {}

    for key in env.keys():
        data[key] = base64.b64encode(env[key].encode()).decode()

    secret = client.V1Secret(
        api_version="v1",
        kind="Secret",
        type="Opaque",
        immutable=True,
        data=data,
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=NAMESPACE,
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

    client.CoreV1Api().create_namespaced_secret(namespace=NAMESPACE, body=secret)

    logging.info("Environment created.")


def create_config_map_object(code: str, job: client.V1Job, name="app-config"):
    # Configureate ConfigMap from a local file
    configmap = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        data={"main.py": code},
        metadata=client.V1ObjectMeta(
            name=name,
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

    result = client.CoreV1Api().create_namespaced_config_map(
        namespace=NAMESPACE, body=configmap
    )

    logging.info("ConfigMap created.")


def prepare_environment(name: str):
    raw = load_env()

    env = []

    for key in raw.keys():
        env.append(
            client.V1EnvVar(
                name=key,
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(name=name, key=key)
                ),
            )
        )

    return env


def registry_credentials_secret_name(name: str):
    return f"{name}-regcred"


def create_job_object(image, code: str, name: str, registry_pat: str | None = None):
    # print(client.V1ConfigMapKeySelector(name="main.py"))

    env = prepare_environment(name)

    # Configureate Pod template container
    container = client.V1Container(
        name=name,
        image=image,
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
            client.V1VolumeMount(name="app-volume", mount_path="/app", read_only=True)
        ],
    )

    # Create and configurate a spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": name}),
        spec=client.V1PodSpec(
            containers=[container],
            image_pull_secrets=(
                [
                    client.V1LocalObjectReference(
                        name=registry_credentials_secret_name(name)
                    )
                ]
                if registry_pat
                else []
            ),
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
    spec = client.V1JobSpec(template=template)  # , ttl_seconds_after_finished=10

    # Find user name
    # user = whoami()

    # Instantiate the job object
    job_spec = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=NAMESPACE,
            labels={"qubernetes.dev/job.type": "jupyter"},
        ),
        spec=spec,
    )

    job = create_job(job_spec)

    create_config_map_object(code, job, name=name)
    create_environment_secret(name=name)
    if registry_pat:
        create_registry_credentials_secret(
            name=name, image=image, registry_pat=registry_pat
        )

    return job


def create_registry_credentials_secret(
    name: str, image: str, registry_pat: str | None = None
):
    segments = image.split("/")
    # Find user name for images on Docker Hub
    username = segments[0] if len(segments) == 2 else segments[1]
    registry = segments[0] if len(segments) == 3 else "https://index.docker.io/v1/"

    config = {
        "auths": {
            registry: {
                "auth": base64.b64encode(
                    f"{username}:{registry_pat}".encode()
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
            name=registry_credentials_secret_name(name),
            namespace=NAMESPACE,
        ),
        data={
            ".dockerconfigjson": base64.b64encode(
                JSONEncoder().encode(config).encode()
            ).decode(),
        },
    )

    client.CoreV1Api().create_namespaced_secret(namespace=NAMESPACE, body=secret)

    logging.info("Registry credentials created.")


def create_job(job_spec: client.V1Job):
    api_instance = client.BatchV1Api()
    job = api_instance.create_namespaced_job(body=job_spec, namespace=NAMESPACE)
    logging.info("Job created")

    return job


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


def delete_job(name="qiskit-aer-gpu", registry_pat: str | None = None):
    if registry_pat:
        client.CoreV1Api().delete_namespaced_secret(
            registry_credentials_secret_name(name), NAMESPACE
        )
        logging.info("Registry credentials cleanup")

    client.CoreV1Api().delete_namespaced_secret(name, NAMESPACE)
    logging.info("Environment cleanup")

    client.CoreV1Api().delete_namespaced_config_map(
        name,
        NAMESPACE,
        body=client.V1DeleteOptions(propagation_policy="Foreground"),
    )

    api_response = client.BatchV1Api().delete_namespaced_job(
        name,
        NAMESPACE,
        body=client.V1DeleteOptions(propagation_policy="Foreground"),
        _preload_content=False,
    )

    try:
        data = loads(api_response.data)

        logging.info(
            "Job cleanup. status='%s'" % str(data["status"]["conditions"][0]["type"])
        )
    except:
        logging.info(api_response.status)
        logging.info("Job cleanup. status='%s'" % str(api_response.status))

    return api_response


def map_job_status_to_stream(status):
    if status.succeeded is not None:
        return "stdout"
    elif status.failed is not None:
        return "stderr"
    else:
        return "unknown"


def execute(
    code: str, temp_dir: str, docker_image: str, registry_pat: str | None = None
) -> tuple[str, str]:
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

    name = f"qubernetes-job-{id}"

    create_job_object(
        image=docker_image, code=code, name=name, registry_pat=registry_pat
    )

    stream = complete_and_get_job_status(name=name)

    log = get_job_logs(get_pods_in_job(name=name))

    delete_job(name=name, registry_pat=registry_pat)

    logging.info(stream)

    # delete_directory(temp_dir)

    return log, stream
