from fastapi_mail import ConnectionConfig
from sqlalchemy.orm import Session
import os
import datetime
from dotenv import load_dotenv
from email.message import EmailMessage
import smtplib
import json
from xhtml2pdf import pisa
from io import BytesIO
from model.mom_model import MoM
from model.mom_model import MoMInformation 
from model.mom_model import MoMDecision 
from model.mom_model import MoMActionItem

load_dotenv()

# Simple direct approach - no Pydantic settings
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PORT = int(os.getenv("MAIL_PORT"))
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS").lower() == "true"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS").lower() == "true"


if not all([MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM]):
    raise ValueError("Email configuration is incomplete. Please check your .env file.")

conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_STARTTLS=MAIL_STARTTLS,
    MAIL_SSL_TLS=MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

def send_mom_email(emails, pdf_bytes, filename=None):
    if filename is None:
        filename = datetime.date.today().strftime("%d-%m-%Y") + ".pdf"
    
    msg = EmailMessage()
    msg['Subject'] = 'New MoM Created - PDF Attached'
    msg['From'] = MAIL_USERNAME
    msg['To'] = ', '.join(emails)
    
    # Better email content
    email_body = f"""
        Dear Team,
        
        A new Minutes of Meeting (MoM) has been created and is attached as a PDF.
        
        Please review the attached document for:
        • Meeting information and attendees
        • Key decisions made
        • Action items assigned
        • Important discussion points
        
        Thank you.
        
        Best regards,
        MoM System
    """
    
    msg.set_content(email_body)
    msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=filename)

    # Send the email
    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as smtp:
        smtp.starttls()
        smtp.login(MAIL_FROM, MAIL_PASSWORD)
        smtp.send_message(msg)

