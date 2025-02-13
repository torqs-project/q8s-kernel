from os import remove
from os.path import exists, join
import unittest

from q8s.project import Project


class TestProject(unittest.TestCase):
    def before(self):
        pass

    def after(self):
        remove("tests/fixtures/cache/.q8s_cache/cpu/requirements.txt", missing_ok=True)

    def test_init(self):

        project = Project("tests/fixtures/cache")

        self.assertEqual(project.name, "Example")
        self.assertIsNotNone(project.configuration.python_env)
        self.assertEqual(project.configuration.targets.keys(), {"cpu", "gpu"})

    def test_init_cache(self):
        project_path = "tests/fixtures/cache"
        project = Project(project_path)

        self.assertFalse(exists(join(project_path, ".q8s_cache/cpu/requirements.txt")))
        self.assertFalse(exists(join(project_path, ".q8s_cache/gpu/requirements.txt")))

        project.init_cache()

        self.assertTrue(exists(join(project_path, ".q8s_cache/cpu/requirements.txt")))
        self.assertTrue(exists(join(project_path, ".q8s_cache/gpu/requirements.txt")))

    def test_clear_cache(self):
        project_path = "tests/fixtures/cache"
        project = Project(project_path)

        project.init_cache()

        self.assertTrue(exists(join(project_path, ".q8s_cache/cpu/requirements.txt")))
        self.assertTrue(exists(join(project_path, ".q8s_cache/gpu/requirements.txt")))

        project.clear_cache()

        self.assertFalse(exists(join(project_path, ".q8s_cache/cpu/requirements.txt")))
        self.assertFalse(exists(join(project_path, ".q8s_cache/gpu/requirements.txt")))

    def test_check_cache(self):
        project_path = "tests/fixtures/cache"
        project = Project(project_path)

        project.init_cache()

        with open(join(project_path, ".q8s_cache/cpu/requirements.txt"), "a") as f:
            f.write("qiskit==1.0.0")

        self.assertFalse(project.check_cache())

        project.clear_cache()
