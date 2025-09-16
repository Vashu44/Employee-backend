from datetime import date
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract, func
import logging
from model.holiday_model import Holiday

class DatabaseHolidayService:
    def __init__(self, db: Session):
        self.db = db
        self.data_source = "MySQL Database"

    # Keep your existing methods and add these new ones:
    
    def get_public_holiday_for_date(self, target_date: date, calendar_id: str = "0") -> Optional[Holiday]:
        """Get public holiday for a specific date"""
        query = self.db.query(Holiday)
        query = query.filter(Holiday.date == target_date)
        query = query.filter(Holiday.calendar_id == calendar_id)
        query = query.filter(Holiday.is_active == True)
        
        return query.first()

    def get_public_holidays_for_month(self, year: int, month: int, calendar_id: str = "0") -> List[Holiday]:
        """Get public holidays for a specific month"""
        query = self.db.query(Holiday)
        query = query.filter(
            and_(
                extract('year', Holiday.date) == year,
                extract('month', Holiday.date) == month
            )
        )
        query = query.filter(Holiday.calendar_id == calendar_id)
        query = query.filter(Holiday.is_active == True)
        
        return query.order_by(Holiday.date).all()

    def get_public_holidays_for_year(self, year: int, calendar_id: int = 0 ) -> List[Holiday]:
        """Get public holidays for a specific year"""
        query = self.db.query(Holiday)
        query = query.filter(extract('year', Holiday.date) == year)
        query = query.filter(Holiday.calendar_id == calendar_id)
        query = query.filter(Holiday.is_active == True)

        holidays = query.order_by(Holiday.date).all()
        logging.info(f"Found {len(holidays)} public holidays for year {year}")
        return holidays
        

    def get_public_holiday_stats(self, year: int, calendar_id: str = "0") -> Dict:
        """Get statistics for public holidays"""
        query = self.db.query(Holiday)
        query = query.filter(Holiday.calendar_id == calendar_id)
        query = query.filter(Holiday.is_active == True)
        query = query.filter(extract('year', Holiday.date) == year)
        
        total_count = query.count()
        
        return {
            "total_holidays": total_count,
            "calendar_id": calendar_id,
            "year": year
        }

    def get_public_available_years(self, calendar_id: str = "0") -> List[int]:
        """Get available years for public calendar"""
        years = self.db.query(extract('year', Holiday.date).label('year')).filter(
            Holiday.calendar_id == calendar_id,
            Holiday.is_active == True
        ).distinct().all()
        return sorted([year[0] for year in years])

    # Keep all your existing methods as they are
    def get_holidays_for_year(self, year: int, region_id: Optional[int] = None) -> List[Holiday]:
        """Get holidays for a specific year from database"""
        query = self.db.query(Holiday)
        query = query.filter(extract('year', Holiday.date) == year)
        query = query.filter(Holiday.is_active == True)
        
        holidays = query.order_by(Holiday.date).all()
        logging.info(f"Found {len(holidays)} holidays for year {year} from database")
        return holidays

    def get_holiday_for_date(self, target_date: date, region_id: Optional[int] = None) -> Optional[Holiday]:
        """Check if a specific date is a holiday"""
        query = self.db.query(Holiday)
        query = query.filter(Holiday.date == target_date)
        query = query.filter(Holiday.is_active == True)
        
        return query.first()

    def get_holidays_for_month(self, year: int, month: int, region_id: Optional[int] = None) -> List[Holiday]:
        """Get holidays for a specific month"""
        query = self.db.query(Holiday)
        query = query.filter(
            and_(
                extract('year', Holiday.date) == year,
                extract('month', Holiday.date) == month
            )
        )
        query = query.filter(Holiday.is_active == True)
        
        return query.order_by(Holiday.date).all()

    def get_available_years(self) -> List[int]:
        """Get list of available years in database"""
        years = self.db.query(extract('year', Holiday.date).label('year')).distinct().all()
        return sorted([year[0] for year in years])

    def get_holiday_stats(self, region_id: Optional[int] = None) -> Dict:
        """Get statistics about available holiday data"""
        query = self.db.query(Holiday)
        query = query.filter(Holiday.is_active == True)
        
        stats = {}
        years = self.get_available_years()
        
        for year in years:
            year_query = query.filter(extract('year', Holiday.date) == year)
            total_count = year_query.count()
            
            stats[year] = {
                "total_holidays": total_count
            }
        
        return stats

    def search_holidays(self, search_term: str, year: Optional[int] = None) -> List[Holiday]:
        """Search holidays by name or description"""
        query = self.db.query(Holiday)
        query = query.filter(Holiday.is_active == True)
        
        search_filter = func.lower(Holiday.name).contains(search_term.lower()) | \
                       func.lower(Holiday.description).contains(search_term.lower())
        
        query = query.filter(search_filter)
        
        if year:
            query = query.filter(extract('year', Holiday.date) == year)
        
        return query.order_by(Holiday.date).all()