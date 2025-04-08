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

    @patch("q8s.kernel.Project")
    @patch("q8s.kernel.Q8sKernel.k8s_context", create=True)
    @patch.dict(
        "os.environ",
        {"KUBECONFIG": "./tests/fixtures/config.fixture", "DOCKER_IMAGE": "mock_image"},
    )
    def test_on_comm_open(self, mock_k8s_context, MockProject):
        # Mock the comm object
        mock_comm = MagicMock()
        mock_comm.comm_id = "mock_comm_id"

        # Mock Project and its configuration
        mock_project_instance = MockProject.return_value
        mock_project_instance.configuration.targets.keys.return_value = [
            "cpu",
            "gpu",
        ]

        # Mock k8s_context target
        mock_k8s_context.target.name = "gpu"

        # Create an instance of Q8sKernel
        kernel = Q8sKernel()

        # Call _on_comm_open
        kernel._on_comm_open(mock_comm, {})

        # Assert comm.send was called with the correct initial message
        mock_comm.send.assert_called_once_with(
            {
                "command": "init",
                "targets": ["cpu", "gpu"],
                "selected_target": "gpu",
            }
        )

    @patch("q8s.kernel.Project")
    @patch("q8s.kernel.Q8sKernel.k8s_context", create=True)
    @patch.dict(
        "os.environ",
        {"KUBECONFIG": "./tests/fixtures/config.fixture", "DOCKER_IMAGE": "mock_image"},
    )
    def test_set_target_comm_msg(self, mock_k8s_context, MockProject):
        # Mock the comm object
        mock_comm = MagicMock()
        mock_comm.comm_id = "mock_comm_id"

        # Mock Project and its configuration
        mock_project_instance = MockProject.return_value
        mock_project_instance.configuration.targets.keys.return_value = [
            "cpu",
            "gpu",
        ]

        # Create an instance of Q8sKernel
        kernel = Q8sKernel()

        kernel.k8s_context = mock_k8s_context

        # Register and invoke the comm_open handler
        # kernel._on_comm_open(mock_comm, {})
        kernel.comm_manager.comm_open(
            stream=None,
            ident=None,
            msg={
                "header": {"msg_type": "comm_open"},
                "content": {
                    "comm_id": mock_comm.comm_id,
                    "target_name": kernel_comm_identifier,
                },
            },
        )

        # Simulate receiving a comm_msg from the frontend
        kernel.comm_manager.comm_msg(
            ident=None,
            stream=None,
            msg={
                "header": {"msg_type": "comm_msg"},
                "content": {
                    "comm_id": mock_comm.comm_id,
                    "data": {
                        "command": "set_target",
                        "payload": {"target": "cpu"},
                    },
                },
            },
        )

        # Assert set_target was called on k8s_context with the correct argument
        mock_k8s_context.set_target.assert_called_once_with("cpu")


if __name__ == "__main__":
    unittest.main()
