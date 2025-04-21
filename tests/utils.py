import os


def get_fixtures_folder() -> str:
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "fixtures")
