import argparse
import asyncio
import logging

from enum import Enum
from sensors.providers.austria import AustriaProvider
from sensors.providers.metar import MetarSource
from sensors.publishers.publisher import Publisher
from sensors.publishers.file import FilePublisher
from sensors.publishers.s3 import S3Publisher

logging.basicConfig(level=logging.INFO)


class ProviderName(Enum):
    NOAA = "noaa"


def _create_publisher(args: argparse.Namespace) -> Publisher:
    if args.storage_uri.startswith("s3://"):
        return S3Publisher(args.storage_uri)
    elif args.storage_uri.startswith("file://"):
        return FilePublisher(args.storage_uri.replace("file://", ""))
    else:
        raise ValueError(f"Unsupported storage URI: {args.storage_uri}")


def _create_metar(args: argparse.Namespace):
    publisher = _create_publisher(args)
    return MetarSource(publisher=publisher, download_path=args.download_path)


def _create_austria(args: argparse.Namespace):
    publisher = _create_publisher(args)
    return AustriaProvider(
        publisher=publisher, 
        download_path=args.download_path,
        api_endpoint=args.api_endpoint,
        timeout=args.timeout
    )


async def main(args: argparse.Namespace):
    provider = args.func(args)
    await provider.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--download-path", dest="download_path", type=str, default="/data",
                        help="Path to store downloaded data (used as temporary storage before upload to cloud)")

    parser.add_argument("--storage-uri", dest="storage_uri", type=str, required=True,
                        help=("URI of the storage to store the data. It could be local storage or any cloud storage. "
                              "Only `s3://` and `file://` are supported for now."))

    subparser = parser.add_subparsers(dest="provider", help="Available intergrations")

    # METAR
    metar_parser = subparser.add_parser("metar", help="Download observations from metar")
    metar_parser.set_defaults(func=_create_metar)

    # Austria
    austria_parser = subparser.add_parser("austria", help="Download observations from Austria Geosphere API")
    austria_parser.add_argument("--api-endpoint", dest="api_endpoint", type=str, 
                               default="https://dataset.api.hub.geosphere.at/v1/station/historical/tawes-v1-10min",
                               help="Austria Geosphere API endpoint URL")
    austria_parser.add_argument("--timeout", dest="timeout", type=int, default=30,
                               help="Request timeout in seconds")
    austria_parser.set_defaults(func=_create_austria)

    args = parser.parse_args()

    asyncio.run(main(args))
