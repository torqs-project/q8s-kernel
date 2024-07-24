import os
from pathlib import Path
import typer
from typing_extensions import Annotated
from kubernetes import config
from q8s_kernel.k8s import execute as execute_k8s

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
):
    if kubeconfig.exists() is False:
        typer.echo(f"kubeconfig file {kubeconfig} does not exist")
        raise typer.Exit(code=1)

    kubeconfig = os.environ.get("KUBECONFIG", kubeconfig.as_posix())

    if kubeconfig is None:
        typer.echo("KUBECONFIG not set")
        raise typer.Exit(code=1)

    config.load_kube_config(kubeconfig)

    with open(file, "r") as f:
        code = f.read()
        output, stream_name = execute_k8s(code, None, image)

        print(f"output:\n{output}")
        print(f"output stream: {stream_name}")


# if __name__ == "__main__":
app()
