from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import date
from math import ceil
from model.mom_model import MoM

from model.mom_model import MoMActionItem
from Schema.mom_action_items_schema import MoMActionItemCreate, MoMActionItemUpdate, MoMActionItemResponse, MoMActionItemListResponse,RemarkItem, ReassignedActionItemResponse, ReassignedActionItemListResponse

class MoMActionItemService:
    def __init__(self, db: Session):
        self.db = db

    def create_action_item(self, action_data: MoMActionItemCreate) -> MoMActionItemResponse:
        """Create a new MoM Action Item"""
        action_dict = action_data.model_dump()
        
        db_action = MoMActionItem(**action_dict)
        if db_action.remark is None:
            db_action.remark = []

        self.db.add(db_action)
        self.db.commit()
        self.db.refresh(db_action)
        
        return MoMActionItemResponse.model_validate(db_action)

    def get_action_item_by_id(self, action_id: int) -> Optional[MoMActionItemResponse]:
        """Get Action Item by ID"""
        db_action = self.db.query(MoMActionItem).filter(MoMActionItem.id == action_id).first()
        if db_action:
            if db_action.remark is None:
                db_action.remark = []
            return MoMActionItemResponse.model_validate(db_action)
        return None

    def get_action_items(
        self,
        skip: int = 0,
        limit: int = 10,
        mom_id: Optional[int] = None,
        assigned_to: Optional[int] = None,
        due_date: Optional[date] = None,
        updated_at: Optional[date] = None,
        remark: Optional[List[RemarkItem]] = None,
        re_assigned_to: Optional[str] = None
    ) -> MoMActionItemListResponse:
        """Get list of MoM Action Items with filters and pagination"""
        query = self.db.query(MoMActionItem)
        
        # Apply filters
        if mom_id:
            query = query.filter(MoMActionItem.mom_id == mom_id)
        if assigned_to:
            query = query.filter(MoMActionItem.assigned_to == assigned_to)
        if due_date:
            query = query.filter(MoMActionItem.due_date == due_date)
        if updated_at:
            query = query.filter(MoMActionItem.updated_at == updated_at)    
        if re_assigned_to:
            query = query.filter(MoMActionItem.re_assigned_to == re_assigned_to)
        # Get total count
        total = query.count()
        
        # Apply pagination and order
        db_actions = query.order_by(MoMActionItem.due_date.asc(), MoMActionItem.id.desc()).offset(skip).limit(limit).all()
        
        # Convert to response models
        action_items = []

        for action in db_actions:
            if action.remark is None:
                action.remark = []
            action_items.append(MoMActionItemResponse.model_validate(action))

        return MoMActionItemListResponse(
            action_items=action_items,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            total_pages=ceil(total / limit) if total > 0 else 0
        )

    def get_action_items_by_mom_id(self, mom_id: int) -> List[MoMActionItemResponse]:
        """Get all action items for a specific MoM"""
        db_actions = self.db.query(MoMActionItem).filter(MoMActionItem.mom_id == mom_id).order_by(MoMActionItem.due_date.asc()).all()
        
        # Ensure remark is not None for each action item
        action_items = []
        for action in db_actions:
            if action.remark is None:
                action.remark = []
            action_items.append(MoMActionItemResponse.model_validate(action))
        
        return action_items

    def get_action_items_by_assigned_username(self, username: str, sort_by: str = "due_date", order: str = "asc"):
        """Get action items by username with project name"""
        try:
            print(f"🔍 Getting action items for user: {username}")
            
            # Import MoM model
            from model.mom_model import MoM
            
             # 🆕 First, let's check direct query without join
            direct_query = self.db.query(MoMActionItem).filter(
                MoMActionItem.assigned_to == username
            ).all()
            
            print(f"🔍 Direct query found {len(direct_query)} action items")
            for item in direct_query:
                print(f"📋 Action item {item.id}: meeting_date = {item.meeting_date}, project = {item.project}")

            # Join query to get project name
            query = self.db.query(
                MoMActionItem.id,
                MoMActionItem.mom_id,
                MoMActionItem.action_item,
                MoMActionItem.assigned_to,
                MoMActionItem.due_date,
                MoMActionItem.status,
                MoMActionItem.remark,
                MoMActionItem.updated_at,
                MoMActionItem.re_assigned_to,
                MoMActionItem.meeting_date,
                MoMActionItem.project
            ).join(
                MoM, MoMActionItem.mom_id == MoM.id
            ).filter(
                MoMActionItem.assigned_to == username
            )
            
            # Apply sorting
            if sort_by == "due_date":
                if order == "desc":
                    query = query.order_by(MoMActionItem.due_date.desc())
                else:
                    query = query.order_by(MoMActionItem.due_date.asc())
            elif sort_by == "status":
                query = query.order_by(MoMActionItem.status)
            elif sort_by == "action_item":
                query = query.order_by(MoMActionItem.action_item)
                
            results = query.all()
            print(f"✅ Found {len(results)} action items with project names")
            
            # Convert to response format
            action_items = []
            for row in results:
                action_dict = {
                    "id": row.id,
                    "mom_id": row.mom_id,
                    "action_item": row.action_item,
                    "assigned_to": row.assigned_to,
                    "due_date": row.due_date,
                    "status": row.status,
                    "remark": row.remark,
                    "updated_at": row.updated_at,
                    "re_assigned_to": row.re_assigned_to,
                    "project": row.project,
                    "meeting_date": row.meeting_date
                }
                action_items.append(MoMActionItemResponse(**action_dict))
                
            return action_items
            
        except Exception as e:
            print(f"❌ Error getting action items: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_overdue_action_items(self) -> List[MoMActionItemResponse]:
        """Get all overdue action items"""
        today = date.today()
        db_actions = self.db.query(MoMActionItem).filter(MoMActionItem.due_date < today).order_by(MoMActionItem.due_date.asc()).all()

        action_items = []
        for action in db_actions:
                if action.remark is None:
                    action.remark = []
                action_items.append(MoMActionItemResponse.model_validate(action))

        return action_items

    def get_action_items_due_soon(self, days: int = 7) -> List[MoMActionItemResponse]:
        """Get action items due within specified number of days"""
        from datetime import timedelta
        today = date.today()
        target_date = today + timedelta(days=days)
        db_actions = self.db.query(MoMActionItem).filter(
            and_(MoMActionItem.due_date >= today, MoMActionItem.due_date <= target_date)
        ).order_by(MoMActionItem.due_date.asc()).all()

        action_items = []
        for action in db_actions:
            if action.remark is None:
                action.remark = []
            action_items.append(MoMActionItemResponse.model_validate(action))
        
        return action_items

    def update_action_item(self, action_id: int, action_data: MoMActionItemUpdate) -> Optional[MoMActionItemResponse]:
        """Update an existing MoM Action Item"""
        db_action = self.db.query(MoMActionItem).filter(MoMActionItem.id == action_id).first()
        if not db_action:
            return None
        
        if db_action.remark is None:
            db_action.remark = []

        # Update only provided fields
        update_dict = action_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            if field == 'remark' and value:
                # Handle remark list - append new remarks to existing list
                if db_action.remark is None:
                    db_action.remark = []
                
                # Extend the existing list with new remarks
                if isinstance(value, list):
                    db_action.remark.extend(value)
                else:
                    db_action.remark.append(value)
            else:
                setattr(db_action, field, value)
        
        # Always update the updated_at field when any change is made
        db_action.updated_at = date.today()
        self.db.commit()
        self.db.refresh(db_action)
        
        return MoMActionItemResponse.model_validate(db_action)

    def add_remark_to_action_item(self, action_id: int, remark_text: str, username: str) -> Optional[MoMActionItemResponse]:
        """Add a new remark to an existing action item"""
        try:
            print(f"🔍 Service: Looking for action item {action_id}")
            
            db_action = self.db.query(MoMActionItem).filter(MoMActionItem.id == action_id).first()
            if not db_action:
                print(f"❌ Action item {action_id} not found")
                return None
            
            print(f"✅ Found action item: {db_action.action_item}")
            print(f"📝 Current remark field: {db_action.remark} (type: {type(db_action.remark)})")
            
            # Initialize remark list if None
            if db_action.remark is None:
                db_action.remark = []
                print("🆕 Initialized empty remark list")
            
            # Make a copy of the current list (important for JSON columns)
            current_remarks = list(db_action.remark) if db_action.remark else []
            print(f"📋 Current remarks copy: {current_remarks}")

            # Create new remark object
            new_remark = {
                "text": remark_text,
                "by": username,
                "remark_date": date.today().isoformat()
            }
            print(f"🆕 New remark object: {new_remark}")

            # Append to the copied list
            current_remarks.append(new_remark)
            print(f"📝 Updated remarks list: {current_remarks}")

            # Append to existing remarks
            db_action.remark = current_remarks
            db_action.updated_at = date.today()
            
            print(f"📝 Updated remark field: {db_action.remark}")
            
            # Commit changes
            self.db.commit()
            print(f"💾 Committed to database")
            self.db.refresh(db_action)
            
            print(f"💾 Committed to database")
            print(f"📝 Final remark field: {db_action.remark}")
            
            # Convert to response model
            response = MoMActionItemResponse.model_validate(db_action)
            print(f"📤 Response remark: {response.remark}")
            
            return response
            
        except Exception as e:
            print(f"❌ Service error: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()
            return None

    def delete_action_item(self, action_id: int) -> bool:
        """Delete a MoM Action Item"""
        db_action = self.db.query(MoMActionItem).filter(MoMActionItem.id == action_id).first()
        if not db_action:
            return False
        
        self.db.delete(db_action)
        self.db.commit()
        return True

    def delete_action_items_by_mom_id(self, mom_id: int) -> int:
        """Delete all action items for a specific MoM"""
        count = self.db.query(MoMActionItem).filter(MoMActionItem.mom_id == mom_id).count()
        self.db.query(MoMActionItem).filter(MoMActionItem.mom_id == mom_id).delete()
        self.db.commit()
        return count
    # Add this method to your existing MoMActionItemService class in mom_action_item_service.py

    def get_action_items_by_reassigned_username(
        self, 
        username: str, 
        sort_by: str = "due_date", 
        order: str = "asc",
        skip: int = 0,
        limit: int = 100
    ) -> ReassignedActionItemListResponse:
        """Get action items by re_assigned_to username with detailed remark breakdown"""
        try:
            from collections import defaultdict
            from datetime import datetime
            from Schema.mom_action_items_schema import ReassignedActionItemResponse, ReassignedActionItemListResponse
            
            print(f"🔍 Getting reassigned action items for user: {username}")
            
            # Base query for action items reassigned to the user
            query = self.db.query(MoMActionItem).filter(
                MoMActionItem.re_assigned_to == username
            )
            
            # Get total count for pagination
            total = query.count()
            print(f"📊 Total reassigned action items found: {total}")
            
            # Apply sorting
            if sort_by == "due_date":
                if order == "desc":
                    query = query.order_by(MoMActionItem.due_date.desc())
                else:
                    query = query.order_by(MoMActionItem.due_date.asc())
            elif sort_by == "status":
                if order == "desc":
                    query = query.order_by(MoMActionItem.status.desc())
                else:
                    query = query.order_by(MoMActionItem.status.asc())
            elif sort_by == "updated_at":
                if order == "desc":
                    query = query.order_by(MoMActionItem.updated_at.desc())
                else:
                    query = query.order_by(MoMActionItem.updated_at.asc())
            elif sort_by == "meeting_date":
                if order == "desc":
                    query = query.order_by(MoMActionItem.meeting_date.desc())
                else:
                    query = query.order_by(MoMActionItem.meeting_date.asc())
            else:
                # Default sorting by due_date ascending
                query = query.order_by(MoMActionItem.due_date.asc())
            
            # Apply pagination
            db_actions = query.offset(skip).limit(limit).all()
            
            print(f"✅ Found {len(db_actions)} reassigned action items after pagination")
            
            # Process each action item with detailed remark breakdown
            action_items = []
            for action in db_actions:
                print(f"📋 Processing action item {action.id}: {action.action_item[:50]}...")
                
                # Initialize remark fields
                all_remarks = action.remark if action.remark else []
                remark_count = len(all_remarks)
                latest_remark = None
                remarks_by_user = defaultdict(list)
                
                # Process remarks if they exist
                if all_remarks:
                    # Find latest remark by date
                    try:
                        # Sort remarks by date to get the latest one
                        sorted_remarks = sorted(
                            all_remarks, 
                            key=lambda x: datetime.fromisoformat(x.get('remark_date', '1900-01-01')),
                            reverse=True
                        )
                        latest_remark = sorted_remarks[0] if sorted_remarks else None
                        
                        # Group remarks by user
                        for remark in all_remarks:
                            user = remark.get('by', 'Unknown')
                            remarks_by_user[user].append(remark)
                            
                    except Exception as remark_error:
                        print(f"⚠️ Error processing remarks for action {action.id}: {remark_error}")
                        latest_remark = all_remarks[-1] if all_remarks else None  # Fallback to last remark
                
                # Convert defaultdict to regular dict for JSON serialization
                remarks_by_user_dict = dict(remarks_by_user) if remarks_by_user else None
                
                # Create response object
                action_response = ReassignedActionItemResponse(
                    id=action.id,
                    mom_id=action.mom_id,
                    project=action.project,
                    action_item=action.action_item,
                    assigned_to=action.assigned_to,
                    re_assigned_to=action.re_assigned_to,
                    due_date=action.due_date,
                    status=action.status,
                    updated_at=action.updated_at,
                    meeting_date=action.meeting_date,
                    all_remarks=all_remarks,
                    remark_count=remark_count,
                    latest_remark=latest_remark,
                    remarks_by_user=remarks_by_user_dict
                )
                
                action_items.append(action_response)
                print(f"✅ Processed action item {action.id} with {remark_count} remarks")
            
            # Calculate pagination info
            total_pages = (total + limit - 1) // limit if total > 0 else 0
            current_page = (skip // limit) + 1
            
            return ReassignedActionItemListResponse(
                action_items=action_items,
                total=total,
                page=current_page,
                per_page=limit,
                total_pages=total_pages
            )
            
        except Exception as e:
            print(f"❌ Error getting reassigned action items: {e}")
            import traceback
            traceback.print_exc()
            return ReassignedActionItemListResponse(
                action_items=[],
                total=0,
                page=1,
                per_page=limit,
                total_pages=0
            )