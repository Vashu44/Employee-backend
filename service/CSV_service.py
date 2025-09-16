from fastapi import Depends
from typing import Optional
from db.database import get_db
import pandas as pd
from datetime import date, datetime

db_dependency = Depends(get_db)

class CSVUserDetailsProcessor:
    """CSV User Details Processing Class"""
    
    def __init__(self):
        self.required_columns = ['user_id']  
        self.optional_columns = [
            'full_name','personal_email','date_of_joining'
            'working_region_id', 'home_region_id', 'manager_name', 
            'current_Department', 'current_role', 'Project_name',
            'project_description', 'project_Start_date', 'project_End_date'
        ]
    
    def validate_csv_structure(self, df: pd.DataFrame) -> dict:
        """Validate CSV structure and return validation results"""
        errors = []
        warnings = []
        
        # Check required columns
        missing_required = [col for col in self.required_columns if col not in df.columns]
        if missing_required:
            errors.append(f"Missing required columns: {missing_required}")
        
        # Check for empty DataFrame
        if df.empty:
            errors.append("CSV file is empty")
        
        # Check for duplicate usernames/emails
        if 'username' in df.columns:
            duplicate_usernames = df[df['username'].duplicated()]['username'].tolist()
            if duplicate_usernames:
                warnings.append(f"Duplicate usernames found: {duplicate_usernames}")
        
        if 'email' in df.columns:
            duplicate_emails = df[df['email'].duplicated()]['email'].tolist()
            if duplicate_emails:
                warnings.append(f"Duplicate emails found: {duplicate_emails}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def parse_date(self, date_str) -> Optional[date]:
        """Parse date string to date object"""
        if pd.isna(date_str) or not date_str:
            return None
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    return datetime.strptime(str(date_str), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    def clean_data_row(self, row: pd.Series) -> dict:
        """Clean and prepare single row data"""
        clean_data = {}

        if 'user_id' in row and pd.notna(row['user_id']):
            try:
                clean_data['user_id'] = int(row['user_id'])
            except (ValueError, TypeError):
                clean_data['user_id'] = None
        else:
            clean_data['user_id'] = None
        
        # Handle string fields
        string_fields = [
            'username', 'personal_email', 'full_name', 'date_of_joining',
            'manager_name', 'current_Department', 'current_role',
            'Project_name', 'project_description', 'project_Start_date', 'project_End_date',
        ]
        
        for field in string_fields:
            if field in row and pd.notna(row[field]):
                clean_data[field] = str(row[field]).strip()
            else:
                clean_data[field] = None
        
        # Handle integer fields
        int_fields = ['working_region_id', 'home_region_id']
        for field in int_fields:
            if field in row and pd.notna(row[field]):
                try:
                    clean_data[field] = int(row[field])
                except (ValueError, TypeError):
                    clean_data[field] = None
            else:
                clean_data[field] = None
        
        # Handle date fields
        date_fields = ['project_Start_date', 'project_End_date']
        for field in date_fields:
            if field in row:
                clean_data[field] = self.parse_date(row[field])
            else:
                clean_data[field] = None
        
        return clean_data