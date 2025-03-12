import os
import unittest
from unittest.mock import patch, MagicMock
from q8s.kernel import get_docker_image
from q8s.project import ProjectNotFoundException, CacheNotBuiltException


class TestLoadDockerImage(unittest.TestCase):

    @patch("q8s.kernel.Project")
    @patch("q8s.kernel.os.environ.get")
    def test_load_docker_image_with_valid_target(self, mock_get_env, mock_project):
        mock_get_env.side_effect = lambda key, default=None: {"TARGET": "gpu"}.get(
            key, default
        )
        mock_project.return_value.cached_images.return_value = "valid_image"

        image = get_docker_image()
        self.assertEqual(image, "valid_image")

    @patch("q8s.kernel.os.environ.get")
    def test_load_docker_image_with_invalid_target(self, mock_get_env):
        mock_get_env.side_effect = lambda key, default=None: {
            "TARGET": "invalid_target"
        }.get(key, default)

        with self.assertRaises(SystemExit):
            get_docker_image()

    @patch("q8s.kernel.Project")
    @patch("q8s.kernel.os.environ.get")
    def test_load_docker_image_project_not_found(self, mock_get_env, mock_project):
        mock_get_env.side_effect = lambda key, default=None: {"TARGET": "gpu"}.get(
            key, default
        )
        mock_project.side_effect = ProjectNotFoundException("Project not found")

        image = get_docker_image()
        self.assertEqual(image, "vstirbu/benchmark-deps")

    @patch("q8s.kernel.Project")
    @patch("q8s.kernel.os.environ.get")
    def test_load_docker_image_cache_not_built(self, mock_get_env, mock_project):
        mock_get_env.side_effect = lambda key, default=None: {"TARGET": "gpu"}.get(
            key, default
        )
        mock_project.side_effect = CacheNotBuiltException("Cache not built")

        image = get_docker_image()
        self.assertEqual(image, "vstirbu/benchmark-deps")

    @patch("q8s.kernel.Project")
    @patch("q8s.kernel.os.environ.get")
    def test_load_docker_image_general_exception(self, mock_get_env, mock_project):
        mock_get_env.side_effect = lambda key, default=None: {"TARGET": "gpu"}.get(
            key, default
        )
        mock_project.side_effect = Exception("General error")

        image = get_docker_image()
        self.assertEqual(image, "vstirbu/benchmark-deps")


if __name__ == "__main__":
    unittest.main()
