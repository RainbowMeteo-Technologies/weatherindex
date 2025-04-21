import argparse
from metrics.parse.parse import parse


def _run_parse(args: argparse.Namespace):
    parse(session_path=args.session_path,
          process_num=args.process_num)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool parses data into common format")

    subparsers = parser.add_subparsers(help="Available commands")

    common = parser.add_argument_group("Common parameters")
    common.add_argument("--process-num", type=int, dest="process_num", default=None, required=False,
                        help="Number of processes for multiprocessing")

    parser.add_argument("--session-path", type=str, dest="session_path", required=True,
                        help="Path to session")

    parser.set_defaults(func=_run_parse)

    args = parser.parse_args()
    args.func(args)
