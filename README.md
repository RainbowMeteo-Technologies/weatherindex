[![metrics](https://github.com/RainbowMeteo-Technologies/weatherindex/actions/workflows/test.yml/badge.svg)](https://github.com/RainbowMeteo-Technologies/weatherindex/actions/workflows/test.yml)

# Weatherindex

Weatherindex is an **open-source platform** for comparing short-term weather forecasts ("nowcasts") from leading weather data providers.

## Development setup

1. Clone the repository
```sh
git clone git@github.com:RainbowMeteo-Technologies/weatherindex.git
cd weatherindex
```

2. Create and activate a virtual environment (recommended)
```sh
python3.11 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies
```sh
pip install -r requirements.dev.txt
```

### Makefile commands

The project uses a Makefile to simplify common tasks:

| Command | Purpose |
|---------|---------|
| `make test` | Run the full test suite |
| `make coverage` | Generate a code-coverage report. |
| `make docker-build-<component>` | Build a Docker image for the specified component (e.g. `forecast`). |
| `make docker-publish-<component>` | Build and push the image to the configured registry. |


**Example - build the _forecast_ image:**
```sh
make docker-build-forecast
```

## Calculating forecast‑quality metrics

The metric-calculation pipeline is split into four independent stages so that you can rerun later stages without repeating earlier ones:
1. [**Collect forecasts**](#collect-forecasts) - Download raw forecast files from each provider.
2. [**Collect observations**](#collect-observations) - Collect observations from sensors.
3. [**Checkout data**](#checkout-data) - Download the required data from cloud storage and isolate the subset covering the desired date-time range.
4. [**Parse data**](#parse-data) - Convert raw files into a uniform internal format.
5. [**Compute metrics**](#compute-metrics) - Produce accuracy metrics and export them as CSV.

### Collect forecasts

Forecast collection is handled by the `forecast` service (`tools/forecast`). 
The service polls every configured forecast provider once every 10 minutes and stores the raw responses, issuing **one API request per sensor** to the chosen forecast provider.

> **API‑call budget**
>
> Daily requests per provider can be estimated as:
>
> `provider_api_calls_per_day = number_of_sensors × 144`
> _(there are 144 ten‑minute intervals in 24 hours)._
>
> With the default `world_sensors.csv` (814 sensors):
>
> `814 × 144 = 117 216 requests / day`
> ≈ **3 516 480** requests / month.
>
> _Make sure your subscription with each provider can accommodate at least this volume._

#### Deploying the forecast service

To bring the forecast downloaders online:
1. **Copy the bundle** - transfer the contents of `deploy/forecast/` to your target server.
2. **Create an environment file** - copy `.env.example` to `.env` and fill in the required credentials and settings.
3. **Launch Docker Compose with selected profiles** - start only the downloaders you need by enabling their profiles, e.g.:
```sh
# Start AccuWeather and rainbow downloaders only
docker compose --profile accuweather --profile rainbow up -d
```

Setup the `--profile` flags to launch required downloaders. Each downloader service in `docker-compose.yml` is tagged with a unique profile (see the file `deploy/forecast/docker-compose.yml` for the full list).

### Collect observations

Observation collection is handled by the `sensors` service (`tools/sensors`).
The service polls every configured sensors source and save data to cloud.

To bling sensors downloader online:
1. **Copy the bundle** - transfer the contents of `deploy/forecast/` to your target server.
2. **Create an environment file** - copy `.env.example` to `.env` and fill in the required credentials and settings.
3. **Launch Docker Compose with selected profiles** - start only the downloaders you need by enabling their profiles, e.g.:
```sh
docker compose --profile metar up -d
```

Setup the `--profile` flags to launch required downloaders. Each downloader service in `docker-compose.yml` is tagged with a unique profile (see the file `deploy/sensors/docker-compose.yml` for the full list).


### Checkout data

This step downloads stored forecasts and observations for a specified time range and writes them into a local session directory. Use the `metrics.checkout` CLI with the desired options:

```sh
python -m metrics.checkout \
    --session-path .dev/sessions/test \
    --start-time 1745233200 \
    --end-time 1745240400 \
    --s3-uri-metar s3://uri/folder/metar/ \ 
    --s3-uri-rainbowai s3://uri/folder/rainbow/ \
    --s3-uri-accuweather s3://uri/folder/accuweather
```
Start and end times are Unix epoch timestamps in seconds.

Provide as many `--s3-uri-<provider>` arguments as needed (one per provider).

Run `python -m metrics.checkout --help` for the full list of parameters.


### Parse data

This stage transforms raw forecast and observation files in a `session` into a canonical, column‑oriented format consumed by the metrics engine.

```sh
python -m metrics.parse \
    --session-path .dev/sessions/test \
    --process-num 4
```

The command parses all providers downloaded into the session. Use `--process-num` to control the number of parallel worker processes. Run `python -m metrics.parse --help` for additional options.

Upon completion, the parser creates a `tables/` directory inside the session path and writes unified Parquet datasets for every forecast and observation provider.


### Compute metrics

This final stage computes accuracy metrics from the unified Parquet tables produced in the previous step and writes them to a CSV file.

```sh
python -m metrics.calc \
    --session-path .dev/sessions/test \
    --process-num 2 \
    --output-csv .dev/output/rainbow.csv \
    events \
    --offsets "0 10 20 30 40 50 60 70 80 90 100 110 120" \
    --forecast-vendor rainbowai \
    --observation-vendor metar
```

- `--offsets` - space‑separated list of forecast lead times (in minutes) for which metrics are calculated.

- `--forecast-vendor` - name of the forecast provider to evaluate.

- `--observation-vendor` - name of the ground‑truth observation provider.

The results are written to the path given in `--output-csv`. Each record contains the fields below:
| Field | Description |
|-------|-------------|
| `id`    | ID of the sensor for which the metric was calculated. |
| `timestamp` | Event timestamp (rounded to the 10‑minute grid). |
| `precip_type_status_forecast` | `1` if the forecasted precipitation type matches the target type (see `--precip-types`), otherwise `0`. |
| `precip_type_status_observations` | Same as above, but for `observations`. |
| `forecast_time` | Lead time of the forecast (in seconds). Example: for a forecast issued at `13:30` that verifies at `13:50`, the value is `1200`. |
| `precip_rate_forecast` | Forecasted precipitation rate (mm/h). |
| `precip_rate_observations` | Observed precipitation rate (mm/h). Constant for METAR (or other binary observations). |
| `observed_precip` | `1` if the target precipitation type was observed at `timestamp`, else `0`. |
| `forecasted_precip` | `1` if the target precipitation type was forecasted at `timestamp`, else `0`. |
| `tp` | True Positive - precip observed `and` forecasted. |
| `fp` | False Positive - precip `not` observed but forecasted. |
| `tn` | True Negative - precip `not` observed and `not` forecasted. |
| `fn` | False Negative - precip observed but `not` forecasted. |

### Custom Provider Integration

For custom provider integration you might want to take a look at:
- [Custom forecast provider data collecting integration guide](docs/integration/forecast.md)
- [Custom forecast provider metrics integration guide](docs/integration/metrics.md)