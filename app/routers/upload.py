from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    DailySchedule,
    MonthlyForecast,
    ProductGroup,
    ProductionHistory,
    SteelGrade,
)
from app.schemas import UploadResponse
from app.services.parser import Parser

router = APIRouter(prefix="/upload", tags=["upload"])


def get_or_create_product_group(db: Session, name: str) -> ProductGroup:
    """Get existing product group or create a new one."""
    product_group = db.query(ProductGroup).filter(ProductGroup.name == name).first()
    if not product_group:
        product_group = ProductGroup(name=name)
        db.add(product_group)
        db.flush()
    return product_group


def get_or_create_steel_grade(
    db: Session, name: str, product_group_id: int
) -> SteelGrade:
    """Get existing steel grade or create a new one."""
    steel_grade = db.query(SteelGrade).filter(SteelGrade.name == name).first()
    if not steel_grade:
        steel_grade = SteelGrade(name=name, product_group_id=product_group_id)
        db.add(steel_grade)
        db.flush()
    return steel_grade


@router.post("/daily-schedule", response_model=UploadResponse)
async def upload_daily_schedule(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload daily charge schedule Excel file.

    Parses the file and stores schedule records in the database.
    Creates steel grades and product groups as needed.
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)",
        )

    try:
        records = Parser.parse_daily_schedule(file.file)

        if not records:
            raise HTTPException(
                status_code=400,
                detail="Error parsing the file, please ensure it follows the template",
            )

        db.query(DailySchedule).delete()

        for record in records:
            product_group_name = Parser.get_product_group_for_grade(record.grade)

            if product_group_name:
                product_group = get_or_create_product_group(db, product_group_name)
                steel_grade = get_or_create_steel_grade(
                    db,
                    record.grade,
                    product_group.id,  # type: ignore
                )
            else:
                product_group = get_or_create_product_group(db, "Unknown")
                steel_grade = get_or_create_steel_grade(
                    db,
                    record.grade,
                    product_group.id,  # type: ignore
                )

            schedule = DailySchedule(
                date=record.date,
                start_time=record.start_time,
                steel_grade_id=steel_grade.id,
                mould_size=record.mould_size,
            )
            db.add(schedule)

        db.commit()

        return UploadResponse(
            message="Daily schedule uploaded successfully",
            records_processed=len(records),
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}",
        )


@router.post("/monthly-forecast", response_model=UploadResponse)
async def upload_monthly_forecast(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload product groups monthly forecast Excel file.

    Parses the file and stores forecast records in the database.
    Creates product groups as needed.
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)",
        )

    try:
        records = Parser.parse_monthly_forecast(file.file)

        if not records:
            raise HTTPException(
                status_code=400,
                detail="No valid records found in the uploaded file",
            )

        db.query(MonthlyForecast).delete()

        for record in records:
            product_group = get_or_create_product_group(db, record.product_group)

            forecast = MonthlyForecast(
                product_group_id=product_group.id,
                month=record.month,
                heats=record.heats,
            )
            db.add(forecast)

        db.commit()

        return UploadResponse(
            message="Monthly forecast uploaded successfully",
            records_processed=len(records),
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}",
        )


@router.post("/production-history", response_model=UploadResponse)
async def upload_production_history(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload steel grade production history Excel file.

    Parses the file and stores production records in the database.
    Creates steel grades and product groups as needed.
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)",
        )

    try:
        records = Parser.parse_production_history(file.file)

        if not records:
            raise HTTPException(
                status_code=400,
                detail="No valid records found in the uploaded file",
            )

        db.query(ProductionHistory).delete()

        for record in records:
            product_group = get_or_create_product_group(db, record.product_group)
            steel_grade = get_or_create_steel_grade(db, record.grade, product_group.id)  # type: ignore

            history = ProductionHistory(
                steel_grade_id=steel_grade.id,
                month=record.month,
                tons=record.tons,
            )
            db.add(history)

        db.commit()

        return UploadResponse(
            message="Production history uploaded successfully",
            records_processed=len(records),
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}",
        )
