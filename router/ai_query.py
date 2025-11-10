from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
import httpx
import os
import time
import re
from db.database import get_db

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Query Generation"]
)

# Pydantic Models
class NaturalLanguageQuery(BaseModel):
    query: str = Field(..., description="Natural language query to convert to SQL")
    provider: str = Field(default="local", description="AI provider: 'local', 'ollama' or 'openai'")
    context: Optional[str] = Field(None, description="Additional context for query generation")
    database_schema: Optional[Dict[str, Any]] = Field(None, description="Database schema for context")

class SQLResponse(BaseModel):
    sql_query: str
    provider: str
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    explanation: Optional[str] = None
    query_type: Optional[str] = None

class QueryValidation(BaseModel):
    is_valid: bool
    error_message: Optional[str] = None
    suggestions: Optional[List[str]] = None

class AIHealthStatus(BaseModel):
    local_available: bool
    ollama_available: bool
    openai_configured: bool
    services_status: Dict[str, Any]
    last_check: datetime

# Database Schema
HR_DATABASE_SCHEMA = {
    "users": {
        "columns": ["id", "username", "email", "password", "is_verified", "role", "last_login", "is_active", "full_name", "created_at", "updated_at"],
        "relationships": []
    },
    "user_details": {
        "columns": ["id", "user_id", "first_name", "last_name", "employee_id", "department", "phone", "address", "created_at", "updated_at"],
        "relationships": [{"table": "users", "foreign_key": "user_id", "references": "id"}]
    },
    "background_check_forms": {
        "columns": ["id", "candidate_name", "father_name", "mother_name", "date_of_birth", "marital_status", 
                   "email_id", "contact_number", "alternate_contact_number", "aadhaar_card_number", "pan_number", 
                   "uan_number", "current_complete_address", "current_city", "current_state", "current_pin_code", 
                   "permanent_complete_address", "permanent_city", "permanent_state", "permanent_pin_code", 
                   "organization_name", "designation", "employee_code", "date_of_joining", "last_working_day", 
                   "salary", "manager_name", "manager_contact_number", "manager_email_id", "education_details", 
                   "hr_details", "reference_details", "verification_checks", "status", "created_at", "updated_at"],
        "relationships": []
    },
    "assets": {
        "columns": ["id", "asset_code", "asset_name", "category", "brand", "model", "serial_number",
                   "purchase_date", "purchase_price", "warranty_period", "description", "status",
                   "location", "assigned_to", "approval_status", "provided_to_employee",
                   "approved_by", "approved_at", "rejection_reason", "created_at", "updated_at"],
        "relationships": [
            {"table": "users", "foreign_key": "assigned_to", "references": "id"},
            {"table": "users", "foreign_key": "approved_by", "references": "id"}
        ]
    },
    "expense_claims": {
        "columns": ["id", "user_id", "approver_id", "title", "description", "claim_date",
                   "total_amount", "approved_amount", "currency", "status", "rejection_reason",
                   "submission_date", "approval_date", "created_at", "updated_at", "employee_id"],
        "relationships": [
            {"table": "users", "foreign_key": "user_id", "references": "id"},
            {"table": "users", "foreign_key": "approver_id", "references": "id"}
        ]
    },
    "expense_items": {
        "columns": ["id", "claim_id", "category_id", "item_description", "expense_date",
                   "amount", "approved_amount", "currency", "vendor_name", "payment_method",
                   "receipt_number", "business_purpose", "is_billable", "client_name",
                   "project_code", "created_at", "updated_at"],
        "relationships": [
            {"table": "expense_claims", "foreign_key": "claim_id", "references": "id"},
            {"table": "expense_categories", "foreign_key": "category_id", "references": "id"}
        ]
    },
    "appreciations": {
        "columns": ["id", "employee_id", "given_by_id", "award_type",
                   "badge_level", "appreciation_message", "month", "year", "is_active", "created_at", "updated_at"],
        "relationships": [
            {"table": "users", "foreign_key": "employee_id", "references": "id"},
            {"table": "users", "foreign_key": "given_by_id", "references": "id"}
        ]
    }
}

