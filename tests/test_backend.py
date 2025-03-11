import unittest
from unittest.mock import patch, MagicMock
from q8s.matplotlib.backend import Q8SLoggerBackend

import matplotlib.pyplot as plt


class TestQ8SLoggerBackend(unittest.TestCase):
    @patch("builtins.print")
    def test_print_png_logs_base64(self, mock_print):
        # Create a simple plot
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])

        # Create an instance of the custom backend
        canvas = Q8SLoggerBackend(fig)

        # Call the print_png method
        canvas.print_png(None)

        # Check that print was called with the expected base64 string
        self.assertTrue(mock_print.called)
        args, _ = mock_print.call_args
        self.assertTrue(args[0].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
