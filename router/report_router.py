from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime, date
import json
import os
from fastapi.responses import FileResponse

# Optional imports with fallbacks
HAS_ADVANCED_FEATURES = True
try:
    import pandas as pd
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.units import inch
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns
    import io
    import base64
    from dateutil.relativedelta import relativedelta
except ImportError as e:
    print(f"Advanced features disabled due to missing dependencies: {e}")
    HAS_ADVANCED_FEATURES = False

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from db.database import get_db
from model.usermodels import User

# Try to import report models, create fallback if not available
try:
    from model.report_model import ReportTemplate, GeneratedReport, EmailLog
    HAS_REPORT_MODELS = True
except ImportError:
    print("Report models not found. Using raw SQL queries.")
    HAS_REPORT_MODELS = False

router = APIRouter(
    prefix="/api/reports",
    tags=["reports"]
)

# Pydantic Models for API
class ReportTemplateCreate(BaseModel):
    template_name: str
    template_type: str  # "employee", "expense", "timesheet", "asset", "appreciation", "mom"
    report_format: str  # "monthly", "yearly", "custom"
    template_config: Dict[str, Any]  # JSON config for template structure
    include_charts: bool = True
    chart_types: List[str] = []  # ["bar", "line", "pie", "table"]
    office_template_links: Dict[str, str] = {}  # Links to Word, Excel, PowerPoint templates
    created_by: int

class ReportTemplateResponse(BaseModel):
    id: int
    template_name: str
    template_type: str
    report_format: str
    template_config: Dict[str, Any]
    include_charts: bool
    chart_types: List[str]
    office_template_links: Dict[str, str]
    created_by: int
    created_at: datetime
    updated_at: datetime

class ReportGenerationRequest(BaseModel):
    template_id: int
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    employee_ids: Optional[List[int]] = []
    department: Optional[str] = None
    additional_filters: Dict[str, Any] = {}

class EmailReportRequest(BaseModel):
    report_id: int
    recipient_email: EmailStr
    subject: str
    message: str
    sender_email: EmailStr

class ReportResponse(BaseModel):
    id: int
    template_id: int
    template_name: str
    report_type: str
    generated_data: Dict[str, Any]
    charts_data: Dict[str, str]  # Base64 encoded chart images
    pdf_path: Optional[str] = None
    generated_by: int
    generated_at: datetime