# Local Rule-Based SQL Generator
def generate_local_sql(query: str) -> str:
    """Generate SQL using local rule-based approach"""
    query_lower = query.lower().strip()
    
    # Enhanced patterns for common queries
    patterns = [
        # Employee queries
        (r'.*active.*employees.*email.*', "SELECT full_name, email FROM users WHERE is_active = 1 ORDER BY full_name"),
        (r'.*all.*employees.*', "SELECT id, full_name, email, role FROM users WHERE is_active = 1 ORDER BY full_name LIMIT 100"),
        (r'.*employee.*count.*department.*', "SELECT ud.department, COUNT(*) as employee_count FROM users u JOIN user_details ud ON u.id = ud.user_id WHERE u.is_active = 1 GROUP BY ud.department ORDER BY employee_count DESC"),
        (r'.*employees.*department.*', "SELECT u.full_name, u.email, ud.department FROM users u JOIN user_details ud ON u.id = ud.user_id WHERE u.is_active = 1 ORDER BY ud.department, u.full_name"),
        
        # Expense queries
        (r'.*pending.*expense.*claims.*', "SELECT id, title, total_amount, user_id, created_at FROM expense_claims WHERE status = 'pending' ORDER BY created_at DESC LIMIT 50"),
        (r'.*expense.*claims.*month.*', "SELECT id, title, total_amount, status, created_at FROM expense_claims WHERE MONTH(created_at) = MONTH(CURDATE()) AND YEAR(created_at) = YEAR(CURDATE()) ORDER BY created_at DESC LIMIT 100"),
        (r'.*expense.*amount.*department.*', "SELECT ud.department, AVG(ec.total_amount) as avg_amount, COUNT(*) as claim_count FROM expense_claims ec JOIN users u ON ec.user_id = u.id JOIN user_details ud ON u.id = ud.user_id WHERE ec.status = 'approved' GROUP BY ud.department ORDER BY avg_amount DESC"),
        (r'.*total.*expense.*user.*', "SELECT u.full_name, SUM(ec.total_amount) as total_expenses, COUNT(*) as claim_count FROM users u JOIN expense_claims ec ON u.id = ec.user_id WHERE ec.status = 'approved' GROUP BY u.id, u.full_name ORDER BY total_expenses DESC LIMIT 20"),
        
        # Asset queries
        (r'.*assets.*it.*department.*', "SELECT a.asset_name, a.asset_code, u.full_name, a.status FROM assets a JOIN users u ON a.assigned_to = u.id JOIN user_details ud ON u.id = ud.user_id WHERE ud.department = 'IT' AND a.status = 'assigned' ORDER BY a.asset_name"),
        (r'.*available.*assets.*', "SELECT asset_name, asset_code, category, brand, model FROM assets WHERE status = 'available' ORDER BY category, asset_name LIMIT 50"),
        (r'.*laptops.*assigned.*', "SELECT asset_name, asset_code, u.full_name, a.assigned_to FROM assets a LEFT JOIN users u ON a.assigned_to = u.id WHERE a.category LIKE '%laptop%' AND a.status = 'assigned' ORDER BY a.asset_name LIMIT 50"),
        (r'.*assets.*unassigned.*', "SELECT asset_name, asset_code, category, status FROM assets WHERE assigned_to IS NULL OR status = 'available' ORDER BY category, asset_name LIMIT 50"),
        
        # Background check queries
        (r'.*background.*check.*30.*days.*', "SELECT candidate_name, email_id, status, created_at FROM background_check_forms WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) ORDER BY created_at DESC LIMIT 50"),
        (r'.*background.*check.*completed.*', "SELECT candidate_name, email_id, organization_name, created_at FROM background_check_forms WHERE status = 'completed' ORDER BY created_at DESC LIMIT 50"),
        (r'.*birthdays.*month.*', "SELECT candidate_name, email_id, date_of_birth FROM background_check_forms WHERE MONTH(date_of_birth) = MONTH(CURDATE()) ORDER BY DAY(date_of_birth)"),
        (r'.*birthdays.*today.*', "SELECT candidate_name, email_id, date_of_birth, contact_number FROM background_check_forms WHERE DAY(date_of_birth) = DAY(CURDATE()) AND MONTH(date_of_birth) = MONTH(CURDATE())"),
        
        # User activity queries
        (r'.*users.*not.*logged.*30.*', "SELECT username, email, full_name, last_login FROM users WHERE (last_login < DATE_SUB(CURDATE(), INTERVAL 30 DAY) OR last_login IS NULL) AND is_active = 1 ORDER BY last_login DESC LIMIT 50"),
        (r'.*new.*users.*week.*', "SELECT username, email, full_name, created_at, role FROM users WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) ORDER BY created_at DESC LIMIT 50"),
        (r'.*hr.*role.*', "SELECT id, username, email, full_name, created_at FROM users WHERE role = 'hr' AND is_active = 1 ORDER BY full_name"),
        (r'.*admin.*users.*', "SELECT id, username, email, full_name, last_login FROM users WHERE role = 'admin' AND is_active = 1 ORDER BY full_name"),
        
        # Appreciation queries
        (r'.*employee.*month.*award.*', "SELECT u.full_name, a.award_type, a.appreciation_message, a.month, a.year FROM users u JOIN appreciations a ON u.id = a.employee_id WHERE a.award_type LIKE '%Employee of the Month%' AND a.is_active = 1 ORDER BY a.year DESC, a.month DESC"),
        (r'.*appreciation.*awards.*', "SELECT u.full_name, a.award_type, a.appreciation_message, a.created_at FROM users u JOIN appreciations a ON u.id = a.employee_id WHERE a.is_active = 1 ORDER BY a.created_at DESC LIMIT 50"),
        (r'.*awards.*this.*year.*', "SELECT u.full_name, a.award_type, a.month FROM users u JOIN appreciations a ON u.id = a.employee_id WHERE a.year = YEAR(CURDATE()) AND a.is_active = 1 ORDER BY a.month DESC"),
        
        # Salary and compensation queries
        (r'.*salary.*information.*', "SELECT candidate_name, organization_name, designation, salary FROM background_check_forms WHERE salary IS NOT NULL AND salary > 0 ORDER BY salary DESC LIMIT 50"),
        (r'.*highest.*paid.*', "SELECT candidate_name, organization_name, salary FROM background_check_forms WHERE salary IS NOT NULL ORDER BY salary DESC LIMIT 10"),
        
        # Count queries
        (r'.*count.*users.*', "SELECT COUNT(*) as total_users, SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_users, SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive_users FROM users"),
        (r'.*count.*assets.*', "SELECT COUNT(*) as total_assets, status, COUNT(*) as count_by_status FROM assets GROUP BY status"),
        (r'.*count.*expense.*claims.*', "SELECT COUNT(*) as total_claims, status, COUNT(*) as count_by_status FROM expense_claims GROUP BY status"),
        
        # Recent activity
        (r'.*recent.*activity.*', "SELECT 'User Registration' as activity_type, username as details, created_at FROM users WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) UNION ALL SELECT 'Expense Claim' as activity_type, title as details, created_at FROM expense_claims WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) ORDER BY created_at DESC LIMIT 20"),
        
        # Default fallbacks
        (r'.*show.*users.*', "SELECT id, username, email, full_name, role FROM users WHERE is_active = 1 ORDER BY full_name LIMIT 50"),
        (r'.*list.*employees.*', "SELECT full_name, email, role FROM users WHERE is_active = 1 ORDER BY full_name LIMIT 50"),
    ]
    
    # Try to match patterns
    for pattern, sql in patterns:
        if re.match(pattern, query_lower):
            return sql
    
    # Default fallback
    return "SELECT id, username, email, full_name, role FROM users WHERE is_active = 1 ORDER BY full_name LIMIT 10"

