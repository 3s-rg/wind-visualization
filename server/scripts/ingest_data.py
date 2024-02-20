import os

from ..logic.ingest import get_ingestable_datasets, ingest_dataset
from ..logic.helpers import join_abs_path


# reads data from ../data/unprocessed and writes processed data to ../data/processed
# data is stored in trixels based on a Hierarchical Triangular Mesh (HTM), all trixels up to depth N are generated
# trixel ids looks like this: N0-0-1-2-3 (N0 is the root trixel, 0-1-2-3 is the path to the sub-trixel)
# /(N0|N1|N2|N3|S0|S1|S2|S3)(-[0-3])*/
# trixel paths looks like this: ../data/processed/[dataset]/N0/0/1/2/3/data.npy
# a chunk is a (n x 6) numpy array with the following columns:
# latitude, longitude, altitude, u, v, w


def process_data():
    scripts_dir = os.path.dirname(os.path.realpath(__file__))
    data_dir = join_abs_path(scripts_dir, "..", "data")
    unprocessed_dir = join_abs_path(data_dir, "unprocessed")
    processed_dir = join_abs_path(data_dir, "processed")

    print(f"Looking for datasets to process in {unprocessed_dir}")

    datasets = get_ingestable_datasets(unprocessed_dir, processed_dir)

    if len(datasets) == 0:
        print("No datasets to process")
        return

    print(
        f"Found {len(datasets)} dataset(s): {', '.join(map(lambda d: d.name, datasets))}"
    )

    for dataset in datasets:
        print(f"Processing {dataset}")

        ingest_dataset(dataset)

        print(f"Done processing {dataset}")

    print("Done processing all datasets")


if __name__ == "__main__":
    process_data()
