import base64
import io
import matplotlib.backend_bases
from matplotlib.backends.backend_agg import FigureCanvasAgg


class Q8SLoggerBackend(FigureCanvasAgg):
    """Custom Matplotlib backend that logs images as base64-encoded strings."""

    def print_png(self, filename_or_obj, *args, **kwargs):
        """Override the PNG printing to log Base64 instead of saving to a file."""
        buf = io.BytesIO()
        super().print_png(buf, *args, **kwargs)

        # Convert to base64
        buf.seek(0)
        encoded_image = base64.b64encode(buf.getvalue()).decode("utf-8")

        # Log to console
        print(f"data:image/png;base64,{encoded_image}\n")


FigureCanvas = Q8SLoggerBackend
# Register the backend


# Fix: Override `show()` to manually trigger rendering
def show():
    """Manually process all figures and log their base64 images."""
    import matplotlib._pylab_helpers

    # Get all active figures
    figures = matplotlib._pylab_helpers.Gcf.get_all_fig_managers()

    for manager in figures:
        figure = manager.canvas.figure
        canvas = Q8SLoggerBackend(figure)
        canvas.draw()  # Render the figure
        canvas.print_png(None)  # Trigger our Base64 logging


# Register the custom show function
matplotlib.backend_bases.show = show