async def generate_with_local(query: str, context: str = None, schema: Dict[str, Any] = None) -> SQLResponse:
    """Generate SQL using local rule-based approach"""
    try:
        sql_query = generate_local_sql(query)
        
        return SQLResponse(
            sql_query=sql_query,
            provider="local",
            confidence=0.85,
            query_type="SELECT",
            explanation="Generated using enhanced local rule-based SQL generator with 25+ patterns"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Local generator error: {str(e)}")

async def check_openai_models() -> List[str]:
    """Check available OpenAI models"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if response.status_code == 200:
                models = response.json().get("data", [])
                return [model["id"] for model in models if "gpt" in model["id"]]
            else:
                return []
    except:
        return []

async def generate_with_openai(query: str, context: str = None, schema: Dict[str, Any] = None) -> SQLResponse:
    """Generate SQL using OpenAI API with model fallback"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500, 
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY in your environment variables."
            )
        
        # Try different models in order of preference
        models_to_try = ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo", "gpt-3.5-turbo-1106"]
        
        schema_context = build_schema_context(schema)
        
        system_prompt = f"""You are an expert MySQL SQL query generator. Convert natural language to valid MySQL queries.

{schema_context}

RULES:
- Generate ONLY valid MySQL syntax
- Use appropriate JOINs for multi-table queries
- Include proper WHERE conditions and aliases
- Ensure queries are safe and optimized
- Use LIMIT for potentially large result sets
- Return ONLY the SQL query without explanations or formatting"""

        for model in models_to_try:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": f"Convert to SQL: {query}"}
                            ],
                            "temperature": 0.1,
                            "max_tokens": 800
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        sql_query = result["choices"][0]["message"]["content"].strip()
                        
                        sql_query = clean_sql_response(sql_query)
                        
                        return SQLResponse(
                            sql_query=sql_query,
                            provider="openai",
                            confidence=0.92,
                            query_type=get_query_type(sql_query),
                            explanation=f"Generated using OpenAI {model}"
                        )
                    elif response.status_code == 404:
                        # Model not found, try next one
                        continue
                    else:
                        error_detail = response.json().get("error", {}).get("message", f"OpenAI API error with {model}")
                        continue
                        
            except httpx.TimeoutException:
                continue
            except Exception as e:
                continue
        
        # If all OpenAI models fail, fallback to local
        local_result = await generate_with_local(query, context, schema)
        local_result.explanation += " (Fallback: OpenAI models unavailable)"
        return local_result
                
    except HTTPException:
        raise
    except Exception as e:
        # Fallback to local generator
        local_result = await generate_with_local(query, context, schema)
        local_result.explanation += f" (Fallback: OpenAI error - {str(e)})"
        return local_result

