import unittest
from unittest.mock import MagicMock, patch
from q8s.kernel import Q8sKernel, kernel_comm_identifier


class TestQ8sKernel(unittest.TestCase):

    @patch("q8s.kernel.CommManager")
    @patch.dict(
        "os.environ",
        {"KUBECONFIG": "./tests/fixtures/config.fixture", "DOCKER_IMAGE": "mock_image"},
    )
    def test_initialize_comm_manager(self, MockCommManager):
        # Mock CommManager instance
        mock_comm_manager = MockCommManager.return_value
        mock_register_target = mock_comm_manager.register_target

        # Create an instance of Q8sKernel
        kernel = Q8sKernel()

        # Assert CommManager was initialized with the kernel instance
        MockCommManager.assert_called_once_with(kernel=kernel)

        # Assert register_target was called with the correct arguments
        mock_register_target.assert_called_once_with(
            kernel_comm_identifier, kernel._on_comm_open
        )

        # Assert shell handlers were set correctly
        self.assertEqual(
            kernel.shell_handlers["comm_open"], mock_comm_manager.comm_open
        )
        self.assertEqual(kernel.shell_handlers["comm_msg"], mock_comm_manager.comm_msg)
        self.assertEqual(
            kernel.shell_handlers["comm_close"], mock_comm_manager.comm_close
        )


if __name__ == "__main__":
    unittest.main()
