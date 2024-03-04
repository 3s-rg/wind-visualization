import os
import sys

from logic.ingest import get_ingestable_datasets, ingest_dataset
from logic.helpers import join_abs_path


# usage: python -m server.ingest_data [input_dir] [output_dir]
# reads data from input_dir and writes processed data to output_dir
# data is stored in trixels based on a Hierarchical Triangular Mesh (HTM), all trixels up to depth N are generated
# trixel ids looks like this: N0-0-1-2-3 (N0 is the root trixel, 0-1-2-3 is the path to the sub-trixel)
# /(N0|N1|N2|N3|S0|S1|S2|S3)(-[0-3])*/
# trixel paths looks like this: ../data/processed/[dataset]/N0/0/1/2/3/data.npy
# a chunk is a (n x 6) numpy array with the following columns:
# latitude, longitude, altitude, u, v, w


def process_data(input_dir: str, output_dir: str) -> None:
    unprocessed_dir = join_abs_path(input_dir)
    processed_dir = join_abs_path(output_dir)

    if not os.path.exists(unprocessed_dir):
        print(f"Unprocessed directory {unprocessed_dir} does not exist")
        return

    # create processed directory if it does not exist
    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)

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
    if len(sys.argv) != 3:
        print("Usage: python -m server.scripts.ingest_data [input_dir] [output_dir]")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    process_data(input_dir, output_dir)
