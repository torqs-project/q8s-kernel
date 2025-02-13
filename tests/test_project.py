from os import remove
from os.path import exists, join
import unittest
from unittest.mock import Mock
from rich.progress import Progress, SpinnerColumn

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

    @unittest.mock.patch("os.system", return_value=0)
    def test_build_container(self, mock_system: Mock):
        project_path = "tests/fixtures/cache"
        project = Project(project_path)

        project.init_cache()

        image_name = project.build_container(
            target="cpu", progress=Progress(SpinnerColumn()), push=False
        )

        assert mock_system.called
        assert (
            mock_system.call_args[0][0]
            == f"docker build -t {image_name} {join(project_path, '.q8s_cache/cpu')}"
        )
        self.assertEqual(image_name, "vstirbu/q8s-example:cpu")

    @unittest.mock.patch("os.system", return_value=0)
    def test_push_container(self, mock_system: Mock):
        project_path = "tests/fixtures/cache"
        project = Project(project_path)

        project.init_cache()

        image_name = project.build_container(
            target="cpu", progress=Progress(SpinnerColumn()), push=False
        )

        project.push_container(target="cpu", progress=Progress(SpinnerColumn()))

        assert mock_system.called
        assert mock_system.call_args[0][0] == f"docker push {image_name}"
