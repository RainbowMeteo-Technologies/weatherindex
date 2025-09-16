import argparse
import asyncio
import logging

from enum import Enum
from sensors.providers.geosphere import GeoSphereProvider
from sensors.providers.dwd import DWDProvider
from sensors.providers.fsdiopendata import FSDIOpenDataProvider
from sensors.providers.metar import MetarSource
from sensors.providers.tao_triton import TaoTritonProvider
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


def _create_geosphere(args: argparse.Namespace):
    publisher = _create_publisher(args)
    return GeoSphereProvider(publisher=publisher,
                             download_path=args.download_path)


def _create_dwd(args: argparse.Namespace):
    publisher = _create_publisher(args)
    return DWDProvider(publisher=publisher,
                       download_path=args.download_path)


def _create_fsdiopendata(args: argparse.Namespace):
    publisher = _create_publisher(args)
    return FSDIOpenDataProvider(publisher=publisher,
                                download_path=args.download_path)


def _create_tao_triton(args: argparse.Namespace):
    publisher = _create_publisher(args)
    return TaoTritonProvider(publisher=publisher,
                             download_path=args.download_path)


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

    # GeoSphere
    geosphere_parser = subparser.add_parser("geosphere", help="Download observations from Austria Geosphere API")
    geosphere_parser.set_defaults(func=_create_geosphere)

    # DWD
    dwd_parser = subparser.add_parser("dwd", help="Download observations from Germany DWD open data")
    dwd_parser.set_defaults(func=_create_dwd)

    # FSDIOpenData
    fsdiopendata_parser = subparser.add_parser("fsdiopendata",
                                               help="Download observations from Switzerland FSDI Open Data")
    fsdiopendata_parser.set_defaults(func=_create_fsdiopendata)

    # NDBC
    tao_triton_parser = subparser.add_parser("tao-triton", help="Download observations from National Data Buoy Center")
    tao_triton_parser.set_defaults(func=_create_tao_triton)

    args = parser.parse_args()

    asyncio.run(main(args))
