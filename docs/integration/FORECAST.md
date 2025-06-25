# Forecast Integration Guide

This guide provides a general overview of the required implementation steps to start data collecting of custom forecast provider data. This is an essential first step, as further [metrics](docs/integration/metrics.md) relies on data stored using this system.

## Overview

Generally, forecast downloading is operated using 2 entities:

- `provider` - component which inherits `BaseProvider` interface and should have implementation of `fetch_job(timestamp: int)` method.
- `publisher` - component which inherits `Publisher` interface and should have implementation of `publish(snapshot_path: str)` method.

## Provider

Generally, providers could be separated on two categories:

- forecast in point providers
- tiles data providers


### For `forecast in point` provider collecting process have the following steps:

- get list of sensors which will be your source of ground truth
- make forecast in point API request to the location of sensor
- store data "as is" and pack into final snapshot

For such purposes you already have `BaseForecastInPointProvider` class which generalise the process of executing requests to different location, using multiprocessing + asyncio execution. If new provider have API you just need to inherit your class for existing base class and implement `get_json_forecast_in_point(lon: float, lat: float)` method.

### For `tiles data provider` you will have the same approach, but without using sensors at all as you will just have to download all available data.

If you still need to leverage multiprocessing for download, you can use `BaseParallelExecutionProvider` as a base class for that. In that case you will have to implement your download pipeline using `execute_with_batches` adjusting `process_num` and `chunk_size` to the capabilities of your machine.

After implementation of core components make sure to visit forecast running [entry point](tools/forecast/__main__.py) to add necessary cli params to be able to run your provider data collecting via CLI.

## Deployment

After implementing necessary components and testing it the only thing left to do is to add new provider service in your `docker-compose.yml`. There is not much to add here, take a look at already implemented services and make sure to add something similar, adjusting the performance related constants (`--process-num, --chunk-size`) for the machine capabilities to be used efficiently.