import os
from q8s.enums import Target
from q8s.project import CacheNotBuiltException, Project, ProjectNotFoundException


def extract_non_none_value(arr):
    non_none_values = [x for x in arr if x is not None]
    return non_none_values[0] if non_none_values else None


def get_docker_image(target: Target = None, logging=None):
    try:
        project = Project()

        image = project.cached_images(target=target)
    except ProjectNotFoundException as e:
        if logging:
            logging.warning(e)
        image = os.environ.get("DOCKER_IMAGE", "vstirbu/benchmark-deps")
    except CacheNotBuiltException as e:
        if logging:
            logging.warning(e)
        image = os.environ.get("DOCKER_IMAGE", "vstirbu/benchmark-deps")
    except Exception as e:
        if logging:
            logging.error(f"Error loading project: {e}")
            logging.warning("Q8Sproject file not found in current folder")
        image = os.environ.get("DOCKER_IMAGE", "vstirbu/benchmark-deps")

    return image
