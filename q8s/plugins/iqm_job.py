from typing import Dict
from kubernetes import client
from q8s.constants import WORKSPACE
from q8s.enums import Target
from q8s.plugins.job_template_spec import hookimpl

MOUNT_PATH = "/cortex/config"
INIT_MOUNT_PATH = "/cortex/init"


class IQMJobPlugin:

    def configmap_init_name(self, name: str) -> str:
        return f"{name}-cortex-config"

    @hookimpl
    def prepare(
        self,
        target: Target,
        name: str,
        namespace: str,
        env: Dict[
            str,
            str | None,
        ],
    ) -> None:
        if target != Target.qpu:
            return

        print("Preparing for IQM job...")

        if (
            not env.clear("CORTEX_USERNAME")
            or not env.get("CORTEX_URL")
            or not env.get("CORTEX_PASSWORD")
        ):
            raise ValueError("Missing required environment variables")

        config_json = {
            "auth_server_url": env.get("CORTEX_URL"),
            "realm": "cortex",
            "client_id": "iqm_client",
            "username": "",
            "tokens_file": f"{MOUNT_PATH}/tokens.json",
        }

        configmap_init = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            data={"config.json": config_json},
            metadata=client.V1ObjectMeta(name=self.configmap_init_name(name)),
        )

        client.CoreV1Api().create_namespaced_config_map(
            namespace=namespace, body=configmap_init
        )

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

        if target != Target.qpu:
            return None

        init_config_volume = client.V1Volume(
            name="init-config-data",
            config_map=client.V1ConfigMapVolumeSource(
                name=self.configmap_init_name(name)
            ),
        )

        init_config_volume_mount = client.V1VolumeMount(
            name=init_config_volume.name,
            mount_path=INIT_MOUNT_PATH,
            read_only=True,
        )

        # shared data volume keeps the cortex configuration
        shared_config_volume = client.V1Volume(
            name="shared-config-data",
            empty_dir=client.V1EmptyDirVolumeSource(),
        )

        shared_config_volume_mount = client.V1VolumeMount(
            name=shared_config_volume.name,
            mount_path=MOUNT_PATH,
        )

        job_container = client.V1Container(
            name="quantum-job",
            image=container_image,
            env=env,
            command=["python"],
            args=[f"{WORKSPACE}/main.py"],
            volume_mounts=[shared_config_volume_mount],
        )

        cortex_init_container = client.V1Container(
            name="cortex",
            image=container_image,
            env=env,
            command=["cp"],
            args=[
                f"{INIT_MOUNT_PATH}/config.json",
                f"{MOUNT_PATH}/config.json",
            ],
            volume_mounts=[init_config_volume_mount, shared_config_volume_mount],
        )

        cortex_login_container = client.V1Container(
            name="cortex",
            image=container_image,
            env=env,
            command=["cortex"],
            args=[
                "auth",
                "login",
                "--username",
                "$(CORTEX_USERNAME)",
                "--password",
                "$(CORTEX_PASSWORD)",
                "--no-refresh",
                "--config-file",
                f"{shared_config_volume_mount.mount_path}/config.json",
            ],
            volume_mounts=[
                shared_config_volume_mount,
            ],
        )

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": name}),
            spec=client.V1PodSpec(
                containers=[job_container],
                init_containers=[cortex_init_container, cortex_login_container],
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
                volumes=[init_config_volume, shared_config_volume],
            ),
        )

        return template

    @hookimpl
    def cleanup(self, name: str, namespace: str) -> None:
        client.CoreV1Api().delete_namespaced_config_map(
            name=self.configmap_init_name(name), namespace=namespace
        )
