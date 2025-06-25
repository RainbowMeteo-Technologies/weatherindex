# Metrics Integration Guide

This guide is for those who considers using this methodology to evaluate forecast quality of any forecast provider originally not supported in `weatherindex` repository. This topic covers only the [metrics](metrics/) scope, for instruction on how to start collecting your custom provider data refer to [forecast.md](docs/integration/forecast.md).

## Overview

You will have to implement several interfaces to support new provider correct checkout and calculation.
As it was already mentioned in [README.md](README.md) there are three stages in calculation process:

- checkout
- parse
- calculation

Each of these stages has it's own interface which should be implemented and integrated for a proper calculation.

## Checkout

You can find checkout implementation in the [relevant subdirectory](metrics/checkout).
Basically, checkout takes a list of download rules called [`DataSource`](metrics/checkout/data_source.py) and process them one by one.

Briefly, `DataSource` describes all there is to know about downloaded provider data:
```python
@dataclass
class DataSource:
    vendor: str                          # name of the data source vendor (used only for logging)
    s3_uri: str                          # s3 uri of the folder where to download data
    data_folder: str                     # the folder where to store downloaded data
    period: str                          # period of the data archives stores in s3
    filename_rule: Callable[[int], str]  # rule to convert timestamp to filename
```

To pass download remote uri to checkout you have to add it to [`ForecastSourcesInfo`](metrics/checkout/data_source.py).
```python
@dataclass
class ForecastSourcesInfo:
    s3_uri_rainviewer: Optional[str] = None
    s3_uri_wk: Optional[str] = None
    s3_uri_accuweather: Optional[str] = None
    s3_uri_tomorrowio: Optional[str] = None
    s3_uri_vaisala: Optional[str] = None
    s3_uri_rainbowai: Optional[str] = None
    s3_uri_weathercompany: Optional[str] = None
    s3_uri_custom_provider: Optional[str] = None # add uri here
```

Add support of this uri as cli argument to [`metrics/checkout/__main__.py`](metrics/checkout/__main__.py).
```python
def _run_checkout(args: argparse.Namespace):
    forecasts = ForecastSourcesInfo(s3_uri_rainviewer=args.s3_uri_rainviewer,
                                    s3_uri_wk=args.s3_uri_wk,
                                    s3_uri_accuweather=args.s3_uri_accuweather,
                                    s3_uri_tomorrowio=args.s3_uri_tomorrowio,
                                    s3_uri_vaisala=args.s3_uri_vaisala,
                                    s3_uri_rainbowai=args.s3_uri_rainbowai,
                                    s3_uri_weathercompany=args.s3_uri_weathercompany,
                                    s3_uri_custom_provider=args.s3_uri_custom_provider) # add uri here

# <...>

s3_group.add_argument("--s3-uri-custom-provider", type=str, dest="s3_uri_custom_provider",
                      required=False, default=None,
                      help="S3 uri where to get custom provider forecast")
```

And add unique enum value to [`DataVendor`](metrics/data_vendor.py).
```python
class DataVendor(BaseDataVendor, Enum):
    WeatherKit = "weatherkit"
    AccuWeather = "accuweather"
    TomorrowIo = "tomorrowio"
    Vaisala = "vaisala"
    RainbowAi = "rainbowai"
    RainViewer = "rainviewer"
    WeatherCompany = "weathercompany"
    CustomProvider = "custom_provider" # add new enum item here

    Metar = "metar"
```

Important part to keep in mind here is `filename_rule` - it is a function which provides remote filename depending on timestamp.
If, for example, we're downloading data for the last hour with 600 seconds step, checkout has to know the source uri for files with data aggregated up to 0, 600, 1200, 1800, ..., 3600 seconds. 

For each of this requested timestamps `filename_rule` has to provide unique filename.
```python
filename_rule(0) -> "data_for_0.ext"
filename_rule(600) -> "data_for_600.ext"
...
filename_rule(3600) -> "data_for_3600.ext"
```

Default filename rule expects to find `{timestamp}.zip` filename. If your stored data has different format you need to implement your own filename_rule. Thus, to create your own download rule for custom provider you will write something like this
```python
DataSource.create(vendor="custom_provider", s3_uri=forecasts_info.s3_uri_custom_provider,
                  data_folder=os.path.join(self._session.data_folder,
                                           DataVendor.CutomProvider.value),
                  period=CUSTOM_PROVIDER_PERIOD),
```
and add it into forecast sources list in [`CheckoutExecutor`](metrics/checkout/checkout.py).
```python
class CheckoutExecutor:
    # <... SOME CODE HERE ...>

    def forecast_sources_list(self, forecasts_info: ForecastSourcesInfo) -> typing.List["DataSource"]:
        return [
            # <ALL SUPPORTED PROVIDERS HERE>
            DataSource.create(vendor="custom_provider",
                              s3_uri=forecasts_info.s3_uri_custom_provider,
                              data_folder=os.path.join(self._session.data_folder,
                                                       DataVendor.CutomProvider.value),
                              period=CUSTOM_PROVIDER_PERIOD)
        ]

    # <... SOME CODE HERE ...>
```

With this changes made you can now run `metrics.checkout` command passing your S3 bucket with custom provider forecast as argument:
```bash
python -m metrics.checkout \
    --session-path .dev/sessions/test \
    --start-time 1745233200 \
    --end-time 1745240400 \
    --s3-uri-custom-provider s3://path-to-custom-provider-data
```

After checkout finished in your session folder you should see something like this:
```
sessions/
    test/
        data/
            custom_provider/
                1745233200.zip
                ...
                1745240400.zip
```

## Parse

In case your provider data is retrieved as API responses to requests of "forecast in point" type you have to convert it to unified format in order for future calculation to happen.

For that you have to create your own `CustomProviderParser` and inherit it from [`BaseParser`](metrics/parse/base_parser.py) and implement the process of converting your format to a table with specified columns.

```python
    def _get_columns(self) -> List[str]:
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"]
```

You can look for implementation ideas in already supported parsers located in [metrics/parse/forecast](metrics/parse/forecast).

With this changes made you can now run `metrics.parse` command:
```bash
python -m metrics.parse \
    --session-path .dev/sessions/test \
    --process-num 4
```

After parse finished in your session folder you should see something like this:
```
sessions/
    test/
        tables/
            custom_provider/
                1745233200.parquet
                ...
                1745240400.parquet
```

## Calculate

If your provider is parsed correctly as JSON API responses it should be calculated with `metrics.calc` as is. However, if your provider data is, for example, tiles you might want to take a look at [`RainViewerProvider`](metrics/calc/forecast/rainviewer.py) implementation and make something similar.
