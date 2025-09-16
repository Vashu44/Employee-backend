from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from model.timesheet_model import Timesheet
from Schema.timesheet_schema import TimesheetCreate, TimesheetOut
from db.database import get_db

router = APIRouter()

# Route to insert a new timesheet entry
@router.post("/timesheets/", response_model=TimesheetOut)
def create_timesheet(timesheet: TimesheetCreate, db: Session = Depends(get_db)):
    db_timesheet = Timesheet(**timesheet.dict())
    db.add(db_timesheet)
    db.commit()
    db.refresh(db_timesheet)
    return db_timesheet

@router.get("/timesheets/", response_model=list[TimesheetOut])
def get_timesheets(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Timesheet)
    if user_id:
        query = query.filter(Timesheet.user_id == user_id)
    return query.all()

@router.put("/timesheets/{id}", response_model=TimesheetOut)
def update_timesheet(id: int, timesheet: TimesheetCreate, db: Session = Depends(get_db)):
    db_timesheet = db.query(Timesheet).filter(Timesheet.id == id).first()
    if not db_timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")

    for key, value in timesheet.dict().items():
        setattr(db_timesheet, key, value)

    db.commit()
    db.refresh(db_timesheet)
    return db_timesheet

@router.delete("/timesheets/{id}", response_model=dict)
def delete_timesheet(id: int, db: Session = Depends(get_db)):
    timesheet = db.query(Timesheet).filter(Timesheet.id == id).first()
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    db.delete(timesheet)
    db.commit()
    return {"message": "Deleted successfully"}