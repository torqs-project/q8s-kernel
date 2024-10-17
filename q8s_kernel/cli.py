import os
from pathlib import Path
import typer
from typing_extensions import Annotated
from kubernetes import config
from q8s_kernel.execution import K8sContext

app = typer.Typer()


@app.command()
def build(tag: str = None):
    pass


@app.command()
def execute(
    file: Annotated[Path, typer.Argument(help="Python file to be executed")],
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
    k8s_context.set_container_image(image)
    k8s_context.set_registry_pat(registry_pat)

    with open(file, "r") as f:
        code = f.read()
        # output, stream_name = execute_k8s(code, None, image, registry_pat)
        output, stream_name = k8s_context.execute(code)

        print(f"output:\n{output}")
        print(f"output stream: {stream_name}")


# if __name__ == "__main__":
app()