def build_schema_context(schema: Dict[str, Any] = None) -> str:
    """Build comprehensive database schema context for AI"""
    schema = schema or HR_DATABASE_SCHEMA
    
    schema_text = "DATABASE SCHEMA:\n\n"
    
    for table_name, table_info in schema.items():
        schema_text += f"Table: {table_name}\n"
        
        if 'columns' in table_info:
            schema_text += f"Columns: {', '.join(table_info['columns'])}\n"
        
        if 'relationships' in table_info and table_info['relationships']:
            schema_text += "Relationships:\n"
            for rel in table_info['relationships']:
                schema_text += f"  - {table_name}.{rel['foreign_key']} -> {rel['table']}.{rel['references']}\n"
        
        schema_text += "\n"
    
    return schema_text

def clean_sql_response(sql_query: str) -> str:
    """Clean and validate SQL response from AI"""
    sql_query = sql_query.replace("``````", "").strip()
    
    lines = sql_query.split('\n')
    sql_lines = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('--'):
            sql_lines.append(line)
    
    return ' '.join(sql_lines).strip()

def get_query_type(sql_query: str) -> str:
    """Determine the type of SQL query"""
    sql_lower = sql_query.lower().strip()
    if sql_lower.startswith('select'):
        return 'SELECT'
    elif sql_lower.startswith('insert'):
        return 'INSERT'
    elif sql_lower.startswith('update'):
        return 'UPDATE'
    elif sql_lower.startswith('delete'):
        return 'DELETE'
    else:
        return 'OTHER'

# API Endpoints
@router.get("/health", response_model=AIHealthStatus)
async def health_check():
    """Health check endpoint for AI services"""
    check_time = datetime.now()
    
    # Check available OpenAI models
    available_models = await check_openai_models()
    
    return AIHealthStatus(
        local_available=True,
        ollama_available=False,
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        services_status={
            "local": {
                "status": "available", 
                "description": "Enhanced rule-based SQL generator with 25+ patterns",
                "patterns": 25
            },
            "ollama": {
                "status": "not_installed", 
                "description": "Ollama not installed"
            },
            "openai": {
                "status": "configured" if os.getenv("OPENAI_API_KEY") else "not_configured",
                "available_models": available_models,
                "description": f"OpenAI configured with {len(available_models)} available models" if available_models else "OpenAI not configured or no models available"
            }
        },
        last_check=check_time
    )

