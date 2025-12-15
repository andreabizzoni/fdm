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


def calculate_forecast(db: Session, target_month: date) -> list[GradeForecast]:
    """
    Calculate heat distribution by steel grade for a target month.

    Steps:
    1. Get the forecast heats per product group for target month
    2. Calculate historical production ratios per grade within each group
    3. Distribute heats proportionally
    """
    results: list[GradeForecast] = []

    # Get forecasts for target month by product group
    forecasts = (
        db.query(MonthlyForecast)
        .join(ProductGroup)
        .filter(MonthlyForecast.month == target_month)
        .all()
    )

    for forecast in forecasts:
        group_id = forecast.product_group_id
        group_name: str = forecast.product_group.name  # type: ignore
        total_heats: int = forecast.heats  # type: ignore

        # Get total historical production per grade in this group
        grade_totals = (
            db.query(
                SteelGrade.name, func.sum(ProductionHistory.tons).label("total_tons")
            )
            .join(ProductionHistory)
            .filter(SteelGrade.product_group_id == group_id)
            .group_by(SteelGrade.id)
            .all()
        )

        if not grade_totals:
            continue

        # Calculate total tons for the group
        group_total_tons = sum(g.total_tons or 0 for g in grade_totals)

        if group_total_tons == 0:
            # Equal distribution if no history
            heats_per_grade = int(total_heats) // len(grade_totals)
            for grade in grade_totals:
                results.append(
                    GradeForecast(
                        grade=grade.name,
                        product_group=group_name,
                        heats=heats_per_grade,
                    )
                )
        else:
            # Proportional distribution based on historical tons
            allocated = 0
            grade_list = list(grade_totals)
            total_heats_int = int(total_heats)

            for i, grade in enumerate(grade_list):
                ratio = (grade.total_tons or 0) / group_total_tons

                if i == len(grade_list) - 1:
                    # Last grade gets remainder to ensure total matches
                    heats = total_heats_int - allocated
                else:
                    heats = round(ratio * total_heats_int)
                    allocated += heats

                results.append(
                    GradeForecast(
                        grade=grade.name, product_group=group_name, heats=heats
                    )
                )

    return results
