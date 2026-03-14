import pandas as pd
from datetime import datetime
from math import radians, cos, sin, asin, sqrt, atan2, degrees

# load notebook source (or just define run_one_row directly since we know what it does)
import sys
import subprocess
import nbformat


def test():
    with open(
        "d:/Projects/volcanic_ash/simulation/analisis_dispersi_abu_batch_gagal.ipynb",
        "r",
        encoding="utf-8",
    ) as f:
        nb = nbformat.read(f, as_version=4)

    code_cells = []
    for c in nb.cells:
        if c.cell_type == "code":
            code_cells.append(c.source)

    exec_scope = {}

    # Exec the cells but not the last fill_dataset_targets call
    # find the part with batch_df and remove it
    for code in code_cells:
        if "batch_df =" in code:
            code = code.replace("batch_df = fill_dataset_targets()", "")
        exec(code, exec_scope)

    df = pd.read_csv("d:/Projects/volcanic_ash/simulation/sisa_gagal.csv")

    print("=== TEST ID 12 ===")
    r12 = df[df["id"] == 12].iloc[0]
    try:
        res = exec_scope["run_one_row"](r12)
        print("Success!", res)
    except Exception as e:
        import traceback

        traceback.print_exc()

    print("\n=== TEST ID 16 ===")
    r16 = df[df["id"] == 16].iloc[0]
    try:
        res = exec_scope["run_one_row"](r16)
        print("Success!", res)
    except Exception as e:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test()
