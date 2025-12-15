from datetime import date, time, datetime
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from app.schemas import (
    DailyScheduleRecord,
    MonthlyForecastRecord,
    ProductionHistoryRecord,
)

FileInput = str | Path | BinaryIO


class Parser:
    """Parser for Excel files containing steel production data."""

    # Product group to steel grade mapping for validation/lookup
    PRODUCT_GROUP_MAPPING = {
        "Rebar": ["B500A", "B500B", "B500C"],
        "MBQ": ["A36", "A5888", "GR50", "44W", "50W", "55W", "60W"],
        "SBQ": ["S235JR", "S355J", "C35", "C40"],
        "CHQ": [
            "A53/A543",
            "A53/C591",
            "A53/C592",
            "A53/C593",
            "A53/C594",
            "A53/C595",
            "A53/C596",
            "A53/C597",
            "A53/C598",
            "A53/C599",
            "A53/C600",
        ],
    }

    @classmethod
    def get_product_group_for_grade(cls, grade: str) -> str | None:
        """Look up which product group a steel grade belongs to."""
        for group, grades in cls.PRODUCT_GROUP_MAPPING.items():
            if grade in grades:
                return group
        return None

    @staticmethod
    def parse_daily_schedule(file: FileInput) -> list[DailyScheduleRecord]:
        """
        Parse daily_charge_schedule.xlsx file.

        File structure:
        - Row 0: Title row ("Daily charge schedule")
        - Row 1: Date headers across columns (e.g., "Friday 8/30/2024")
        - Row 2: Column headers (Start time, Grade, Mould size) repeated for each day
        - Row 3+: Data rows with times, grades, and mould sizes

        Each day has 3 columns: Start time, Grade, Mould size
        Empty grades or "-" indicate no heat scheduled.
        """
        # Read the Excel file, skipping the title row
        df = pd.read_excel(file, header=None, skiprows=1)

        records: list[DailyScheduleRecord] = []

        # Row 0 (after skip) contains dates, row 1 contains column headers
        date_row = df.iloc[0]
        data_rows = df.iloc[2:]  # Skip date row and header row

        # Process each group of 3 columns (one per day)
        col_idx = 0
        while col_idx < len(df.columns):
            # Get the date from the header row
            date_cell = date_row.iloc[col_idx]

            if pd.isna(date_cell):
                col_idx += 3
                continue

            # Parse date - can be datetime object or string like "Friday 8/30/2024"
            try:
                if isinstance(date_cell, datetime):
                    date_value = date_cell.date()
                elif isinstance(date_cell, date):
                    date_value = date_cell
                else:
                    date_str = str(date_cell)
                    # Extract the date portion (after the day name)
                    date_parts = date_str.split()
                    if len(date_parts) >= 2:
                        date_value = datetime.strptime(
                            date_parts[-1], "%m/%d/%Y"
                        ).date()
                    else:
                        col_idx += 3
                        continue
            except (ValueError, IndexError):
                col_idx += 3
                continue

            # Process data rows for this day
            for _, row in data_rows.iterrows():
                time_cell = row.iloc[col_idx] if col_idx < len(row) else None
                grade_cell = row.iloc[col_idx + 1] if col_idx + 1 < len(row) else None
                mould_cell = row.iloc[col_idx + 2] if col_idx + 2 < len(row) else None

                # Skip if no time or grade
                if pd.isna(time_cell) or pd.isna(grade_cell):
                    continue

                grade = str(grade_cell).strip()

                # Skip empty grades or placeholder values
                if grade == "-" or grade == "" or grade.lower() == "nan":
                    continue

                # Parse time
                try:
                    if isinstance(time_cell, time):
                        time_value = time_cell
                    elif isinstance(time_cell, datetime):
                        time_value = time_cell.time()
                    else:
                        time_str = str(time_cell).strip()
                        # Handle H:MM format
                        time_value = datetime.strptime(time_str, "%H:%M").time()
                except ValueError:
                    continue

                # Parse mould size (optional)
                mould_size = None
                if not pd.isna(mould_cell):
                    mould_size = str(mould_cell).strip()
                    if mould_size == "-":
                        mould_size = None

                records.append(
                    DailyScheduleRecord(
                        date=date_value,
                        start_time=time_value,
                        grade=grade,
                        mould_size=mould_size,
                    )
                )

            col_idx += 3

        return records

    @staticmethod
    def parse_monthly_forecast(file: FileInput) -> list[MonthlyForecastRecord]:
        """
        Parse product_groups_monthly.xlsx file.

        File structure:
        - Row 0: Title ("Order forecast (heats per quality group)")
        - Row 1: Headers - "Quality:", Jun 24, Jul 24, Aug 24, Sep 24
        - Row 2+: Data - Product group name, heat counts per month
        """
        # Read the Excel file
        df = pd.read_excel(file, header=None, skiprows=1)

        records: list[MonthlyForecastRecord] = []

        # Row 0 (after skip) has headers including month names
        header_row = df.iloc[0]

        # Parse month columns (starting from column 1)
        months: list[date] = []
        for col_idx in range(1, len(header_row)):
            month_cell = header_row.iloc[col_idx]
            if pd.isna(month_cell):
                break

            # Parse month - can be datetime object or string like "Jun 24"
            try:
                if isinstance(month_cell, datetime):
                    month_date = month_cell.date().replace(day=1)
                elif isinstance(month_cell, date):
                    month_date = month_cell.replace(day=1)
                else:
                    month_str = str(month_cell).strip()
                    month_date = (
                        datetime.strptime(month_str, "%b %y").date().replace(day=1)
                    )
                months.append(month_date)
            except ValueError:
                continue

        # Process data rows (starting from row 1 after header)
        data_rows = df.iloc[1:]

        for _, row in data_rows.iterrows():
            product_group = row.iloc[0]

            if pd.isna(product_group):
                continue

            product_group = str(product_group).strip()

            # Get heat counts for each month
            for month_idx, month_date in enumerate(months):
                col_idx = month_idx + 1
                if col_idx < len(row):
                    heats_cell = row.iloc[col_idx]
                    if not pd.isna(heats_cell):
                        try:
                            heats = int(float(heats_cell))
                            records.append(
                                MonthlyForecastRecord(
                                    product_group=product_group,
                                    month=month_date,
                                    heats=heats,
                                )
                            )
                        except (ValueError, TypeError):
                            continue

        return records

    @staticmethod
    def parse_production_history(file: FileInput) -> list[ProductionHistoryRecord]:
        """
        Parse steel_grade_production.xlsx file.

        File structure:
        - Row 0: Title ("Production history (short tons)")
        - Row 1: Headers - "Quality group", "Grade", Jun 24, Jul 24, Aug 24, ...
        - Row 2+: Data rows with quality group (may be empty if same as above), grade, tons per month
        """
        # Read the Excel file
        df = pd.read_excel(file, header=None, skiprows=1)

        records: list[ProductionHistoryRecord] = []

        # Row 0 (after skip) has headers
        header_row = df.iloc[0]

        # Parse month columns (starting from column 2)
        months: list[date] = []
        for col_idx in range(2, len(header_row)):
            month_cell = header_row.iloc[col_idx]
            if pd.isna(month_cell):
                break

            # Parse month - can be datetime object or string like "Jun 24"
            try:
                if isinstance(month_cell, datetime):
                    month_date = month_cell.date().replace(day=1)
                elif isinstance(month_cell, date):
                    month_date = month_cell.replace(day=1)
                else:
                    month_str = str(month_cell).strip()
                    month_date = (
                        datetime.strptime(month_str, "%b %y").date().replace(day=1)
                    )
                months.append(month_date)
            except ValueError:
                break

        # Process data rows
        data_rows = df.iloc[1:]
        current_product_group: str | None = None

        for _, row in data_rows.iterrows():
            # Product group may be in column 0, or empty if continuing from previous
            group_cell = row.iloc[0]
            grade_cell = row.iloc[1]

            # Update product group if provided
            if not pd.isna(group_cell):
                group_str = str(group_cell).strip()
                if group_str:
                    current_product_group = group_str

            # Skip if no grade
            if pd.isna(grade_cell):
                continue

            grade = str(grade_cell).strip()
            if not grade:
                continue

            # Get tons for each month
            for month_idx, month_date in enumerate(months):
                col_idx = month_idx + 2  # Offset by 2 (group and grade columns)
                if col_idx < len(row):
                    tons_cell = row.iloc[col_idx]
                    if not pd.isna(tons_cell):
                        try:
                            tons = float(tons_cell)
                            if current_product_group:
                                records.append(
                                    ProductionHistoryRecord(
                                        product_group=current_product_group,
                                        grade=grade,
                                        month=month_date,
                                        tons=tons,
                                    )
                                )
                        except (ValueError, TypeError):
                            continue

        return records
