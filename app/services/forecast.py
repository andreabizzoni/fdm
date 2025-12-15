"""
Forecast calculation logic.

Distributes heats across steel grades within each product group
based on historical production ratios.
"""

from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import MonthlyForecast, ProductGroup, ProductionHistory, SteelGrade
from app.schemas import GradeForecast


class Forecaster:
    """Calculates heat distribution forecasts based on historical production."""

    def __init__(self, db: Session):
        self.db = db

    def calculate(self, target_month: date) -> list[GradeForecast]:
        """
        Calculate heat distribution by steel grade for a target month.

        Steps:
        1. Get the forecast heats per product group for target month
        2. Calculate historical production ratios per grade within each group
        3. Distribute heats proportionally
        """
        results: list[GradeForecast] = []

        forecasts = (
            self.db.query(MonthlyForecast)
            .join(ProductGroup)
            .filter(MonthlyForecast.month == target_month)
            .all()
        )

        for forecast in forecasts:
            grade_forecasts = self._process_product_group(forecast)
            results.extend(grade_forecasts)

        return results

    def _process_product_group(self, forecast: MonthlyForecast) -> list[GradeForecast]:
        """Process a single product group and return grade forecasts."""
        group_id = forecast.product_group_id
        group_name: str = forecast.product_group.name  # type: ignore
        total_heats: int = forecast.heats  # type: ignore

        grade_totals = (
            self.db.query(
                SteelGrade.name, func.sum(ProductionHistory.tons).label("total_tons")
            )
            .join(ProductionHistory)
            .filter(SteelGrade.product_group_id == group_id)
            .group_by(SteelGrade.id)
            .all()
        )

        if not grade_totals:
            return []

        group_total_tons = sum(g.total_tons or 0 for g in grade_totals)

        if group_total_tons == 0:
            return self._distribute_equally(grade_totals, group_name, total_heats)
        else:
            return self._distribute_proportionally(
                grade_totals, group_name, total_heats, group_total_tons
            )

    def _distribute_equally(
        self, grade_totals: list, group_name: str, total_heats: int
    ) -> list[GradeForecast]:
        """Distribute heats equally when no historical data exists."""
        heats_per_grade = int(total_heats) // len(grade_totals)
        return [
            GradeForecast(
                grade=grade.name, product_group=group_name, heats=heats_per_grade
            )
            for grade in grade_totals
        ]

    def _distribute_proportionally(
        self,
        grade_totals: list,
        group_name: str,
        total_heats: int,
        group_total_tons: float,
    ) -> list[GradeForecast]:
        """Distribute heats based on historical production ratios."""
        results: list[GradeForecast] = []
        allocated = 0
        grade_list = list(grade_totals)
        total_heats_int = int(total_heats)

        for i, grade in enumerate(grade_list):
            ratio = (grade.total_tons or 0) / group_total_tons

            if i == len(grade_list) - 1:
                heats = total_heats_int - allocated
            else:
                heats = round(ratio * total_heats_int)
                allocated += heats

            results.append(
                GradeForecast(grade=grade.name, product_group=group_name, heats=heats)
            )

        return results
