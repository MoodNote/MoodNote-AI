"""
Convert manual-audit annotation sheets between CSV and Excel, so raters can work in Excel only.

    python -m src.qa.sheet_convert data/synthetic/audit/rater_a.csv data/synthetic/audit/rater_b.csv
    python -m src.qa.sheet_convert data/synthetic/audit/rater_a.xlsx data/synthetic/audit/rater_b.xlsx

manual_audit writes and the acceptance gate reads CSV. Each file is converted to the other format
next to it, picked by its extension: .csv -> .xlsx before labelling, .xlsx -> .csv (UTF-8 with
BOM, same as manual_audit writes) before running the gate. An existing .xlsx is never
overwritten, because it may already hold a rater's labels.
"""

import argparse
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment

from ..utils.logger import get_logger, setup_logger

logger = get_logger("sheet_convert")


def write_xlsx(sheet: pd.DataFrame, path: Path) -> None:
    """
    Write a sheet to Excel with its `text` column wide and wrapped, so entries are readable.

    Args:
        sheet: Rows to write; must have a `text` column
        path: Output .xlsx path
    """
    column = sheet.columns.get_loc("text") + 1
    with pd.ExcelWriter(path) as writer:
        sheet.to_excel(writer, index=False)
        worksheet = writer.sheets["Sheet1"]
        worksheet.column_dimensions[worksheet.cell(1, column).column_letter].width = 100
        for (cell,) in worksheet.iter_rows(min_row=2, min_col=column, max_col=column):
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def convert_sheet(path: Path) -> Path:
    """
    Convert one annotation sheet to the other format, next to the source file.

    Args:
        path: A .csv sheet (to .xlsx) or a .xlsx sheet (to .csv)

    Returns:
        Path of the written file
    """
    if path.suffix == ".csv":
        target = path.with_suffix(".xlsx")
        if target.exists():
            raise FileExistsError(f"{target} already exists, not overwriting: it may hold labels")
        write_xlsx(pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False), target)
    elif path.suffix == ".xlsx":
        target = path.with_suffix(".csv")
        sheet = pd.read_excel(path, dtype=str, keep_default_na=False)
        sheet.to_csv(target, index=False, encoding="utf-8-sig")
    else:
        raise ValueError(f"{path}: expected a .csv or .xlsx sheet")
    logger.info(f"{path} -> {target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    setup_logger()
    for sheet_path in args.paths:
        convert_sheet(sheet_path)
