import os
import unittest
from unittest.mock import patch, MagicMock
from q8s.utils import get_docker_image
from q8s.enums import Target
from q8s.project import ProjectNotFoundException, CacheNotBuiltException


class TestGetDockerImage(unittest.TestCase):

    @patch("q8s.utils.Project")
    def test_get_docker_image_success(self, MockProject):
        mock_project = MockProject.return_value
        mock_project.cached_images.return_value = "mock_image"
        image = get_docker_image(target=Target.cpu)
        self.assertEqual(image, "mock_image")

    @patch("q8s.utils.Project")
    @patch("q8s.utils.os.environ.get")
    def test_get_docker_image_project_not_found(self, mock_environ_get, MockProject):
        MockProject.side_effect = ProjectNotFoundException
        mock_environ_get.return_value = "env_image"
        image = get_docker_image(target=Target.gpu)
        self.assertEqual(image, "env_image")

    @patch("q8s.utils.Project")
    @patch("q8s.utils.os.environ.get")
    def test_get_docker_image_cache_not_built(self, mock_environ_get, MockProject):
        MockProject.return_value.cached_images.side_effect = CacheNotBuiltException
        mock_environ_get.return_value = "env_image"
        image = get_docker_image(target=Target.gpu)
        self.assertEqual(image, "env_image")

    @patch("q8s.utils.Project")
    @patch("q8s.utils.os.environ.get")
    def test_get_docker_image_general_exception(self, mock_environ_get, MockProject):
        MockProject.side_effect = Exception("General error")
        mock_environ_get.return_value = "env_image"
        image = get_docker_image(target=Target.cpu)
        self.assertEqual(image, "env_image")


if __name__ == "__main__":
    unittest.main()
