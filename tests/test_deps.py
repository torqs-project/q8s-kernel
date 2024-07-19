import unittest

from q8s_kernel.deps.parser import Parser


class TestParser(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(1, 1)

        with open("tests/fixtures/qiskit.py") as f:
            code = f.read()
            parser = Parser()
            result = parser.parse(code)

            self.assertEqual(result, "qiskit==1.0.0\nqiskit-aer-gpu==0.13.3")


if __name__ == "__main__":
    unittest.main()
