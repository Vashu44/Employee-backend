from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
import io
import pandas as pd
import logging
from service.CSV_service import CSVUserDetailsProcessor
from db.database import get_db 
from model import usermodels, userDetails_model  

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/CSV")

# Database dependency
db_dependency = Depends(get_db)

@router.post("/upload-users-company-data", status_code=status.HTTP_201_CREATED)
async def upload_users_company_data(
    file: UploadFile = File(...),
    db: Session = db_dependency
):
    """
    CSV file se users aur unke details upload karne ka route
    Expected CSV columns:
    - Required: email
    - Optional: full_name, date_of_joining, & their Project related Details etc.
    """
    
    processor = CSVUserDetailsProcessor()
    
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400, 
                detail="Only CSV files are allowed"
            )
        
        # Read CSV file
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Validate CSV structure
        validation = processor.validate_csv_structure(df)
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"CSV validation failed: {validation['errors']}"
            )
        
        # Process data
        successful_inserts = []
        failed_inserts = []
        updated_users = []
        
        for index, row in df.iterrows():
            try:
                # Clean data
                clean_data = processor.clean_data_row(row)
                
                if not clean_data.get('user_id'):
                    failed_inserts.append({
                        'row': index + 1,
                        'error': 'User ID is required'
                    })
                    continue
                
                # Check if user already exists
                existing_user = db.query(usermodels.User).filter(
                    and_(
                        usermodels.User.id == clean_data['user_id']
                    )
                ).first()
                
                if existing_user:
                    # Update existing user details
                    user_details = db.query(userDetails_model.UserDetails).filter(
                        userDetails_model.UserDetails.user_id == existing_user.id
                    ).first()
                    
                    if not user_details:
                        # Create new user details
                        user_details = userDetails_model.UserDetails(
                            user_id=existing_user.id
                        )
                        db.add(user_details)
                    
                    # Update user details fields
                    for field in processor.optional_columns:
                        if field in clean_data and clean_data[field] is not None:
                            setattr(user_details, field, clean_data[field])
                    
                    db.commit()
                    updated_users.append({
                        'row': index + 1,
                        'user_id': existing_user.id,
                        'action': 'updated'
                    })
                    
                else:
                    # Create new user
                    new_user = usermodels.User(
                        email=clean_data['email'],
                        password="password",  # Set default password or generate
                        is_verified=0
                    )
                    
                    db.add(new_user)
                    db.flush()  # Get the user ID
                    
                    # Create user details
                    user_details = userDetails_model.UserDetails(
                        user_id=new_user.id
                    )
                    
                    # Set user details fields
                    for field in processor.optional_columns:
                        if field in clean_data and clean_data[field] is not None:
                            setattr(user_details, field, clean_data[field])
                    
                    db.add(user_details)
                    db.commit()
                    
                    successful_inserts.append({
                        'row': index + 1,
                        'user_id': new_user.id,
                        'action': 'created'
                    })
                
            except Exception as e:
                db.rollback()
                failed_inserts.append({
                    'row': index + 1,
                    'error': str(e)
                })
                logger.error(f"Error processing row {index + 1}: {str(e)}")
                continue
        
        # Prepare response
        response = {
            'message': 'CSV processing completed',
            'total_rows': len(df),
            'successful_inserts': len(successful_inserts),
            'updated_users': len(updated_users),
            'failed_inserts': len(failed_inserts),
            'details': {
                'created': successful_inserts,
                'updated': updated_users,
                'failed': failed_inserts
            }
        }
        
        if validation['warnings']:
            response['warnings'] = validation['warnings']
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )