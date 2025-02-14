import os
from typing import Dict
import pluggy
from kubernetes import client, config

from q8s.constants import WORKSPACE
from q8s.enums import Target

MEMORY = os.environ.get("MEMORY", "32Gi")

hookspec = pluggy.HookspecMarker("q8s")
hookimpl = pluggy.HookimplMarker("q8s")


class JobTemplatePluginSpec:

    @hookspec
    def makejob(
        self,
        name: str,
        registry_pat: str | None,
        registry_credentials_secret_name: str,
        container_image: str,
        env: Dict[
            str,
            str | None,
        ],
        target: Target,
    ) -> client.V1PodTemplateSpec:
        return None


class CPUandGPUJobTemplatePlugin:

    @hookimpl
    def makejob(
        self,
        name: str,
        registry_pat: str | None,
        registry_credentials_secret_name: str,
        container_image: str,
        env: Dict[
            str,
            str | None,
        ],
        target: Target,
    ) -> client.V1PodTemplateSpec:

        if target != Target.cpu and target != Target.gpu:
            return None

        container = client.V1Container(
            name="quantum-routine",
            image=container_image,
            env=env,
            command=["python"],
            args=[f"{WORKSPACE}/main.py"],
            resources=(
                client.V1ResourceRequirements(
                    limits=(
                        {
                            "cpu": "2",
                            "ephemeral-storage": "50Gi",
                            "memory": MEMORY,
                            "nvidia.com/gpu": "1",
                            # "qubernetes.dev/qpu": "1",
                        }
                    ),
                    requests=(
                        {
                            "cpu": "2",
                            "ephemeral-storage": "0",
                            "memory": MEMORY,
                            "nvidia.com/gpu": "1",
                            # "qubernetes.dev/qpu": "1",
                        }
                    ),
                )
                if target == Target.gpu
                else None
            ),
            volume_mounts=[
                client.V1VolumeMount(
                    name="app-volume", mount_path=WORKSPACE, read_only=True
                )
            ],
        )

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": name}),
            spec=client.V1PodSpec(
                containers=[container],
                image_pull_secrets=(
                    [
                        client.V1LocalObjectReference(
                            name=registry_credentials_secret_name
                        )
                    ]
                    if registry_pat
                    else []
                ),
                runtime_class_name="nvidia" if target == Target.gpu else None,
                restart_policy="Never",
                volumes=[
                    client.V1Volume(
                        name="app-volume",
                        config_map=client.V1ConfigMapVolumeSource(name=name),
                    )
                ],
            ),
        )

        return template
