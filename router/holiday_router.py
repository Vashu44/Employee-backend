from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from calendar import monthcalendar, month_name
from typing import Optional, List
import logging
import csv
import io
from datetime import datetime

# Import your existing modules (adjust paths as needed)
from db.database import get_db
from model.region_model import Region
from model.holiday_model import Holiday
from Schema.holiday_schema import HolidayCalendarResponse, HolidayResponse,HolidayEventCreate,HolidayEventUpdate,CSVUploadResponse
from service.holiday_service import DatabaseHolidayService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/holidays")


@router.get("/calendar", response_model=HolidayCalendarResponse)
async def get_holiday_calendar(
    year: Optional[int] = Query(None, description="Specific year (default: current year)"),
    month: Optional[int] = Query(0, description="Month (0=whole year, 1-12=specific month)"),
    date: Optional[int] = Query(0, description="Date (0=whole month, 1-31=specific date)"),
    db: Session = Depends(get_db)
):
    """
    Public Holiday Calendar - displays holidays with calendar_id = '000'
    """
    try:
        # Initialize holiday service
        holiday_service = DatabaseHolidayService(db)

        # Set default year to current year if not provided
        if not year:
            year = datetime.now().year

        # Validation
        if month != 0 and not (1 <= month <= 12):
            raise HTTPException(status_code=400, detail="Month must be 1-12")
        if date != 0 and not (1 <= date <= 31):
            raise HTTPException(status_code=400, detail="Date must be 1-31")
        if date != 0 and month == 0:
            raise HTTPException(status_code=400, detail="Month is required when date is specified")

        # Fetch holidays based on filters (calendar_id = '000' for public holidays)
        if date != 0:
            target_date = datetime(year, month, date).date()
            holiday = holiday_service.get_public_holiday_for_date(target_date, calendar_id= 0)
            holidays_list = [holiday] if holiday else []
            filter_desc = f"{date} {month_name[month]} {year} - Public Holidays"
            request_type = "specific_date"
        elif month != 0:
            holidays_list = holiday_service.get_public_holidays_for_month(year, month, calendar_id= 0)
            filter_desc = f"{month_name[month]} {year} - Public Holidays"
            request_type = "specific_month"
        else:
            holidays_list = holiday_service.get_public_holidays_for_year(year, calendar_id= 0)
            filter_desc = f"Year {year} - Public Holidays"
            request_type = "full_year"

        # Convert to response format
        holidays = []
        for h in holidays_list:
            try:
                holidays.append(HolidayResponse(
                    id=h.id,
                    date=h.date,
                    name=h.name,
                    # type="holiday",
                    # is_public=True,
                    calendar_id=h.calendar_id
                ))
            except Exception as e:
                logger.error(f"Error processing holiday {h.id}: {str(e)}")
                continue

        # Generate calendar grid for month view
        cal_grid = None
        if month != 0 and date == 0:
            cal_grid = monthcalendar(year, month)

        # Get holiday statistics for public calendar
        holiday_stats = holiday_service.get_public_holiday_stats(year, calendar_id="000")
        available_years = holiday_service.get_public_available_years(calendar_id="000")

        return HolidayCalendarResponse(
            request_type=request_type,
            year=year,
            month=month if month else None,
            date=date if date else None,
            filter_description=filter_desc,
            calendar_grid=cal_grid,
            holidays=holidays,
            total_holidays=len(holidays),
            api_source="MySQL Database - Public Holiday Calendar (ID: 000)",
            available_years=available_years
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in holiday calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/add-event", response_model=dict)
async def add_holiday_event(
    event_data: HolidayEventCreate,
    db: Session = Depends(get_db)
):
    """
    Add a new holiday event to the public calendar (calendar_id = '000')
    """
    try:
        # Create new holiday event
        new_holiday = Holiday(
            name=event_data.name,
            date=event_data.date,
            calendar_id="000",  # Default public calendar
        )
        
        db.add(new_holiday)
        db.commit()
        db.refresh(new_holiday)
        
        return {
            "status": "success",
            "message": "Holiday event added successfully",
            "holiday_id": new_holiday.id,
            "calendar_id": "000"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding holiday event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add holiday event: {str(e)}")


@router.put("/update-event/{holiday_id}", response_model=dict)
async def update_holiday_event(
    holiday_id: int,
    event_data: HolidayEventUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing holiday event in the public calendar
    """
    try:
        # Find the holiday by ID and ensure it's from public calendar
        holiday = db.query(Holiday).filter(
            Holiday.id == holiday_id,
            Holiday.calendar_id == "000"
        ).first()
        
        if not holiday:
            raise HTTPException(status_code=404, detail="Holiday event not found in public calendar")
        
        # Update fields if provided
        if event_data.name is not None:
            holiday.name = event_data.name
        if event_data.date is not None:
            holiday.date = event_data.date
        
        db.commit()
        db.refresh(holiday)
        
        return {
            "status": "success",
            "message": "Holiday event updated successfully",
            "holiday_id": holiday.id,
            "calendar_id": "000"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating holiday event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update holiday event: {str(e)}")


@router.delete("/delete-event/{holiday_id}", response_model=dict)
async def delete_holiday_event(
    holiday_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a holiday event from the public calendar
    """
    try:
        # Find the holiday by ID and ensure it's from public calendar
        holiday = db.query(Holiday).filter(
            Holiday.id == holiday_id,
            Holiday.calendar_id == "000"
        ).first()
        
        if not holiday:
            raise HTTPException(status_code=404, detail="Holiday event not found in public calendar")
        
        db.delete(holiday)
        db.commit()
        
        return {
            "status": "success",
            "message": "Holiday event deleted successfully",
            "holiday_id": holiday_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting holiday event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete holiday event: {str(e)}")



@router.get("/region-calendar/{region_id}", response_model=HolidayCalendarResponse)
async def get_region_holiday_calendar(
    region_id: int,
    year: Optional[int] = Query(None, description="Specific year (default: current year)"),
    month: Optional[int] = Query(0, description="Month (0=whole year, 1-12=specific month)"),
    date: Optional[int] = Query(0, description="Date (0=whole month, 1-31=specific date)"),
    db: Session = Depends(get_db)
):
    """Holiday Calendar for a specific Region"""
    try:
        region = db.query(Region).filter(Region.id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")

        holiday_service = DatabaseHolidayService(db)

        if not year:
            year = datetime.now().year

        # Validation
        if month != 0 and not (1 <= month <= 12):
            raise HTTPException(status_code=400, detail="Month must be 1-12")
        if date != 0 and not (1 <= date <= 31):
            raise HTTPException(status_code=400, detail="Date must be 1-31")
        if date != 0 and month == 0:
            raise HTTPException(status_code=400, detail="Month is required when date is specified")

        # Fetch holidays
        if date != 0:
            target_date = datetime(year, month, date).date()
            holiday = holiday_service.get_holiday_for_date(target_date, region_id)
            holidays_list = [holiday] if holiday else []
            filter_desc = f"{date} {month_name[month]} {year} - {region.name}"
            request_type = "specific_date"
        elif month != 0:
            holidays_list = holiday_service.get_holidays_for_month(year, month, region_id)
            filter_desc = f"{month_name[month]} {year} - {region.name}"
            request_type = "specific_month"
        else:
            holidays_list = holiday_service.get_holidays_for_year(year, region_id)
            filter_desc = f"Year {year} - {region.name}"
            request_type = "full_year"

        holidays = []
        for h in holidays_list:
            try:
                holidays.append(HolidayResponse(
                    id=h.id,
                    date=h.date,
                    name=h.name,
                    type="holiday",
                    description=h.description,
                    is_public=True
                ))
            except Exception as e:
                logger.error(f"Error processing holiday {h.id}: {str(e)}")
                continue

        cal_grid = None
        if month != 0 and date == 0:
            cal_grid = monthcalendar(year, month)

        holiday_stats = holiday_service.get_holiday_stats(year, region_id)
        available_years = holiday_service.get_available_years(region_id)

        return HolidayCalendarResponse(
            request_type=request_type,
            year=year,
            month=month if month else None,
            date=date if date else None,
            filter_description=filter_desc,
            calendar_grid=cal_grid,
            holidays=holidays,
            total_holidays=len(holidays),
            api_source="MySQL Database - Region Specific",
            available_years=available_years
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in region holiday calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/upload-csv", response_model=CSVUploadResponse)
async def upload_holiday_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
        Upload a CSV file containing holiday data.
        Expected CSV format:
            name,date,calendar_id
            New Year,2025-01-01,000
            Republic Day,2025-01-26,000
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    try:
        # Read the CSV file
        contents = await file.read()
        csv_text = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        total_processed = 0
        successful_inserts = 0
        failed_inserts = 0
        errors = []

        for row in csv_reader:
            total_processed += 1
            try:
                # Convert date string to datetime.date object
                date_str = row.get('date', '').strip()
                try:
                    holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError(f"Invalid date format for {date_str}. Expected format: YYYY-MM-DD")

                # Create new holiday
                new_holiday = Holiday(
                    name=row.get('name', '').strip(),
                    date=holiday_date,
                    calendar_id=row.get('calendar_id', '000').strip()
                )
                
                # Add to database
                db.add(new_holiday)
                db.commit()
                successful_inserts += 1
                
            except Exception as e:
                failed_inserts += 1
                errors.append(f"Row {total_processed}: {str(e)}")
                db.rollback()
                continue

        return CSVUploadResponse(
            status="success" if failed_inserts == 0 else "partial_success",
            message="CSV upload completed",
            total_processed=total_processed,
            successful_inserts=successful_inserts,
            failed_inserts=failed_inserts,
            errors=errors if errors else None
        )

    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process CSV file: {str(e)}")
