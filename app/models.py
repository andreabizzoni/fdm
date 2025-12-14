from sqlalchemy import Column, Integer, String, Float, Date, Time, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ProductGroup(Base):
    __tablename__ = "product_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    steel_grades = relationship("SteelGrade", back_populates="product_group")
    monthly_forecasts = relationship("MonthlyForecast", back_populates="product_group")


class SteelGrade(Base):
    __tablename__ = "steel_grades"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    product_group_id = Column(Integer, ForeignKey("product_groups.id"), nullable=False)

    product_group = relationship("ProductGroup", back_populates="steel_grades")
    production_history = relationship("ProductionHistory", back_populates="steel_grade")
    daily_schedules = relationship("DailySchedule", back_populates="steel_grade")


class MonthlyForecast(Base):
    __tablename__ = "monthly_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    product_group_id = Column(Integer, ForeignKey("product_groups.id"), nullable=False)
    month = Column(Date, nullable=False)
    heats = Column(Integer, nullable=False)

    product_group = relationship("ProductGroup", back_populates="monthly_forecasts")


class ProductionHistory(Base):
    __tablename__ = "production_history"

    id = Column(Integer, primary_key=True, index=True)
    steel_grade_id = Column(Integer, ForeignKey("steel_grades.id"), nullable=False)
    month = Column(Date, nullable=False)
    tons = Column(Float, nullable=False)

    steel_grade = relationship("SteelGrade", back_populates="production_history")


class DailySchedule(Base):
    __tablename__ = "daily_schedules"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    steel_grade_id = Column(Integer, ForeignKey("steel_grades.id"), nullable=False)
    mould_size = Column(String, nullable=True)

    steel_grade = relationship("SteelGrade", back_populates="daily_schedules")