# Helper Functions
def table_exists(db: Session, table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        result = db.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
        return result.fetchone() is not None
    except:
        return False

def execute_flexible_query(db: Session, query_config: Dict[str, Any], filters: Dict[str, Any] = {}):
    """Execute flexible database queries with table validation and better error handling"""
    try:
        # Check available tables
        available_tables = {
            "users": table_exists(db, "users"),
            "timesheets": table_exists(db, "timesheets"),
            "leave_requests": table_exists(db, "leave_requests"),
            "expense_claims": table_exists(db, "expense_claims")
        }
        
        print(f"Available tables: {available_tables}")
        
        # Build query based on available tables
        if available_tables["users"]:
            if available_tables["timesheets"] and available_tables["leave_requests"] and available_tables["expense_claims"]:
                # Full query with all tables
                safe_query = """
                SELECT 
                    u.id, 
                    u.username, 
                    u.email, 
                    u.role,
                    COALESCE(t.total_hours, 0) as total_hours,
                    COALESCE(t.days_present, 0) as days_present,
                    COALESCE(l.leave_days, 0) as leave_days,
                    COALESCE(e.expense_amount, 0) as expense_amount
                FROM users u
                LEFT JOIN (
                    SELECT user_id, SUM(hours_worked) as total_hours, COUNT(DISTINCT date) as days_present 
                    FROM timesheets GROUP BY user_id
                ) t ON u.id = t.user_id
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as leave_days 
                    FROM leave_requests WHERE status = 'approved' GROUP BY user_id
                ) l ON u.id = l.user_id
                LEFT JOIN (
                    SELECT user_id, SUM(amount) as expense_amount 
                    FROM expense_claims WHERE status = 'approved' GROUP BY user_id
                ) e ON u.id = e.user_id
                WHERE 1=1
                """
            else:
                # Simplified query for missing tables
                safe_query = """
                SELECT 
                    u.id, 
                    u.username, 
                    u.email, 
                    u.role,
                    0 as total_hours,
                    0 as days_present,
                    0 as leave_days,
                    0 as expense_amount
                FROM users u
                WHERE 1=1
                """
        else:
            raise HTTPException(status_code=500, detail="Users table not found")
        
        # Build conditions for WHERE clause
        conditions = []
        params = {}
        
        if filters.get("date_from") and filters.get("date_to"):
            date_field = query_config.get("date_field", "u.created_at")
            conditions.append(f"{date_field} BETWEEN :date_from AND :date_to")
            params["date_from"] = filters["date_from"]
            params["date_to"] = filters["date_to"]
        
        if filters.get("employee_ids"):
            employee_list = ",".join(map(str, filters["employee_ids"]))
            conditions.append(f"u.id IN ({employee_list})")
        
        if filters.get("department"):
            conditions.append("u.role = :department")
            params["department"] = filters["department"]
        
        # Handle additional filters
        additional_filters = filters.get("additional_filters", {})
        if additional_filters.get("role"):
            conditions.append("u.role = :role_filter")
            params["role_filter"] = additional_filters["role"]
        
        if additional_filters.get("status") and additional_filters["status"] == "active":
            conditions.append("u.is_verified = 1")
        
        # Add conditions to query
        if conditions:
            safe_query += " AND " + " AND ".join(conditions)
        
        safe_query += query_config.get("order_by", " ORDER BY u.username")
        safe_query += query_config.get("limit", " LIMIT 100")
        
        print(f"Executing query: {safe_query}")
        print(f"With parameters: {params}")
        
        result = db.execute(text(safe_query), params)
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in result.fetchall()]
        
        return {"data": data, "columns": list(columns)}
    
    except Exception as e:
        print(f"Query execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")

def generate_charts(data: List[Dict], chart_configs: List[Dict]) -> Dict[str, str]:
    """Generate charts based on data and configuration (if matplotlib available)"""
    charts = {}
    
    if not HAS_ADVANCED_FEATURES:
        print("Charts disabled - matplotlib not available")
        return charts
    
    try:
        if not data:
            return charts
            
        df = pd.DataFrame(data)
        
        for config in chart_configs:
            chart_type = config.get("type", "bar")
            title = config.get("title", "Chart")
            x_field = config.get("x_field")
            y_field = config.get("y_field")
            
            if x_field not in df.columns or y_field not in df.columns:
                continue
            
            plt.figure(figsize=(10, 6))
            
            if chart_type == "bar":
                plt.bar(df[x_field], df[y_field])
                plt.xlabel(x_field.replace('_', ' ').title())
                plt.ylabel(y_field.replace('_', ' ').title())
            elif chart_type == "line":
                plt.plot(df[x_field], df[y_field], marker='o')
                plt.xlabel(x_field.replace('_', ' ').title())
                plt.ylabel(y_field.replace('_', ' ').title())
            elif chart_type == "pie":
                plt.pie(df[y_field], labels=df[x_field], autopct='%1.1f%%')
            
            plt.title(title)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save chart as base64 string
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()
            
            charts[config.get("name", f"chart_{len(charts)}")] = chart_base64
    
    except Exception as e:
        print(f"Chart generation error: {str(e)}")
    
    return charts

