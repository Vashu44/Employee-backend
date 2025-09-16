from fastapi import APIRouter, Form, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from model import usermodels
from db.database import get_db
from utils.mail_config_utils import send_mom_email, generate_pdf_from_html, get_complete_mom_data, generate_mom_html_from_db_data
import datetime

router = APIRouter(prefix="/mom")

@router.post("/send-mom-pdf-from-html/")
async def send_mom_pdf_from_html(
    usernames: str = Form(...),
    html_content: str = Form(...),
    mom_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Generate PDF from ViewDownloadMom HTML and send to multiple users"""
    try:
        print(f"📧 Processing email request for MOM: {mom_id}")
        print(f"📧 HTML content length: {len(html_content)} characters")
        
        username_list = [u.strip() for u in usernames.split(',') if u.strip()]
        if not username_list:
            raise HTTPException(status_code=400, detail="No valid usernames provided")
        
        print(f"📧 Sending to users: {username_list}")
        
        users = db.query(usermodels.User).filter(usermodels.User.username.in_(username_list)).all()
        if not users:
            raise HTTPException(status_code=404, detail="No users found")
        
        emails = [user.email for user in users if user.email]
        if not emails:
            raise HTTPException(status_code=404, detail="No valid emails found")
        
        print(f"📧 Email addresses: {emails}")
        
        pdf_bytes = generate_pdf_from_html(html_content)
        print(f"📧 PDF generated successfully: {len(pdf_bytes)} bytes")
        
        filename = f"MOM_{mom_id}_{datetime.date.today().strftime('%d-%m-%Y')}.pdf"
        send_mom_email(emails, pdf_bytes, filename)
        
        print(f"📧 Email sent successfully to {len(emails)} recipients")
        
        return {
            "message": f"PDF sent successfully to {len(emails)} recipients",
            "recipients": emails,
            "pdf_size": len(pdf_bytes),
            "filename": filename
        }
        
    except Exception as e:
        print(f"❌ Error in send_mom_pdf_from_html: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

# 🔧 Fix the endpoint path - remove the extra "/mom" prefix
@router.get("/{mom_id}/generate-and-send-pdf")
async def generate_and_send_pdf(
    mom_id: int,
    usernames: str = Query(..., description="Comma-separated usernames"),
    db: Session = Depends(get_db)
):
    """Database से MOM fetch करके PDF generate करें और email भेजें"""
    try:
        print(f"📧 Processing database PDF request for MOM: {mom_id}")
        
        # 1. Get complete MOM data from database
        mom_data = get_complete_mom_data(mom_id, db)
        if not mom_data:
            raise HTTPException(status_code=404, detail="MOM not found")
        
        print(f"📧 Retrieved MOM data: {mom_data['id']}")
        
        # 2. Generate HTML using same logic as ViewDownloadMom
        html_content = generate_mom_html_from_db_data(mom_data)
        print(f"📧 Generated HTML content: {len(html_content)} characters")
        
        # 3. Generate PDF
        pdf_bytes = generate_pdf_from_html(html_content)
        print(f"📧 Generated PDF: {len(pdf_bytes)} bytes")
        
        # 4. Send email
        username_list = [u.strip() for u in usernames.split(',') if u.strip()]
        users = db.query(usermodels.User).filter(usermodels.User.username.in_(username_list)).all()
        emails = [user.email for user in users if user.email]
        
        if not emails:
            raise HTTPException(status_code=404, detail="No valid emails found")
        
        filename = f"MOM_{mom_id}_{datetime.date.today().strftime('%d-%m-%Y')}.pdf"
        send_mom_email(emails, pdf_bytes, filename)
        
        print(f"📧 Email sent successfully to {len(emails)} recipients")
        
        return {
            "message": f"PDF sent successfully to {len(emails)} recipients",
            "recipients": emails,
            "mom_id": mom_id,
            "pdf_size": len(pdf_bytes),
            "filename": filename
        }
        
    except Exception as e:
        print(f"❌ Error in generate_and_send_pdf: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate and send PDF: {str(e)}")