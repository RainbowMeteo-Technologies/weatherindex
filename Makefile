include .versions

# Docker commands
docker-build-metrics:
	docker build \
		-f Dockerfile.metrics \
		--target metrics \
		--platform linux/amd64 \
		$(if $(NO_CACHE),--no-cache) \
		-t weatherindex/weatherindex:metrics-${METRICS_DOCKER_VERSION} \
		.

docker-build-forecast:
	docker build \
		-f Dockerfile.forecast \
		--target metrics-forecast \
		--platform linux/amd64 \
		$(if $(NO_CACHE),--no-cache) \
		-t weatherindex/weatherindex:forecast-${METRICS_DOCKER_VERSION} \
		.

docker-build-sensors:
	docker build \
		-f Dockerfile.sensors \
		--target metrics-sensors \
		--platform linux/amd64 \
		$(if $(NO_CACHE),--no-cache) \
		-t weatherindex/weatherindex:sensors-${METRICS_DOCKER_VERSION} \
		.

docker-publish-metrics:docker-build-metrics
	docker push weatherindex/weatherindex:metrics-${METRICS_DOCKER_VERSION}

docker-publish-forecast:docker-build-forecast
	docker push weatherindex/weatherindex:forecast-${METRICS_DOCKER_VERSION}

docker-publish-sensors:docker-build-sensors
	docker push weatherindex/weatherindex:sensors-${METRICS_DOCKER_VERSION}

# testing
test:
	export PYTHONPATH="${PYTHONPATH}:$(pwd)" && \
	pytest tests/

# test coverage
coverage:
	export PYTHONPATH="${PYTHONPATH}:$(pwd)" && \
	coverage run --rcfile=.coveragerc -m pytest tests/ && \
	coverage report --show-missing
