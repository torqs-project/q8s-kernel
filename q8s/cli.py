import os
from pathlib import Path
from time import sleep
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
import sys
from typing_extensions import Annotated
from q8s.execution import K8sContext
from q8s.enums import Target
from q8s.install import install_my_kernel_spec
from q8s.project import Project

app = typer.Typer()


@app.command()
def build(
    init: Annotated[bool, typer.Option(help="Initialize project")] = False,
    target: Annotated[
        Target, typer.Option(help="Execution target", case_sensitive=False)
    ] = None,
):

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(description="Loading project...", total=None)

        project = Project()

        progress.update(task, completed=True)

        if init:
            progress.update(task, description="Initializing cache...")
            project.init_cache()

        if target:
            project.build_container(target=target.value, progress=progress, push=True)

        else:
            for build in project.configuration.targets.keys():
                project.build_container(build, progress=progress, push=True)

    print(f"Project {project.name} ready")
    project.update_images_cache()


@app.command()
def execute(
    file: Annotated[Path, typer.Argument(help="Python file to be executed")],
    target: Annotated[
        Target, typer.Option(help="Execution target", case_sensitive=False)
    ] = Target.gpu,
    kubeconfig: Annotated[
        Path, typer.Option(help="Kubernetes configuration", envvar="KUBECONFIG")
    ] = None,
    image: Annotated[str, typer.Option(help="Docker image")] = None,
    registry_pat: Annotated[
        str,
        typer.Option(
            help="Registry personal access token (PAT)",
            envvar="REGISTRY_PAT",
        ),
    ] = None,
):
    if image is None:
        project = Project()
        image = project.cached_images(target.value)

    if kubeconfig.exists() is False:
        typer.echo(f"kubeconfig file {kubeconfig} does not exist")
        raise typer.Exit(code=1)

    kubeconfig = os.environ.get("KUBECONFIG", kubeconfig.as_posix())

    if kubeconfig is None:
        typer.echo("KUBECONFIG not set")
        raise typer.Exit(code=1)

    # config.load_kube_config(kubeconfig)

    k8s_context = K8sContext(kubeconfig)
    k8s_context.set_target(target)
    k8s_context.set_container_image(image)
    k8s_context.set_registry_pat(registry_pat)

    with open(file, "r") as f:
        code = f.read()
        # output, stream_name = execute_k8s(code, None, image, registry_pat)
        output, stream_name = k8s_context.execute(code)

        print(f"output:\n{output}")
        print(f"output stream: {stream_name}")


@app.command()
def jupyter(
    install: Annotated[
        bool,
        typer.Option(
            help="Install kernel spec for Jupyter",
        ),
    ] = False,
):
    print("install:", install)
    if install:
        install_my_kernel_spec(user=False, prefix=sys.prefix)
        # install_my_kernel_spec(user=user, prefix=prefix)


# if __name__ == "__main__":
app()