@router.post("/generate-sql", response_model=SQLResponse)
async def generate_sql_from_natural_language(
    request: NaturalLanguageQuery,
    db: Session = Depends(get_db)
):
    """Generate SQL query from natural language using AI"""
    start_time = time.time()
    
    try:
        schema = request.database_schema or HR_DATABASE_SCHEMA
        
        if request.provider == "openai":
            result = await generate_with_openai(request.query, request.context, schema)
        elif request.provider == "ollama":
            # Ollama not implemented yet, fallback to local
            result = await generate_with_local(request.query, request.context, schema)
            result.explanation += " (Ollama not available, using local generator)"
        else:  # local or any other provider
            result = await generate_with_local(request.query, request.context, schema)
        
        processing_time = time.time() - start_time
        result.processing_time = round(processing_time, 2)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        # Final fallback to local generator
        try:
            result = await generate_with_local(request.query, request.context, schema)
            result.explanation += f" (Fallback due to error: {str(e)})"
            processing_time = time.time() - start_time
            result.processing_time = round(processing_time, 2)
            return result
        except:
            raise HTTPException(status_code=500, detail=f"All AI providers failed: {str(e)}")

@router.get("/examples")
async def get_query_examples():
    """Get example natural language queries and their SQL equivalents"""
    examples = [
        {
            "natural_language": "Show me all active employees with their email addresses",
            "sql_query": "SELECT full_name, email FROM users WHERE is_active = 1 ORDER BY full_name",
            "category": "Employee Management"
        },
        {
            "natural_language": "Get employee count by department",
            "sql_query": "SELECT ud.department, COUNT(*) as employee_count FROM users u JOIN user_details ud ON u.id = ud.user_id WHERE u.is_active = 1 GROUP BY ud.department ORDER BY employee_count DESC",
            "category": "Analytics"
        },
        {
            "natural_language": "Find all pending expense claims",
            "sql_query": "SELECT id, title, total_amount, user_id, created_at FROM expense_claims WHERE status = 'pending' ORDER BY created_at DESC LIMIT 50",
            "category": "Expense Management"
        },
        {
            "natural_language": "Show employees with birthdays this month",
            "sql_query": "SELECT candidate_name, email_id, date_of_birth FROM background_check_forms WHERE MONTH(date_of_birth) = MONTH(CURDATE()) ORDER BY DAY(date_of_birth)",
            "category": "Employee Information"
        },
        {
            "natural_language": "List all available assets",
            "sql_query": "SELECT asset_name, asset_code, category, brand, model FROM assets WHERE status = 'available' ORDER BY category, asset_name LIMIT 50",
            "category": "Asset Management"
        }
    ]
    
    return {
        "examples": examples,
        "total_examples": len(examples),
        "categories": list(set(example["category"] for example in examples))
    }

@router.get("/schema")
async def get_database_schema():
    """Get the current database schema for AI context"""
    return {
        "schema": HR_DATABASE_SCHEMA,
        "tables": list(HR_DATABASE_SCHEMA.keys()),
        "total_tables": len(HR_DATABASE_SCHEMA),
        "description": "HR Management System Database Schema"
    }

@router.post("/validate-sql", response_model=QueryValidation)
async def validate_sql_query(
    sql_query: str,
    db: Session = Depends(get_db)
):
    """Validate SQL query syntax and provide suggestions"""
    try:
        sql_lower = sql_query.lower().strip()
        
        validation_result = QueryValidation(is_valid=True)
        suggestions = []
        
        if not sql_lower:
            validation_result.is_valid = False
            validation_result.error_message = "Empty SQL query"
            return validation_result
        
        # Check for dangerous operations
        dangerous_keywords = ['drop', 'truncate', 'delete from', 'update']
        if any(keyword in sql_lower for keyword in dangerous_keywords):
            suggestions.append("Query contains potentially dangerous operations")
        
        # Check for missing LIMIT in SELECT statements
        if sql_lower.startswith('select') and 'limit' not in sql_lower and 'count(' not in sql_lower:
            suggestions.append("Consider adding LIMIT clause for better performance")
        
        # Check for proper JOIN syntax
        if 'join' in sql_lower and 'on' not in sql_lower:
            validation_result.is_valid = False
            validation_result.error_message = "JOIN statement missing ON condition"
            return validation_result
        
        validation_result.suggestions = suggestions if suggestions else None
        
        return validation_result
        
    except Exception as e:
        return QueryValidation(
            is_valid=False,
            error_message=f"Validation error: {str(e)}"
        )
