import json
import os
import typing

from .helpers import join_abs_path


def get_dataset_names(datasets_dir: str) -> typing.List[str]:
    """
    Returns a list of dataset names
    """
    datasets = [
        d
        for d in os.listdir(datasets_dir)
        if os.path.isdir(os.path.join(datasets_dir, d)) and not d.startswith(".")
    ]

    return datasets


def get_datasets_with_simplified_layers(
    data_dir: str,
) -> typing.Dict[str, typing.List[str]]:
    """
    Returns a dictionary of dataset names and their simplified layer names
    """

    datasets_names = get_dataset_names(data_dir)

    result = {}

    for dataset_name in datasets_names:
        dataset_dir = join_abs_path(data_dir, dataset_name)

        meta_file = os.path.join(dataset_dir, "meta.json")

        with open(meta_file) as f:
            meta = json.load(f)

        layers = list(meta["simplifiedLayers"].keys())

        result[dataset_name] = layers

    return result
