from importlib.metadata import (
    packages_distributions,
    version,
)

from .code_analyzer import CodeAnalyzer

mapping = {
    "qiskit-aer": "qiskit-aer-gpu",
}


class Parser:
    def __init__(self) -> None:
        self.installed = packages_distributions()

    def mapToPip(self, package: str) -> str:
        """
        Map the package to the pip package.
        """

        try:
            return self.installed[package][0]
        except KeyError:
            return None

    def parse(self, code: str) -> str:
        """
        Parse the code and returns the requirements.
        """
        imports = CodeAnalyzer(code).getImports()

        pips = list(map(self.mapToPip, imports))

        return "\n".join(
            list(
                map(
                    lambda x: "{name}=={version}".format(
                        name=mapping[x] if x in mapping.keys() else x,
                        version=version(x),
                    ),
                    pips,
                )
            )
        )
