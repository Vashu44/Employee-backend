# router/report_router.py - Windows Compatible Version with xhtml2pdf

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import json, time, os, uuid
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

# Use xhtml2pdf instead of WeasyPrint (Windows compatible)
from xhtml2pdf import pisa
import io

from db.database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Utility functions
def serialize_value(value):
    """Convert any value to JSON serializable format"""
    if value is None:
        return None
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return str(value)
    else:
        return value

def serialize_row(row):
    """Convert a database row to JSON serializable format"""
    return [serialize_value(cell) for cell in row]

def get_query_type(query: str) -> tuple:
    """Categorize SQL query"""
    q = query.upper().strip()
    if q.startswith('SELECT'): return 'DQL', 'SELECT'
    elif q.startswith('SHOW'): return 'DQL', 'SHOW'
    elif q.startswith('DESCRIBE') or q.startswith('DESC'): return 'DQL', 'DESCRIBE'
    elif q.startswith('INSERT'): return 'DML', 'INSERT'
    elif q.startswith('UPDATE'): return 'DML', 'UPDATE'
    elif q.startswith('DELETE'): return 'DML', 'DELETE'
    elif q.startswith('CREATE'): return 'DDL', 'CREATE'
    elif q.startswith('ALTER'): return 'DDL', 'ALTER'
    elif q.startswith('DROP'): return 'DDL', 'DROP'
    elif q.startswith('TRUNCATE'): return 'DDL', 'TRUNCATE'
    else: return 'OTHER', 'OTHER'

def ensure_tables_exist(db: Session):
    """Create tables if they don't exist"""
    try:
        # Create hr_reports table
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS hr_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                user_id INT NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                status ENUM('draft', 'completed', 'failed') DEFAULT 'draft',
                pdf_generated BOOLEAN DEFAULT FALSE,
                pdf_path VARCHAR(500) NULL,
                total_queries INT DEFAULT 0
            )
        """))
        
        # Create report_query_executions table
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS report_query_executions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                report_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                sql_query TEXT NOT NULL,
                query_category VARCHAR(10) NOT NULL,
                query_type VARCHAR(20) NOT NULL,
                result_data JSON,
                affected_rows INT DEFAULT 0,
                execution_time VARCHAR(20),
                execution_order INT NOT NULL DEFAULT 1,
                status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
                error_message TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (report_id) REFERENCES hr_reports(id) ON DELETE CASCADE
            )
        """))
        
        db.commit()
    except Exception as e:
        print(f"Table creation warning: {e}")

