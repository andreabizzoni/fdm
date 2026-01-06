from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    DailySchedule,
    MonthlyForecast,
    ProductGroup,
    ProductionHistory,
    SteelGrade,
)
from app.schemas import GradeForecast


class Forecaster:
    """Calculates heat distribution forecasts based on historical production and scheduled heats."""

    MONTH_WEIGHTS = [3, 2, 1]

    def __init__(self, db: Session):
        self.db = db

    def calculate(self, target_month: date) -> list[GradeForecast]:
        """Calculate heat distribution by steel grade for a target month."""
        results: list[GradeForecast] = []

        scheduled_heats = self._get_scheduled_heats(target_month)

        forecasts = (
            self.db.query(MonthlyForecast)
            .join(ProductGroup)
            .filter(MonthlyForecast.month == target_month)
            .all()
        )

        for forecast in forecasts:
            grade_forecasts = self._process_product_group(
                forecast, target_month, scheduled_heats
            )
            results.extend(grade_forecasts)

        return results

    def _get_scheduled_heats(self, target_month: date) -> dict[str, int]:
        """Get count of scheduled heats per grade for the target month."""
        month_start = target_month.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)

        scheduled = (
            self.db.query(
                SteelGrade.name, func.count(DailySchedule.id).label("heat_count")
            )
            .join(DailySchedule)
            .filter(DailySchedule.date >= month_start)
            .filter(DailySchedule.date < month_end)
            .group_by(SteelGrade.name)
            .all()
        )

        return {record.name: record.heat_count for record in scheduled}

    def _get_month_weight(self, production_month: date, target_month: date) -> float:
        """Calculate weight for a historical month based on recency."""
        months_ago = (target_month.year - production_month.year) * 12 + (
            target_month.month - production_month.month
        )

        if months_ago <= 0 or months_ago > len(self.MONTH_WEIGHTS):
            return self.MONTH_WEIGHTS[-1]

        return self.MONTH_WEIGHTS[months_ago - 1]

    def _process_product_group(
        self,
        forecast: MonthlyForecast,
        target_month: date,
        scheduled_heats: dict[str, int],
    ) -> list[GradeForecast]:
        """Process a single product group and return grade forecasts."""
        group_id = forecast.product_group_id
        group_name: str = forecast.product_group.name  # type: ignore
        total_heats: int = forecast.heats  # type: ignore

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

        grade_weighted_totals: dict[str, float] = {}
        for record in history:
            weight = self._get_month_weight(record.month, target_month)
            weighted_tons = (record.tons or 0) * weight
            grade_weighted_totals[record.name] = (
                grade_weighted_totals.get(record.name, 0) + weighted_tons
            )

        group_scheduled = {
            grade: scheduled_heats.get(grade, 0)
            for grade in grade_weighted_totals.keys()
        }
        total_scheduled = sum(group_scheduled.values())
        remaining_heats = max(0, total_heats - total_scheduled)

        group_weighted_total = sum(grade_weighted_totals.values())

        if group_weighted_total == 0:
            historical_distribution = {
                grade: 0 for grade in grade_weighted_totals.keys()
            }
        else:
            historical_distribution = self._distribute_proportionally(
                grade_weighted_totals, remaining_heats, group_weighted_total
            )

        results: list[GradeForecast] = []
        for grade in grade_weighted_totals.keys():
            scheduled = group_scheduled.get(grade, 0)
            from_history = historical_distribution.get(grade, 0)
            results.append(
                GradeForecast(
                    grade=grade,
                    product_group=group_name,
                    heats=scheduled + from_history,
                )
            )

        return results

    def _distribute_proportionally(
        self,
        grade_weighted_totals: dict[str, float],
        total_heats: int,
        group_weighted_total: float,
    ) -> dict[str, int]:
        """Distribute heats based on weighted historical production ratios."""
        total_heats_int = int(total_heats)
        grades = list(grade_weighted_totals.items())

        allocations: list[tuple[str, int, float]] = []
        for grade_name, weighted_tons in grades:
            ratio = weighted_tons / group_weighted_total
            raw = ratio * total_heats_int
            floored = int(raw)
            remainder = raw - floored
            allocations.append((grade_name, floored, remainder))

        floored_total = sum(a[1] for a in allocations)
        leftover = total_heats_int - floored_total

        allocations.sort(key=lambda x: x[2], reverse=True)

        results: dict[str, int] = {}
        for i, (grade_name, floored, _) in enumerate(allocations):
            heats = floored + (1 if i < leftover else 0)
            results[grade_name] = heats

        return results
