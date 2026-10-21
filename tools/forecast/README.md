# Downloader

Tool makes requests to specified API and saves responses into zip file. It also uploads this file to S3.

File `world.common.csv` contains already filtered sensors for download.

## precip.ai

`python -m forecast --download-path <path> --s3-uri <uri> --download-period 3600 precipai --sensors forecast/uscrn.sensors.csv`
reads the public [precip.ai nowcast archive](https://api-docs.precip.ai/nowcast-archive) (Icechunk repository
`precip-rate-v4/5min`, branch `main`, group `mrms_native`, variable `precipitation_rate` in mm/h) at the nearest
grid cell of every sensor. It needs Python 3.12 (`icechunk>=2.0`, `xarray>=2025.6`).

- A run of the archive (every 5 minutes, leads 0–115 min) is published once its init time is at least 24 hours old.
  Every hourly run picks up the archive runs initialized after the last published one, which is kept in
  `<download path>/last_init_time`.
- Every archive run is uploaded as `<s3 uri>/<init time>.zip` with `<init time>/precipai.csv`
  (`id, lon, lat, grid_lon, grid_lat, lead_time, precipitation_rate`; `lead_time` in seconds, cells without data are
  left out) and `<init time>/snapshot.json` with the Icechunk `snapshot_id` the points were read from.
- The archive covers CONUS only, sensors outside the grid get no rows.
- Data: Precip ([precip.ai](https://precip.ai)), free for non-commercial research and benchmarking with attribution.

`uscrn.sensors.csv` lists the operational USCRN stations (ids `uscrn_<WBAN>`, as the metrics USCRN parser names them).
It is generated from the NCEI station list:

```bash
curl -s https://www.ncei.noaa.gov/pub/data/uscrn/products/stations.tsv | python3 -c "
import csv, sys
rows = [r for r in csv.DictReader(sys.stdin, delimiter='\\t') if r['NETWORK'] == 'USCRN' and r['OPERATION'] == 'Operational']
print('id,lon,lat,country')
for r in sorted(rows, key=lambda r: r['WBAN']):
    print(f\"uscrn_{r['WBAN']},{float(r['LONGITUDE'])},{float(r['LATITUDE'])},USA\")
" > uscrn.sensors.csv
```