def generate_pdf_from_html(html_content):
    """
    Convert HTML to PDF using xhtml2pdf (simpler alternative)
    """
    try:
        print("🔄 Generating PDF using xhtml2pdf...")
        
        # Create BytesIO object to hold PDF data
        pdf_buffer = BytesIO()
        
        # Convert HTML to PDF
        pisa_status = pisa.CreatePDF(
            src=html_content,
            dest=pdf_buffer,
            encoding='utf-8'
        )
        
        if pisa_status.err:
            raise Exception("PDF generation failed with errors")
        
        # Get PDF bytes
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        print(f"✅ PDF generated successfully: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        print(f"❌ PDF generation error: {str(e)}")
        raise Exception(f"PDF generation failed: {str(e)}")
    

def parse_attendees(attendee_data):
        """Helper function to parse attendees"""
        if not attendee_data:
            return []
        
        if isinstance(attendee_data, list):
            return [item for item in attendee_data if item and str(item).strip()]
        
        if isinstance(attendee_data, str):
            return [name.strip() for name in attendee_data.split(',') if name.strip()]
        
        return []

def parse_remarks(remark_data):
    """Parse remarks data - can be JSON string, list, or None"""
    if not remark_data:
        return []
    
    if isinstance(remark_data, str):
        try:
            parsed = json.loads(remark_data)
            return parsed if isinstance(parsed, list) else []
        except:
            return []
    
    return remark_data if isinstance(remark_data, list) else []

def format_remark(remark):
    """Format a single remark for display"""
    if isinstance(remark, dict):
        return {
            'text': remark.get('remark_text', remark.get('text', 'No remark text')),
            'by': remark.get('remark_by', remark.get('by', 'Unknown')),
            'remark_date': remark.get('remark_date', remark.get('date', datetime.date.today().isoformat()))
        }
    elif isinstance(remark, str):
        return {
            'text': remark,
            'by': 'Unknown',
            'remark_date': datetime.date.today().isoformat()
        }
    else:
        return {
            'text': str(remark),
            'by': 'Unknown', 
            'remark_date': datetime.date.today().isoformat()
        }
    
def get_complete_mom_data(mom_id: int, db: Session):
        """
        Database से complete MOM data fetch करें
        """
        # Main MOM data
        mom = db.query(MoM).filter(MoM.id == mom_id).first()
        if not mom:
            return None
        
        # Information entries
        information = db.query(MoMInformation).filter(MoMInformation.mom_id == mom_id).all()

        # Decision entries
        decisions = db.query(MoMDecision).filter(MoMDecision.mom_id == mom_id).all()
        
        # Action items
        action_items = db.query(MoMActionItem).filter(MoMActionItem.mom_id == mom_id).all()

        # Format data same as ViewDownloadMom expects
        return {
            "id": mom.id,
            "meeting_date": str(mom.meeting_date),
            "start_time": mom.start_time,
            "end_time": mom.end_time,
            "project": mom.project,
            "meeting_type": mom.meeting_type,
            "location": mom.location_link,
            "attendees": mom.attendees,
            "absent": mom.absent,
            "other_attendees": mom.outer_attendees,
            "information": [info.information for info in information],
            "decisions": [dec.decision for dec in decisions],
            "actionItems": [
                {
                    "id": item.id,
                    "action_item": item.action_item,
                    "assigned_to": item.assigned_to,
                    "due_date": str(item.due_date) if item.due_date else None,
                    "status": item.status,
                    "project": item.project,
                    "meeting_date": str(item.meeting_date) if item.meeting_date else None,
                    "re_assigned_to": item.re_assigned_to,
                    "updated_at": str(item.updated_at) if item.updated_at else None,
                    "remark": []
                } for item in action_items
            ]
        }    

def generate_mom_html_from_db_data(mom_data):
        """
        ViewDownloadMom.js जैसा exact HTML generate करें
        """
        
            # Parse attendees
        present_attendees = parse_attendees(mom_data.get('attendees', ''))
        absent_attendees = parse_attendees(mom_data.get('absent', ''))

        # Generate Information section
        information_section = ""
        if mom_data.get('information'):
            info_items = []
            for info in mom_data['information']:
                info_items.append(f'<div class="content-item"><strong>• </strong>{info}</div>')
            
            information_section = f"""
            <div class="section">
                <h3 class="section-title">ℹ️ Information ({len(mom_data['information'])})</h3>
                {''.join(info_items)}
            </div>
            """
        
        # Generate Decisions section
        decisions_section = ""
        if mom_data.get('decisions'):
            decision_items = []
            for i, decision in enumerate(mom_data['decisions']):
                decision_items.append(f'<div class="content-item decision-item"><strong>{i+1}. </strong>{decision}</div>')
            
            decisions_section = f"""
            <div class="section">
                <h3 class="section-title">✅ Key Decisions ({len(mom_data['decisions'])})</h3>
                {''.join(decision_items)}
            </div>
            """
        
        # Generate Action Items section with remarks support
        action_items_section = ""
        if mom_data.get('actionItems'):
            action_items = []
            for item in mom_data['actionItems']:
                # Parse remarks for this action item
                remarks = parse_remarks(item.get('remark', item.get('remarks')))
                
                # Build action meta information
                action_meta_parts = []
                if item.get('assigned_to'):
                    action_meta_parts.append(f"👤 <strong>Assigned to:</strong> {item['assigned_to']}")
                if item.get('re_assigned_to'):
                    action_meta_parts.append(f"🔄 <strong>Re-assigned to:</strong> {item['re_assigned_to']}")
                if item.get('due_date'):
                    try:
                        due_date = datetime.datetime.fromisoformat(str(item['due_date'])).strftime('%d/%m/%Y')
                    except:
                        due_date = str(item['due_date'])
                    action_meta_parts.append(f"📅 <strong>Due:</strong> {due_date}")
                if item.get('meeting_date'):
                    try:
                        meeting_date = datetime.datetime.fromisoformat(str(item['meeting_date'])).strftime('%d/%m/%Y')
                    except:
                        meeting_date = str(item['meeting_date'])
                    action_meta_parts.append(f"🗓️ <strong>Meeting:</strong> {meeting_date}")
                if item.get('project'):
                    action_meta_parts.append(f"📁 <strong>Project:</strong> {item['project']}")
                
                action_meta = " | ".join(action_meta_parts)
                
                # Build status badge
                status_badge = ""
                if item.get('status'):
                    status_class = item['status'].lower().replace(' ', '-').replace('_', '-')
                    status_badge = f'<span class="status-badge status-{status_class}">{item["status"]}</span>'
                
                # Build remarks section
                remarks_html = ""
                if remarks:
                    remark_items = []
                    for idx, remark in enumerate(remarks):
                        formatted_remark = format_remark(remark)
                        try:
                            remark_date = datetime.datetime.fromisoformat(str(formatted_remark['remark_date'])).strftime('%d/%m/%Y')
                        except:
                            remark_date = str(formatted_remark['remark_date'])
                        
                        remark_items.append(f"""
                        <div class="remark-item">
                            <div style="margin-bottom: 8px;">
                                <p class="remark-text">
                                    <strong>{idx + 1}.</strong> {formatted_remark['text']}
                                </p>
                            </div>
                            <div class="remark-meta">
                                <span>👤 <strong>By:</strong> {formatted_remark['by']}</span>
                                <span>📅 <strong>Date:</strong> {remark_date}</span>
                            </div>
                        </div>
                        """)
                    
                    remarks_html = f"""
                    <div class="remarks-section">
                        <div class="remarks-header">💬 REMARKS ({len(remarks)})</div>
                        {''.join(remark_items)}
                    </div>
                    """
                else:
                    remarks_html = """
                    <div class="no-remarks">
                        <p>💬 No remarks added</p>
                    </div>
                    """
                
                # Build timestamps
                timestamps = []
                if item.get('created_at'):
                    try:
                        created_date = datetime.datetime.fromisoformat(str(item['created_at'])).strftime('%d/%m/%Y')
                        timestamps.append(f"📅 <strong>Created:</strong> {created_date}")
                    except:
                        pass
                if item.get('updated_at'):
                    try:
                        updated_date = datetime.datetime.fromisoformat(str(item['updated_at'])).strftime('%d/%m/%Y')
                        timestamps.append(f"🔄 <strong>Updated:</strong> {updated_date}")
                    except:
                        pass
                
                timestamps_html = ""
                if timestamps:
                    timestamps_html = f"""
                    <div style="font-size: 11px; color: #666; margin-top: 15px; padding-top: 12px; border-top: 1px solid #eee;">
                        {" | ".join(timestamps)}
                    </div>
                    """
                
                action_items.append(f"""
                <div class="content-item action-item">
                    <div style="margin-bottom: 15px;">
                        <strong style="font-size: 14px; color: #2c3e50;">
                            {item.get('action_item', item.get('description', item.get('text', item.get('content', str(item) if isinstance(item, str) else 'No action text'))))}
                        </strong>
                        {status_badge}
                    </div>
                    
                    <div class="action-meta" style="margin-bottom: 15px;">
                        {action_meta}
                    </div>
                    
                    {remarks_html}
                    {timestamps_html}
                </div>
                """)
            
            action_items_section = f"""
            <div class="section">
                <h3 class="section-title">🎯 Action Items ({len(mom_data['actionItems'])})</h3>
                {''.join(action_items)}
            </div>
            """
        
        # Generate other attendees section if exists
        other_attendees_html = ""
        if mom_data.get('other_attendees'):
            other_attendees_html = f"""
            <div class="info-item" style="grid-column: 1 / -1;">
                <span class="info-label">📧 Other Attendees:</span>
                <span class="info-value">{mom_data['other_attendees']}</span>
            </div>
            """
        
        # Complete HTML with enhanced styling
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>MOM_{mom_data['id']}_{mom_data['meeting_date']}</title>
            <style>
                * {{
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }}
                
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    line-height: 1.6;
                    color: #2c3e50;
                    background-color: #ffffff;
                    font-size: 12px;
                }}
                
                .container {{
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                }}
                
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #3498db;
                    padding: 20px 0;
                    margin-bottom: 25px;
                    background: #f8f9fa;
                    border-radius: 6px;
                }}
                
                .header h1 {{
                    color: #2c3e50;
                    font-size: 24px;
                    margin-bottom: 8px;
                    font-weight: 600;
                }}
                
                .header h2 {{
                    color: #3498db;
                    font-size: 16px;
                    font-weight: 500;
                }}
                
                .section {{
                    margin-bottom: 20px;
                    page-break-inside: auto;
                    break-inside: auto;
                }}
                
                .section-title {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #2c3e50;
                    border-bottom: 1px solid #e9ecef;
                    padding-bottom: 8px;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    page-break-after: avoid;
                    break-after: avoid;
                }}
                
                .info-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 12px;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 6px;
                    border: 1px solid #e9ecef;
                    margin-bottom: 15px;
                }}
                
                .info-item {{
                    display: flex;
                    align-items: flex-start;
                    gap: 8px;
                    padding: 6px 0;
                    font-size: 15px;
                    color: #1f2937;
                }}
                
                .info-label {{
                    font-weight: 600;
                    color: #1f2937;
                    min-width: 120px;
                    flex-shrink: 0;
                }}
                
                .info-value {{
                    color: #1f2937;
                    flex: 1;
                }}
                
                .attendee-section {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin-bottom: 15px;
                }}
                
                .attendee-column {{
                    background: #f8f9fa;
                    padding: 12px;
                    border-radius: 6px;
                    border: 1px solid #e9ecef;
                }}
                
                .attendee-column h4 {{
                    margin-bottom: 10px;
                    font-size: 13px;
                    font-weight: 600;
                    padding-bottom: 6px;
                    border-bottom: 1px solid #dee2e6;
                }}
                
                .attendee-column.present h4 {{
                    color: #28a745;
                }}
                
                .attendee-column.absent h4 {{
                    color: #dc3545;
                }}
                
                .attendee-list {{
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }}
                
                .attendee-list li {{
                    padding: 3px 0;
                    color: #1f2937;
                    font-size: 15px;
                    border-bottom: 1px dotted #dee2e6;
                }}
                
                .attendee-list li:last-child {{
                    border-bottom: none;
                }}
                
                .content-item {{
                    background-color: #ffffff;
                    padding: 12px;
                    margin-bottom: 10px;
                    border-left: 4px solid #3498db;
                    border-radius: 6px;
                    border: 1px solid #e9ecef;
                    page-break-inside: auto;
                    break-inside: auto;
                    orphans: 2;
                    widows: 2;
                }}
                
                .decision-item {{
                    border-left-color: #28a745;
                }}
                
                .action-item {{
                    border-left-color: #fd7e14;
                    padding: 10px;
                    margin-bottom: 8px;
                }}
                
                .action-meta {{
                    margin-top: 8px;
                    padding-top: 8px;
                    border-top: 1px solid #e9ecef;
                    font-size: 15px;
                    color: #1f2937;
                    line-height: 1.4;
                }}
                
                .remarks-section {{
                    background-color: #f8f9fa;
                    padding: 12px;
                    margin: 12px 0;
                    border-left: 4px solid #17a2b8;
                    border-radius: 6px;
                    font-size: 12px;
                    page-break-inside: auto;
                    break-inside: auto;
                }}
                
                .remarks-header {{
                    color: #0c5460;
                    font-size: 13px;
                    font-weight: 700;
                    margin-bottom: 10px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                
                .remark-item {{
                    background-color: #ffffff;
                    padding: 12px;
                    margin: 8px 0;
                    border-radius: 6px;
                    border: 1px solid #dee2e6;
                    font-size: 12px;
                    page-break-inside: auto;
                    break-inside: auto;
                }}
                
                .remark-text {{
                    color: #1a202c !important;
                    font-size: 13px !important;
                    line-height: 1.5;
                    margin: 0 0 8px 0;
                    font-weight: 500;
                }}
                
                .remark-meta {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding-top: 6px;
                    border-top: 1px solid #f1f3f5;
                    font-size: 11px !important;
                    color: #2d3748 !important;
                    font-weight: 500;
                }}
                
                .no-remarks {{
                    background-color: #f8f9fa;
                    padding: 8px;
                    margin: 8px 0;
                    border-left: 3px solid #6c757d;
                    border-radius: 3px;
                    color: #6c757d;
                    font-size: 10px;
                    font-style: italic;
                }}
                
                .status-badge {{
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 9px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.3px;
                    margin-left: 8px;
                }}
                
                .status-completed {{ 
                    background-color: #d4edda; 
                    color: #155724; 
                }}
                
                .status-in-progress,
                .status-progress {{ 
                    background-color: #cce7ff; 
                    color: #004085; 
                }}
                
                .status-pending {{ 
                    background-color: #fff3cd; 
                    color: #856404; 
                }}
                
                .status-cancelled {{ 
                    background-color: #f8d7da; 
                    color: #721c24; 
                }}
                
                .footer {{
                    margin-top: 30px;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 6px;
                    text-align: center;
                    font-size: 10px;
                    color: #6c757d;
                    border: 1px solid #e9ecef;
                    page-break-inside: avoid;
                    break-inside: avoid;
                }}
                
                @media print {{
                    body {{ 
                        padding: 10px; 
                        background: white; 
                        font-size: 15px !important;
                        line-height: 1.4;
                        color: #1f2937 !important;
                    }}
                    
                    .container {{ 
                        box-shadow: none; 
                        padding: 0;
                        max-width: none;
                    }}
                    
                    .header {{ 
                        background: none; 
                        border-bottom: 2px solid #333;
                        margin-bottom: 20px;
                    }}
                    
                    .info-grid {{ 
                        background: none; 
                        border: 1px solid #ccc;
                        page-break-inside: avoid;
                    }}
                    
                    .attendee-column {{ 
                        background: none; 
                        border: 1px solid #ccc;
                    }}
                    
                    .content-item {{ 
                        box-shadow: none; 
                        border: 1px solid #ccc;
                        page-break-inside: auto;
                        orphans: 3;
                        widows: 3;
                    }}
                    
                    .footer {{ 
                        background: none; 
                        border: 1px solid #ccc; 
                    }}
                    
                    .remarks-section {{
                        background-color: #f9f9f9 !important;
                        border-left: 3px solid #666 !important;
                        -webkit-print-color-adjust: exact;
                        print-color-adjust: exact;
                    }}
                    
                    .remark-item {{
                        background-color: #ffffff !important;
                        border: 1px solid #999 !important;
                    }}
                    
                    .action-meta {{
                        background-color: transparent !important;
                        border-top: 1px solid #ccc !important;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Minutes of Meeting (MOM)</h1>
                    <h2>MOM ID: #{mom_data['id']}</h2>
                </div>
                
                <div class="section">
                    <h3 class="section-title">📋 General Information</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <span class="info-label">📅 Date:</span>
                            <span class="info-value">{mom_data['meeting_date']}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">⏰ Time:</span>
                            <span class="info-value">{mom_data['start_time']} - {mom_data['end_time']}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">🎯 Project:</span>
                            <span class="info-value">{mom_data['project']}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">📞 Meeting Type:</span>
                            <span class="info-value">{mom_data.get('meeting_type', 'Not specified')}</span>
                        </div>
                        <div class="info-item" style="grid-column: 1 / -1;">
                            <span class="info-label">📍 Venue/Platform:</span>
                            <span class="info-value">{mom_data.get('location', mom_data.get('location_link', 'Not specified'))}</span>
                        </div>
                        {other_attendees_html}
                    </div>
                </div>

                <div class="section">
                    <h3 class="section-title">👥 Attendees</h3>
                    <div class="attendee-section">
                        <div class="attendee-column present">
                            <h4>✅ Present ({len(present_attendees)})</h4>
                            <ul class="attendee-list">
                                {(''.join([f'<li>• {attendee}</li>' for attendee in present_attendees]) if present_attendees else '<li>No attendees listed</li>')}
                            </ul>
                        </div>
                        <div class="attendee-column absent">
                            <h4>❌ Absent ({len(absent_attendees)})</h4>
                            <ul class="attendee-list">
                                {(''.join([f'<li>• {attendee}</li>' for attendee in absent_attendees]) if absent_attendees else '<li>No absentees listed</li>')}
                            </ul>
                        </div>
                    </div>
                </div>

                {information_section}
                {decisions_section}
                {action_items_section}
                
                <div class="footer">
                    <p><strong>MOM ID:</strong> #{mom_data['id']} | <strong>Generated on:</strong> {datetime.date.today().strftime('%d/%m/%Y')}</p>
                    <p>This document was automatically generated from the MOM system.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content

