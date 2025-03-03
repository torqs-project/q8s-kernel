from q8s.plugins.job_template_spec import hookimpl
from q8s.enums import Target
from kubernetes import client
from q8s.constants import WORKSPACE
from typing import Dict


class CPUJobTemplatePlugin:

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

        if target != Target.cpu:
            return None

        container = client.V1Container(
            name="quantum-routine",
            image=container_image,
            env=env,
            command=["python"],
            args=[f"{WORKSPACE}/main.py"],
            image_pull_policy="Always",
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
