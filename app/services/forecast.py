from datetime import date
from sqlalchemy.orm import Session

from app.models import MonthlyForecast, ProductGroup, ProductionHistory, SteelGrade
from app.schemas import GradeForecast


class Forecaster:
    """Calculates heat distribution forecasts based on historical production.

    Uses weighted recent history: more recent months have higher influence.
    Weights: most recent = 3x, second = 2x, third = 1x
    """

    MONTH_WEIGHTS = [3, 2, 1]

    def __init__(self, db: Session):
        self.db = db

    def calculate(self, target_month: date) -> list[GradeForecast]:
        """
        Calculate heat distribution by steel grade for a target month.

        Steps:
        1. Get the forecast heats per product group for target month
        2. Calculate weighted historical production per grade
        3. Distribute heats proportionally based on weighted totals
        """
        results: list[GradeForecast] = []

        forecasts = (
            self.db.query(MonthlyForecast)
            .join(ProductGroup)
            .filter(MonthlyForecast.month == target_month)
            .all()
        )

        for forecast in forecasts:
            grade_forecasts = self._process_product_group(forecast, target_month)
            results.extend(grade_forecasts)

        return results

    def _get_month_weight(self, production_month: date, target_month: date) -> float:
        """Calculate weight for a historical month based on recency."""
        months_ago = (target_month.year - production_month.year) * 12 + (
            target_month.month - production_month.month
        )

        if months_ago <= 0 or months_ago > len(self.MONTH_WEIGHTS):
            return self.MONTH_WEIGHTS[-1]  # Default to lowest weight

        return self.MONTH_WEIGHTS[months_ago - 1]

    def _process_product_group(
        self, forecast: MonthlyForecast, target_month: date
    ) -> list[GradeForecast]:
        """Process a single product group and return grade forecasts."""
        group_id = forecast.product_group_id
        group_name: str = forecast.product_group.name  # type: ignore
        total_heats: int = forecast.heats  # type: ignore

        # Get production history with month info for weighting
        history = (
            self.db.query(
                SteelGrade.name,
                ProductionHistory.month,
                ProductionHistory.tons,
            )
            .join(ProductionHistory)
            .filter(SteelGrade.product_group_id == group_id)
            .all()
        )

        if not history:
            return []

        # Calculate weighted totals per grade
        grade_weighted_totals: dict[str, float] = {}
        for record in history:
            weight = self._get_month_weight(record.month, target_month)
            weighted_tons = (record.tons or 0) * weight
            grade_weighted_totals[record.name] = (
                grade_weighted_totals.get(record.name, 0) + weighted_tons
            )

        group_weighted_total = sum(grade_weighted_totals.values())

        if group_weighted_total == 0:
            return self._distribute_equally(
                list(grade_weighted_totals.keys()), group_name, total_heats
            )
        else:
            return self._distribute_proportionally(
                grade_weighted_totals, group_name, total_heats, group_weighted_total
            )

    def _distribute_equally(
        self, grades: list[str], group_name: str, total_heats: int
    ) -> list[GradeForecast]:
        """Distribute heats equally when no historical data exists."""
        heats_per_grade = int(total_heats) // len(grades)
        return [
            GradeForecast(grade=grade, product_group=group_name, heats=heats_per_grade)
            for grade in grades
        ]

    def _distribute_proportionally(
        self,
        grade_weighted_totals: dict[str, float],
        group_name: str,
        total_heats: int,
        group_weighted_total: float,
    ) -> list[GradeForecast]:
        """Distribute heats based on weighted historical production ratios."""
        total_heats_int = int(total_heats)
        grades = list(grade_weighted_totals.items())

        # Calculate raw (non-rounded) allocations and sort by remainder descending
        allocations: list[tuple[str, int, float]] = []
        for grade_name, weighted_tons in grades:
            ratio = weighted_tons / group_weighted_total
            raw = ratio * total_heats_int
            floored = int(raw)
            remainder = raw - floored
            allocations.append((grade_name, floored, remainder))

        # Sum of floored values
        floored_total = sum(a[1] for a in allocations)
        leftover = total_heats_int - floored_total

        # Sort by remainder descending to distribute leftover fairly
        allocations.sort(key=lambda x: x[2], reverse=True)

        # Distribute leftover one heat at a time to grades with highest remainders
        results: list[GradeForecast] = []
        for i, (grade_name, floored, _) in enumerate(allocations):
            heats = floored + (1 if i < leftover else 0)
            results.append(
                GradeForecast(grade=grade_name, product_group=group_name, heats=heats)
            )

        return results
