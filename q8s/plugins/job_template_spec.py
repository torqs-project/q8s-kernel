import os
from typing import Dict
import pluggy
from kubernetes import client

from q8s.constants import WORKSPACE
from q8s.enums import Target

hookspec = pluggy.HookspecMarker("q8s")
hookimpl = pluggy.HookimplMarker("q8s")


class JobTemplatePluginSpec:

    @hookspec
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
        pass

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

    @hookspec
    def cleanup(self, name: str, namespace: str) -> None:
        pass
