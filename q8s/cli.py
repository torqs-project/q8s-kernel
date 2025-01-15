import os
from pathlib import Path
import typer
import sys
from typing_extensions import Annotated
from q8s.execution import K8sContext, Target
from q8s.install import install_my_kernel_spec

app = typer.Typer()


@app.command()
def build(tag: str = None):
    pass


@app.command()
def execute(
    file: Annotated[Path, typer.Argument(help="Python file to be executed")],
    target: Annotated[
        Target, typer.Option(help="Execution target", case_sensitive=False)
    ] = Target.gpu,
    kubeconfig: Annotated[
        Path, typer.Option(help="Kubernetes configuration", envvar="KUBECONFIG")
    ] = None,
    image: Annotated[str, typer.Option(help="Docker image")] = "vstirbu/benchmark-deps",
    registry_pat: Annotated[
        str,
        typer.Option(
            help="Registry personal access token (PAT)",
            envvar="REGISTRY_PAT",
        ),
    ] = None,
):
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
