import os


def join_abs_path(*paths: str) -> str:
    """
    Joins paths and returns an absolute path instead of a relative one
    """
    return os.path.abspath(os.path.join(*paths))
