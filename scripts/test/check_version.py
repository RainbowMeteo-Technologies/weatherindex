import metrics.version as version
import os

docker_version = os.environ.get("METRICS_DOCKER_VERSION")

print(f"Package version: {version.__version__}")
print(f"Docker version: {docker_version}")

assert version.__version__ == docker_version