def execute_single_query(db: Session, query_data: dict, report_id: int) -> dict:
    """Execute a single query and return results"""
    start_time = time.time()
    
    try:
        category, query_type = get_query_type(query_data['sql_query'])
        result = db.execute(text(query_data['sql_query']))
        exec_time = time.time() - start_time
        
        if query_type in ['SELECT', 'SHOW', 'DESCRIBE']:
            rows = result.fetchall()
            if rows:
                columns = list(result.keys())
                data = [serialize_row(row) for row in rows]
            else:
                columns = []
                data = []
            affected = len(data)
        else:
            affected = getattr(result, 'rowcount', 0)
            columns = ["Status", "Rows_Affected"]
            data = [["Success", affected]]
            db.commit()
        
        # Save query execution to database
        result_data_json = json.dumps({
            "columns": columns,
            "data": data,
            "total_rows": len(data),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        insert_query = text("""
            INSERT INTO report_query_executions
            (report_id, title, description, sql_query, query_category, query_type, 
             result_data, affected_rows, execution_time, execution_order, status)
            VALUES
            (:report_id, :title, :description, :sql_query, :category, :qtype, 
             :result_data, :affected_rows, :exec_time, :execution_order, 'completed')
        """)
        
        db.execute(insert_query, {
            "report_id": report_id,
            "title": query_data['title'],
            "description": query_data.get('description'),
            "sql_query": query_data['sql_query'],
            "category": category,
            "qtype": query_type,
            "result_data": result_data_json,
            "affected_rows": affected,
            "exec_time": f"{exec_time:.3f}s",
            "execution_order": query_data.get('execution_order', 1)
        })
        
        return {
            "status": "completed",
            "columns": columns,
            "data": data,
            "affected_rows": affected,
            "execution_time": f"{exec_time:.3f}s",
            "query_category": category,
            "query_type": query_type
        }
        
    except Exception as e:
        # Save failed query execution
        insert_query = text("""
            INSERT INTO report_query_executions
            (report_id, title, description, sql_query, query_category, query_type, 
             execution_order, status, error_message)
            VALUES
            (:report_id, :title, :description, :sql_query, 'OTHER', 'OTHER', 
             :execution_order, 'failed', :error_message)
        """)
        
        db.execute(insert_query, {
            "report_id": report_id,
            "title": query_data['title'],
            "description": query_data.get('description'),
            "sql_query": query_data['sql_query'],
            "execution_order": query_data.get('execution_order', 1),
            "error_message": str(e)
        })
        
        return {
            "status": "failed",
            "error_message": str(e),
            "columns": [],
            "data": [],
            "affected_rows": 0,
            "execution_time": "0s"
        }
def generate_html_report(report_data: dict, query_results: List[dict]) -> str:
    """Generate beautifully styled HTML content for professional PDF reports"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{report_data['title']}</title>
        <style>
            @page {{
                size: A4;
                margin: 0.8cm;
                @bottom-center {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 9px;
                    color: #6b7280;
                }}
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #1f2937;
                line-height: 1.6;
                background-color: #ffffff;
            }}
            
            .report-container {{
                max-width: 100%;
                margin: 0 auto;
            }}
            
            /* Header Styling */
            .report-header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 12px;
                margin-bottom: 30px;
                text-align: center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }}
            
            .report-title {{ 
                font-size: 28px; 
                font-weight: 700; 
                margin-bottom: 12px;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }}
            
            .report-description {{ 
                font-size: 16px; 
                opacity: 0.95;
                margin-bottom: 15px;
                font-weight: 300;
                line-height: 1.5;
            }}
            
            .report-meta {{ 
                font-size: 12px; 
                opacity: 0.8;
                border-top: 1px solid rgba(255,255,255,0.2);
                padding-top: 15px;
                display: flex;
                justify-content: center;
                gap: 20px;
                flex-wrap: wrap;
            }}
            
            .meta-item {{
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            
            /* Query Section Styling */
            .query-section {{ 
                margin: 25px 0; 
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                overflow: hidden;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                page-break-inside: avoid;
            }}
            
            .query-header {{
                background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%);
                padding: 20px;
                border-bottom: 2px solid #e5e7eb;
            }}
            
            .query-title {{ 
                font-size: 20px; 
                font-weight: 600; 
                color: #1e40af;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .query-number {{
                background: #3b82f6;
                color: white;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                font-weight: 700;
            }}
            
            .query-description {{ 
                font-size: 14px; 
                color: #6b7280; 
                font-style: italic;
                line-height: 1.5;
            }}
            
            .query-content {{
                padding: 20px;
            }}
            
            /* Table Styling */
            .results-table {{ 
                width: 100%; 
                border-collapse: separate;
                border-spacing: 0;
                margin-top: 15px;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.12);
                font-size: 11px;
            }}
            
            .results-table th {{ 
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white;
                font-weight: 600; 
                padding: 12px 10px;
                text-align: left;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border-bottom: 3px solid #3730a3;
            }}
            
            .results-table th:first-child {{
                border-top-left-radius: 8px;
            }}
            
            .results-table th:last-child {{
                border-top-right-radius: 8px;
            }}
            
            .results-table td {{ 
                padding: 12px 10px;
                border-bottom: 1px solid #f1f5f9;
                font-size: 11px;
                vertical-align: top;
                max-width: 200px;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }}
            
            .results-table tbody tr:nth-child(even) {{
                background-color: #f8fafc;
            }}
            
            .results-table tbody tr:hover {{
                background-color: #e0e7ff;
                transition: all 0.2s ease;
            }}
            
            .results-table tbody tr:last-child td:first-child {{
                border-bottom-left-radius: 8px;
            }}
            
            .results-table tbody tr:last-child td:last-child {{
                border-bottom-right-radius: 8px;
            }}
            
            /* No Data Styling */
            .no-data {{
                text-align: center;
                padding: 40px 20px;
                background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
                border-radius: 8px;
                margin: 15px 0;
            }}
            
            .no-data-icon {{
                font-size: 48px;
                color: #cbd5e1;
                margin-bottom: 15px;
            }}
            
            .no-data-text {{
                color: #64748b;
                font-size: 14px;
                font-weight: 500;
            }}
            
            .no-data-subtext {{
                color: #94a3b8;
                font-size: 12px;
                margin-top: 5px;
            }}
            
            /* Query Metadata */
            .query-meta {{ 
                background: #f8fafc;
                padding: 15px 20px;
                margin-top: 15px;
                border-top: 2px solid #e2e8f0;
                border-radius: 0 0 8px 8px;
            }}
            
            .meta-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                font-size: 11px;
            }}
            
            .meta-item {{
                display: flex;
                align-items: center;
                gap: 8px;
                color: #6b7280;
            }}
            
            .meta-icon {{
                color: #9ca3af;
                font-size: 12px;
            }}
            
            .meta-value {{
                font-weight: 600;
                color: #374151;
            }}
            
            /* Error Styling */
            .error {{ 
                background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
                border: 2px solid #f87171;
                border-radius: 8px;
                padding: 20px;
                margin: 15px 0;
            }}
            
            .error-header {{
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 10px;
            }}
            
            .error-icon {{
                color: #dc2626;
                font-size: 20px;
            }}
            
            .error-title {{
                color: #991b1b;
                font-weight: 600;
                font-size: 14px;
            }}
            
            .error-message {{
                color: #7f1d1d;
                font-size: 12px;
                line-height: 1.5;
                margin-left: 30px;
            }}
            
            /* Footer Styling */
            .report-footer {{
                margin-top: 40px;
                padding: 25px;
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                border-radius: 12px;
                text-align: center;
                border-top: 3px solid #3b82f6;
            }}
            
            .footer-content {{
                color: #64748b;
                font-size: 11px;
                line-height: 1.6;
            }}
            
            .footer-title {{
                color: #334155;
                font-weight: 600;
                margin-bottom: 8px;
            }}
            
            /* Utility Classes */
            .text-center {{ text-align: center; }}
            .font-bold {{ font-weight: 700; }}
            .text-sm {{ font-size: 12px; }}
            .text-xs {{ font-size: 11px; }}
            .mb-2 {{ margin-bottom: 8px; }}
            .mt-3 {{ margin-top: 12px; }}
            
            /* Print Optimizations */
            @media print {{
                .query-section {{
                    break-inside: avoid;
                }}
                .results-table {{
                    font-size: 10px;
                }}
                .results-table th,
                .results-table td {{
                    padding: 8px 6px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <!-- Professional Header -->
            <div class="report-header">
                <div class="report-title">{report_data['title']}</div>
                <div class="report-description">{report_data.get('description', '')}</div>
                <div class="report-meta">
                    <div class="meta-item">
                        <span>📅</span>
                        <span>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</span>
                    </div>
                    <div class="meta-item">
                        <span>🆔</span>
                        <span>Report ID: {report_data['id']}</span>
                    </div>
                    <div class="meta-item">
                        <span>📊</span>
                        <span>Sections: {len(query_results)}</span>
                    </div>
                </div>
            </div>
    """
    
    # Process each query result
    for i, query in enumerate(query_results, 1):
        html_content += f"""
            <div class="query-section">
                <div class="query-header">
                    <div class="query-title">
                        <div class="query-number">{i}</div>
                        <div>{query['title']}</div>
                    </div>
                    <div class="query-description">{query.get('description', '')}</div>
                </div>
                
                <div class="query-content">
        """
        
        if query['status'] == 'completed':
            if query['columns'] and query['data']:
                html_content += """
                    <table class="results-table">
                        <thead>
                            <tr>
                """
                
                # Add table headers
                for col in query['columns']:
                    html_content += f"<th>{str(col).replace('_', ' ').title()}</th>"
                
                html_content += "</tr></thead><tbody>"
                
                # Add table rows (limit to 50 rows for better PDF performance)
                for row_idx, row in enumerate(query['data'][:50]):
                    html_content += "<tr>"
                    for cell in row:
                        if cell is not None:
                            cell_str = str(cell)
                            # Truncate very long content
                            if len(cell_str) > 100:
                                cell_str = cell_str[:97] + "..."
                            # Escape HTML characters
                            cell_str = cell_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        else:
                            cell_str = '<span style="color: #9ca3af; font-style: italic;">N/A</span>'
                        html_content += f"<td>{cell_str}</td>"
                    html_content += "</tr>"
                
                html_content += "</tbody></table>"
                
                # Show truncation message if needed
                if len(query['data']) > 50:
                    html_content += f"""
                    <div class="text-center mt-3 text-sm" style="color: #6b7280; font-style: italic;">
                        📋 Displaying first 50 rows of {len(query['data'])} total records
                    </div>
                    """
                    
            else:
                html_content += """
                    <div class="no-data">
                        <div class="no-data-icon">📊</div>
                        <div class="no-data-text">No Data Available</div>
                        <div class="no-data-subtext">This query executed successfully but returned no results</div>
                    </div>
                """
                
            # Add execution metadata
            html_content += f"""
                    <div class="query-meta">
                        <div class="meta-grid">
                            <div class="meta-item">
                                <span class="meta-icon">⏱️</span>
                                <span>Execution Time: <span class="meta-value">{query['execution_time']}</span></span>
                            </div>
                            <div class="meta-item">
                                <span class="meta-icon">📄</span>
                                <span>Records: <span class="meta-value">{query['affected_rows']:,}</span></span>
                            </div>
                            <div class="meta-item">
                                <span class="meta-icon">🔧</span>
                                <span>Query Type: <span class="meta-value">{query['query_type']}</span></span>
                            </div>
                            <div class="meta-item">
                                <span class="meta-icon">✅</span>
                                <span>Status: <span class="meta-value">Success</span></span>
                            </div>
                        </div>
                    </div>
            """
        else:
            # Show error with professional styling
            html_content += f"""
                    <div class="error">
                        <div class="error-header">
                            <span class="error-icon">⚠️</span>
                            <span class="error-title">Query Execution Failed</span>
                        </div>
                        <div class="error-message">{query.get('error_message', 'An unknown error occurred while executing this query.')}</div>
                    </div>
            """
        
        html_content += """
                </div>
            </div>
        """
    
    # Add professional footer
    html_content += f"""
            <!-- Professional Footer -->
            <div class="report-footer">
                <div class="footer-content">
                    <div class="footer-title">🏢 HR Intranet System</div>
                    <div>This report was automatically generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
                    <div style="margin-top: 8px; font-size: 10px; color: #94a3b8;">
                        Confidential & Proprietary • For Internal Use Only
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def generate_pdf_from_html(html_content: str, filename: str) -> str:
    """Generate PDF from HTML content using xhtml2pdf (Windows compatible)"""
    try:
        # Create pdfs directory if it doesn't exist
        pdf_dir = Path("static/pdfs")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_path = pdf_dir / filename
        
        # Generate PDF using xhtml2pdf
        with open(pdf_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
            
            if pisa_status.err:
                raise Exception(f"PDF generation failed with errors: {pisa_status.err}")
        
        return str(pdf_path)
    except Exception as e:
        print(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

# Pydantic models for request/response
from pydantic import BaseModel, validator
from typing import Optional, List

class QueryExecutionRequest(BaseModel):
    title: str
    description: Optional[str] = None
    sql_query: str
    execution_order: int = 1
    
    @validator('sql_query')
    def validate_sql_query(cls, v):
        query_clean = v.strip().upper()
        allowed_starts = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'REPLACE',
            'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE', 'TRUNCATE',
            'CREATE INDEX', 'DROP INDEX', 'SHOW', 'DESCRIBE'
        ]
        
        is_valid = any(query_clean.startswith(start) for start in allowed_starts)
        if not is_valid:
            raise ValueError('Query type not supported or not allowed')
            
        dangerous_keywords = [
            'INFORMATION_SCHEMA', 'MYSQL', 'PERFORMANCE_SCHEMA', 'SYS',
            '/*', '*/', '--', ';--', 'EXEC', 'EXECUTE', 'EVAL'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_clean:
                raise ValueError(f'Dangerous keyword "{keyword}" not allowed')
        return v

class CreateReportRequest(BaseModel):
    title: str
    description: Optional[str] = None
    queries: List[QueryExecutionRequest]
    
    @validator('title')
    def validate_title(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Title must be at least 3 characters long')
        return v.strip()
    
    @validator('queries')
    def validate_queries(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one query is required')
        if len(v) > 20:
            raise ValueError('Maximum 20 queries allowed per report')
        return v

class QueryExecutionResponse(BaseModel):
    id: int
    title: str 
    description: Optional[str]
    query_category: str
    query_type: str
    columns: List[str] = []
    data: List[List[Any]] = []
    affected_rows: int
    execution_time: Optional[str]
    execution_order: int
    status: str
    error_message: Optional[str] = None

class ReportResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    user_id: int
    created_at: datetime
    updated_at: datetime
    status: str
    pdf_generated: bool
    pdf_path: Optional[str]
    total_queries: int
    query_executions: List[QueryExecutionResponse] = []

class ReportListResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    user_id: int
    created_at: datetime
    status: str
    pdf_generated: bool
    total_queries: int

# API Endpoints
@router.post("/create", response_model=ReportResponse)
async def create_report_with_queries(request: CreateReportRequest, db: Session = Depends(get_db)):
    """Create a new report with multiple queries and generate PDF"""
    try:
        ensure_tables_exist(db)
        
        # Create main report
        insert_report = text("""
            INSERT INTO hr_reports (title, description, user_id, total_queries, status)
            VALUES (:title, :description, 1, :total_queries, 'draft')
        """)
        
        db.execute(insert_report, {
            "title": request.title,
            "description": request.description,
            "total_queries": len(request.queries)
        })
        
        # Get report ID
        report_result = db.execute(text("SELECT LAST_INSERT_ID() as id"))
        report_id = report_result.fetchone()[0]
        
        # Execute all queries
        query_results = []
        completed_queries = 0
        
        for query_req in request.queries:
            query_data = {
                "title": query_req.title,
                "description": query_req.description,
                "sql_query": query_req.sql_query,
                "execution_order": query_req.execution_order
            }
            
            result = execute_single_query(db, query_data, report_id)
            query_results.append({
                **query_data,
                **result
            })
            
            if result['status'] == 'completed':
                completed_queries += 1
        
        # Update report status
        report_status = 'completed' if completed_queries == len(request.queries) else 'failed'
        
        # Generate PDF
        pdf_filename = f"report_{report_id}_{uuid.uuid4().hex[:8]}.pdf"
        
        try:
            report_data = {
                "id": report_id,
                "title": request.title,
                "description": request.description
            }
            
            html_content = generate_html_report(report_data, query_results)
            pdf_path = generate_pdf_from_html(html_content, pdf_filename)
            
            # Update report with PDF info
            update_report = text("""
                UPDATE hr_reports 
                SET status = :status, pdf_generated = TRUE, pdf_path = :pdf_path, updated_at = NOW()
                WHERE id = :report_id
            """)
            
            db.execute(update_report, {
                "status": report_status,
                "pdf_path": pdf_path,
                "report_id": report_id
            })
            
        except Exception as pdf_error:
            print(f"PDF generation failed: {pdf_error}")
            # Update report without PDF
            update_report = text("""
                UPDATE hr_reports 
                SET status = :status, updated_at = NOW()
                WHERE id = :report_id
            """)
            
            db.execute(update_report, {
                "status": report_status,
                "report_id": report_id
            })
            pdf_path = None
        
        db.commit()
        
        # Get complete report data
        return await get_report_detail(report_id, db)
        
    except Exception as e:
        db.rollback()
        print(f"Report creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report creation failed: {str(e)}")

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report_detail(report_id: int, db: Session = Depends(get_db)):
    """Get detailed report information with all query executions"""
    try:
        # Get report info
        report_query = text("""
            SELECT id, title, description, user_id, created_at, updated_at, 
                   status, pdf_generated, pdf_path, total_queries
            FROM hr_reports WHERE id = :report_id
        """)
        
        report_result = db.execute(report_query, {"report_id": report_id})
        report_row = report_result.fetchone()
        
        if not report_row:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get query executions
        queries_query = text("""
            SELECT id, title, description, query_category, query_type, result_data,
                   affected_rows, execution_time, execution_order, status, error_message
            FROM report_query_executions 
            WHERE report_id = :report_id 
            ORDER BY execution_order
        """)
        
        queries_result = db.execute(queries_query, {"report_id": report_id})
        query_rows = queries_result.fetchall()
        
        query_executions = []
        for row in query_rows:
            result_data = json.loads(row[5]) if row[5] else {"columns": [], "data": []}
            query_executions.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "query_category": row[3],
                "query_type": row[4],
                "columns": result_data.get("columns", []),
                "data": result_data.get("data", []),
                "affected_rows": row[6],
                "execution_time": row[7],
                "execution_order": row[8],
                "status": row[9],
                "error_message": row[10]
            })
        
        return {
            "id": report_row[0],
            "title": report_row[1],
            "description": report_row[2],
            "user_id": report_row[3],
            "created_at": report_row[4],
            "updated_at": report_row[5],
            "status": report_row[6],
            "pdf_generated": report_row[7],
            "pdf_path": report_row[8],
            "total_queries": report_row[9],
            "query_executions": query_executions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get report error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving report: {str(e)}")

@router.get("/{report_id}/download-pdf")
async def download_report_pdf(report_id: int, db: Session = Depends(get_db)):
    """Download the PDF file for a report"""
    try:
        query = text("SELECT pdf_path, title FROM hr_reports WHERE id = :report_id AND pdf_generated = TRUE")
        result = db.execute(query, {"report_id": report_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Report PDF not found")
        
        pdf_path, title = row
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found on disk")
        
        return FileResponse(
            path=pdf_path,
            filename=f"{title.replace(' ', '_')}_report.pdf",
            media_type='application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"PDF download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading PDF: {str(e)}")

@router.get("/", response_model=List[ReportListResponse])
async def get_all_reports(limit: int = 50, db: Session = Depends(get_db)):
    """Get list of all reports"""
    try:
        ensure_tables_exist(db)
        
        query = text("""
            SELECT id, title, description, user_id, created_at, status, pdf_generated, total_queries
            FROM hr_reports
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit})
        rows = result.fetchall()
        
        reports = []
        for row in rows:
            reports.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "user_id": row[3],
                "created_at": row[4],
                "status": row[5],
                "pdf_generated": row[6],
                "total_queries": row[7]
            })
        
        return reports
        
    except Exception as e:
        print(f"Get reports error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving reports: {str(e)}")
