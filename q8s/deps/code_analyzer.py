import ast
import sys

from stdlib_list import stdlib_list


class CodeAnalyzer(ast.NodeVisitor):
    stdlibs = []
    version = "{}.{}".format(sys.version_info.major, sys.version_info.minor)

    def __init__(self, code):
        self.imports = set()
        self.stdlibs = self.stdlib_list()

        # with open(file, "r") as source:
        #     tree = ast.parse(source.read())

        #     self.visit(tree)
        tree = ast.parse(code)
        self.visit(tree)

        # print("working with version: ", self.version)

    def stdlib_list(self):
        if sys.version_info.major == 3 and sys.version_info.minor < 10:
            return stdlib_list(self.version)
        else:
            return sys.stdlib_module_names

    def addImport(self, name):
        if name in self.stdlibs:
            pass
        elif name in sys.builtin_module_names:
            pass
        else:
            self.imports.add(name.split(".")[0])

    def visit_Import(self, node):
        for alias in node.names:
            # pprint(vars(alias))
            self.addImport(alias.name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        # pprint(vars(node))
        # pprint(self.file)

        if node.level == 0:
            self.addImport(node.module)
        else:
            if node.module is None:
                for name in node.names:
                    self.addImport(name.asname or name.name)
            else:
                self.addImport(node.module)

        self.generic_visit(node)

    def getImports(self):
        return sorted(self.imports)