def generate_pdf_report(report_data: Dict[str, Any], charts: Dict[str, str], template_config: Dict[str, Any]) -> str:
    """Generate PDF report (if reportlab available, otherwise HTML)"""
    if not HAS_ADVANCED_FEATURES:
        return generate_simple_html_report(report_data, template_config)
    
    try:
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = f"reports/{filename}"
        
        os.makedirs("reports", exist_ok=True)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph(template_config.get("title", "HR Report"), styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Report Info
        info_data = [
            ["Report Type:", template_config.get("report_type", "")],
            ["Generated On:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Date Range:", f"{report_data.get('date_from', '')} to {report_data.get('date_to', '')}"]
        ]
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 12))
        
        # Data Table
        if report_data.get("data"):
            data = report_data["data"]
            if data:
                headers = list(data[0].keys())
                table_data = [headers]
                
                for row in data[:50]:  # Limit to first 50 rows
                    table_data.append([str(row.get(col, "")) for col in headers])
                
                data_table = Table(table_data)
                data_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                story.append(data_table)
                story.append(PageBreak())
        
        # Add Charts section
        if charts:
            story.append(Paragraph("Charts and Visualizations", styles['Heading2']))
            for chart_name, chart_data in charts.items():
                story.append(Paragraph(f"Chart: {chart_name.replace('_', ' ').title()}", styles['Heading3']))
                story.append(Paragraph("Chart visualization embedded", styles['Normal']))
                story.append(Spacer(1, 12))
        
        doc.build(story)
        return filepath
    
    except Exception as e:
        print(f"PDF generation failed, falling back to HTML: {str(e)}")
        return generate_simple_html_report(report_data, template_config)

