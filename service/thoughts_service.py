from sqlalchemy.orm import Session
from sqlalchemy import func
from model.thoughts_model import Thought
from Schema.thoughts_schema import ThoughtCreate, ThoughtUpdate
from typing import List, Optional
import pandas as pd
import io

class ThoughtService:
    def create_thought(db: Session, thought: ThoughtCreate) -> Thought:
        db_thought = Thought(
            thoughts=thought.thoughts,
            author=thought.author,
            created_by=thought.created_by
        )
        db.add(db_thought)
        db.commit()
        db.refresh(db_thought)
        return db_thought

    def bulk_create_thoughts(db: Session, csv_content: bytes, created_by: int) -> dict:
        """
        Bulk create thoughts from CSV file
        CSV should have columns: thoughts, author
        """
        try:
            # Read CSV content
            csv_string = csv_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_string))
            
            # Validate required columns
            required_columns = ['thoughts', 'author']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    "success": False,
                    "message": f"Missing required columns: {missing_columns}",
                    "created_count": 0
                }
            
            # Remove empty rows
            df = df.dropna(subset=required_columns)
            
            created_thoughts = []
            failed_rows = []
            
            for index, row in df.iterrows():
                try:
                    db_thought = Thought(
                        thoughts=str(row['thoughts']).strip(),
                        author=str(row['author']).strip(),
                        created_by=created_by
                    )
                    db.add(db_thought)
                    created_thoughts.append(db_thought)
                except Exception as e:
                    failed_rows.append({"row": index + 1, "error": str(e)})
            
            # Commit all at once
            db.commit()
            
            return {
                "success": True,
                "message": f"Successfully created {len(created_thoughts)} thoughts",
                "created_count": len(created_thoughts),
                "failed_count": len(failed_rows),
                "failed_rows": failed_rows
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error processing CSV: {str(e)}",
                "created_count": 0
            }
    
    def get_random_thought(db: Session) -> Optional[Thought]:
        """Get a random thought from the database"""
        return db.query(Thought).order_by(func.random()).first()
    
    def get_thought(db: Session, thought_id: int) -> Optional[Thought]:
        return db.query(Thought).filter(Thought.id == thought_id).first()
    
    
    def get_all_thoughts(db: Session, skip: int = 0, limit: int = 100) -> List[Thought]:
        return db.query(Thought).offset(skip).limit(limit).all()
    
    
    def get_thoughts_by_author(db: Session, author: str) -> List[Thought]:
        return db.query(Thought).filter(Thought.author == author).all()
    
    
    def update_thought(db: Session, thought_id: int, thought_update: ThoughtUpdate) -> Optional[Thought]:
        db_thought = db.query(Thought).filter(Thought.id == thought_id).first()
        if db_thought:
            update_data = thought_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_thought, field, value)
            db.commit()
            db.refresh(db_thought)
        return db_thought
    

    def delete_thought(db: Session, thought_id: int) -> bool:
        db_thought = db.query(Thought).filter(Thought.id == thought_id).first()
        if db_thought:
            db.delete(db_thought)
            db.commit()
            return True
        return False