def generate_simple_html_report(report_data: Dict[str, Any], template_config: Dict[str, Any]) -> str:
    """Generate simple HTML report"""
    try:
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = f"reports/{filename}"
        
        os.makedirs("reports", exist_ok=True)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{template_config.get('title', 'HR Report')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; margin-bottom: 30px; border-radius: 8px; }}
                .header h1 {{ margin: 0; font-size: 28px; }}
                .info-section {{ background-color: #f8f9ff; padding: 20px; margin-bottom: 20px; border-radius: 6px; border-left: 4px solid #667eea; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                .data-table th, .data-table td {{ border: 1px solid #ddd; padding: 12px 8px; text-align: left; }}
                .data-table th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: bold; }}
                .data-table tr:nth-child(even) {{ background-color: #f9f9ff; }}
                .data-table tr:hover {{ background-color: #e8eaff; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-box {{ background-color: #f0f2ff; padding: 20px; border-radius: 8px; text-align: center; min-width: 120px; }}
                .stat-number {{ font-size: 24px; font-weight: bold; color: #667eea; }}
                .stat-label {{ color: #666; margin-top: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{template_config.get('title', 'HR Report')}</h1>
                    <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <div class="info-section">
                    <h3>Report Information</h3>
                    <p><strong>Report Type:</strong> {template_config.get('report_type', 'Employee Report')}</p>
                    <p><strong>Description:</strong> {template_config.get('description', 'Comprehensive employee data analysis')}</p>
                </div>
        """
        
        if report_data.get("data"):
            data = report_data["data"]
            if data:
                # Add statistics
                html_content += f"""
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-number">{len(data)}</div>
                        <div class="stat-label">Total Records</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{sum(row.get('total_hours', 0) for row in data)}</div>
                        <div class="stat-label">Total Hours</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{sum(row.get('expense_amount', 0) for row in data)}</div>
                        <div class="stat-label">Total Expenses</div>
                    </div>
                </div>
                """
                
                html_content += '<h2>Detailed Data</h2>'
                html_content += '<table class="data-table">'
                
                headers = list(data[0].keys())
                html_content += '<tr>'
                for header in headers:
                    html_content += f'<th>{header.replace("_", " ").title()}</th>'
                html_content += '</tr>'
                
                for row in data:
                    html_content += '<tr>'
                    for header in headers:
                        value = str(row.get(header, ""))
                        html_content += f'<td>{value}</td>'
                    html_content += '</tr>'
                
                html_content += '</table>'
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HTML report generation error: {str(e)}")

def generate_csv_report(report_data: Dict[str, Any], template_config: Dict[str, Any]) -> str:
    """Generate CSV report"""
    try:
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = f"reports/{filename}"
        
        os.makedirs("reports", exist_ok=True)
        
        if report_data.get("data"):
            data = report_data["data"]
            if data:
                import csv
                
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    headers = list(data[0].keys())
                    writer = csv.DictWriter(csvfile, fieldnames=headers)
                    
                    writer.writeheader()
                    for row in data:
                        writer.writerow(row)
        
        return filepath
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV report generation error: {str(e)}")

async def send_email_with_attachment(email_data: EmailReportRequest, file_path: str):
    """Send email with file attachment"""
    try:
        msg = MIMEMultipart()
        msg['From'] = email_data.sender_email
        msg['To'] = email_data.recipient_email
        msg['Subject'] = email_data.subject
        
        msg.attach(MIMEText(email_data.message, 'plain'))
        
        if os.path.exists(file_path):
            with open(file_path, "rb") as attachment:
                part = MIMEApplication(attachment.read(), Name=os.path.basename(file_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                msg.attach(part)
        
        return {"message": "Email prepared successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email preparation error: {str(e)}")

# API Endpoints
@router.post("/templates", response_model=ReportTemplateResponse)
async def create_report_template(template: ReportTemplateCreate, db: Session = Depends(get_db)):
    """Create a new report template"""
    try:
        # Create table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS report_templates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            template_name VARCHAR(200) NOT NULL,
            template_type VARCHAR(50) NOT NULL,
            report_format VARCHAR(20) NOT NULL,
            template_config JSON NOT NULL,
            include_charts BOOLEAN DEFAULT TRUE,
            chart_types JSON DEFAULT (JSON_ARRAY()),
            office_template_links JSON DEFAULT (JSON_OBJECT()),
            created_by INT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        db.execute(text(create_table_query))
        
        # Insert template
        query = text("""
            INSERT INTO report_templates 
            (template_name, template_type, report_format, template_config, 
             include_charts, chart_types, office_template_links, created_by, 
             created_at, updated_at)
            VALUES 
            (:template_name, :template_type, :report_format, :template_config,
             :include_charts, :chart_types, :office_template_links, :created_by,
             :created_at, :updated_at)
        """)
        
        result = db.execute(query, {
            "template_name": template.template_name,
            "template_type": template.template_type,
            "report_format": template.report_format,
            "template_config": json.dumps(template.template_config),
            "include_charts": template.include_charts,
            "chart_types": json.dumps(template.chart_types),
            "office_template_links": json.dumps(template.office_template_links),
            "created_by": template.created_by,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        db.commit()
        template_id = result.lastrowid
        
        return ReportTemplateResponse(
            id=template_id,
            template_name=template.template_name,
            template_type=template.template_type,
            report_format=template.report_format,
            template_config=template.template_config,
            include_charts=template.include_charts,
            chart_types=template.chart_types,
            office_template_links=template.office_template_links,
            created_by=template.created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating template: {str(e)}")

@router.get("/templates", response_model=List[ReportTemplateResponse])
async def get_all_templates(db: Session = Depends(get_db)):
    """Get all report templates"""
    try:
        query = text("SELECT * FROM report_templates ORDER BY created_at DESC")
        result = db.execute(query)
        templates = []
        
        for row in result:
            templates.append(ReportTemplateResponse(
                id=row.id,
                template_name=row.template_name,
                template_type=row.template_type,
                report_format=row.report_format,
                template_config=json.loads(row.template_config) if isinstance(row.template_config, str) else row.template_config,
                include_charts=row.include_charts,
                chart_types=json.loads(row.chart_types) if isinstance(row.chart_types, str) else row.chart_types,
                office_template_links=json.loads(row.office_template_links) if isinstance(row.office_template_links, str) else row.office_template_links,
                created_by=row.created_by,
                created_at=row.created_at,
                updated_at=row.updated_at
            ))
        
        return templates
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching templates: {str(e)}")

@router.get("/templates/{template_id}", response_model=ReportTemplateResponse)
async def get_template_by_id(template_id: int, db: Session = Depends(get_db)):
    """Get a specific report template"""
    try:
        query = text("SELECT * FROM report_templates WHERE id = :template_id")
        result = db.execute(query, {"template_id": template_id})
        template = result.fetchone()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return ReportTemplateResponse(
            id=template.id,
            template_name=template.template_name,
            template_type=template.template_type,
            report_format=template.report_format,
            template_config=json.loads(template.template_config) if isinstance(template.template_config, str) else template.template_config,
            include_charts=template.include_charts,
            chart_types=json.loads(template.chart_types) if isinstance(template.chart_types, str) else template.chart_types,
            office_template_links=json.loads(template.office_template_links) if isinstance(template.office_template_links, str) else template.office_template_links,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching template: {str(e)}")

@router.post("/generate")
async def generate_report(request: ReportGenerationRequest, user_id: int, db: Session = Depends(get_db)):
    """Generate a report based on template and parameters"""
    try:
        print(f"Generating report with template_id: {request.template_id}")
        
        # Try to get template from database, use default if not found
        try:
            query = text("SELECT * FROM report_templates WHERE id = :template_id")
            result = db.execute(query, {"template_id": request.template_id})
            template = result.fetchone()
            
            if template:
                template_config = json.loads(template.template_config) if isinstance(template.template_config, str) else template.template_config
                template_name = template.template_name
                template_type = template.template_type
            else:
                raise Exception("Template not found")
        except:
            # Use default template config
            template_config = {
                "title": "Employee Report",
                "description": "Basic employee data report",
                "date_field": "u.created_at",
                "employee_field": "u.id",
                "order_by": " ORDER BY u.username",
                "limit": " LIMIT 100"
            }
            template_name = "Default Employee Report"
            template_type = "employee"
        
        # Prepare filters
        filters = {
            "date_from": request.date_from,
            "date_to": request.date_to,
            "employee_ids": request.employee_ids,
            "department": request.department,
            "additional_filters": request.additional_filters
        }
        
        print(f"Filters: {filters}")
        
        # Execute query
        query_result = execute_flexible_query(db, template_config, filters)
        
        print(f"Query result: {len(query_result['data'])} records found")
        
        # Generate charts if enabled and advanced features available
        charts = {}
        if HAS_ADVANCED_FEATURES and template_config.get("charts"):
            charts = generate_charts(query_result["data"], template_config.get("charts", []))
        
        # Generate reports
        html_path = generate_simple_html_report(query_result, template_config)
        csv_path = generate_csv_report(query_result, template_config)
        
        if HAS_ADVANCED_FEATURES:
            pdf_path = generate_pdf_report(query_result, charts, template_config)
        else:
            pdf_path = html_path
        
        # Try to save generated report to database
        try:
            # Create table if it doesn't exist
            create_table_query = """
            CREATE TABLE IF NOT EXISTS generated_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                template_id INT NOT NULL,
                template_name VARCHAR(200) NOT NULL,
                report_type VARCHAR(50) NOT NULL,
                generated_data JSON NOT NULL,
                charts_data JSON DEFAULT (JSON_OBJECT()),
                pdf_path VARCHAR(500),
                generated_by INT NOT NULL,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            db.execute(text(create_table_query))
            
            insert_query = text("""
                INSERT INTO generated_reports 
                (template_id, template_name, report_type, generated_data, 
                 charts_data, pdf_path, generated_by, generated_at)
                VALUES 
                (:template_id, :template_name, :report_type, :generated_data,
                 :charts_data, :pdf_path, :generated_by, :generated_at)
            """)
            
            result = db.execute(insert_query, {
                "template_id": request.template_id,
                "template_name": template_name,
                "report_type": template_type,
                "generated_data": json.dumps(query_result),
                "charts_data": json.dumps(charts),
                "pdf_path": pdf_path,
                "generated_by": user_id,
                "generated_at": datetime.utcnow()
            })
            
            db.commit()
            report_id = result.lastrowid
        except Exception as e:
            print(f"Failed to save report to database: {e}")
            report_id = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "report_id": report_id,
            "message": "Report generated successfully",
            "html_path": html_path,
            "csv_path": csv_path,
            "pdf_path": pdf_path if HAS_ADVANCED_FEATURES else None,
            "data_count": len(query_result["data"]),
            "charts_count": len(charts),
            "advanced_features": HAS_ADVANCED_FEATURES
        }
    
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@router.get("/reports", response_model=List[ReportResponse])
async def get_generated_reports(db: Session = Depends(get_db)):
    """Get all generated reports"""
    try:
        query = text("SELECT * FROM generated_reports ORDER BY generated_at DESC")
        result = db.execute(query)
        reports = []
        
        for row in result:
            reports.append(ReportResponse(
                id=row.id,
                template_id=row.template_id,
                template_name=row.template_name,
                report_type=row.report_type,
                generated_data=json.loads(row.generated_data) if isinstance(row.generated_data, str) else row.generated_data,
                charts_data=json.loads(row.charts_data) if isinstance(row.charts_data, str) else row.charts_data,
                pdf_path=row.pdf_path,
                generated_by=row.generated_by,
                generated_at=row.generated_at
            ))
        
        return reports
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reports: {str(e)}")

@router.post("/send-email")
async def send_report_email(email_request: EmailReportRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Send generated report via email"""
    try:
        query = text("SELECT * FROM generated_reports WHERE id = :report_id")
        result = db.execute(query, {"report_id": email_request.report_id})
        report = result.fetchone()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        background_tasks.add_task(send_email_with_attachment, email_request, report.pdf_path)
        
        return {"message": "Email is being prepared in the background"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating email: {str(e)}")

@router.get("/check-tables")
async def check_database_tables(db: Session = Depends(get_db)):
    """Check which tables exist in the database"""
    try:
        tables_to_check = ["users", "timesheets", "leave_requests", "expense_claims", "report_templates", "generated_reports"]
        table_status = {}
        
        for table in tables_to_check:
            table_status[table] = table_exists(db, table)
        
        return {
            "database_tables": table_status,
            "missing_tables": [table for table, exists in table_status.items() if not exists],
            "advanced_features": HAS_ADVANCED_FEATURES,
            "report_models": HAS_REPORT_MODELS
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking tables: {str(e)}")

@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a report template"""
    try:
        query = text("DELETE FROM report_templates WHERE id = :template_id")
        result = db.execute(query, {"template_id": template_id})
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Template not found")
        
        db.commit()
        return {"message": "Template deleted successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting template: {str(e)}")

@router.delete("/reports/{report_id}")
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    """Delete a generated report"""
    try:
        select_query = text("SELECT pdf_path FROM generated_reports WHERE id = :report_id")
        result = db.execute(select_query, {"report_id": report_id})
        report = result.fetchone()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Delete files if they exist
        if report.pdf_path and os.path.exists(report.pdf_path):
            os.remove(report.pdf_path)
        
        delete_query = text("DELETE FROM generated_reports WHERE id = :report_id")
        db.execute(delete_query, {"report_id": report_id})
        db.commit()
        
        return {"message": "Report deleted successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting report: {str(e)}")
@router.get("/download/{filename}")
async def download_report(filename: str):
    """Download a specific report file"""
    try:
        file_path = f"reports/{filename}"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine content type based on file extension
        if filename.endswith('.pdf'):
            media_type = 'application/pdf'
        elif filename.endswith('.html'):
            media_type = 'text/html'
        elif filename.endswith('.csv'):
            media_type = 'text/csv'
        else:
            media_type = 'application/octet-stream'
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

@router.get("/view/{filename}")
async def view_report(filename: str):
    """View a specific report file in browser"""
    try:
        file_path = f"reports/{filename}"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # For viewing in browser (inline display)
        if filename.endswith('.pdf'):
            media_type = 'application/pdf'
        elif filename.endswith('.html'):
            media_type = 'text/html'
        else:
            media_type = 'application/octet-stream'
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            headers={"Content-Disposition": "inline"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error viewing file: {str(e)}")