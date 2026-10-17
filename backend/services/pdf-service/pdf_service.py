"""
ZELIA PDF Service
Generates filled PDF forms from templates using applicant data.
"""
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from io import BytesIO
import os
from datetime import datetime
from minio import Minio
from minio.error import S3Error

# PDF generation libraries
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch, cm

app = FastAPI(
    title="ZELIA PDF Service",
    version="1.0.0",
    description="Template-based PDF form generation"
)

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "zelia-pdfs")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

_minio_client = None

def get_minio_client():
    global _minio_client
    if _minio_client is None:
        try:
            _minio_client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            if not _minio_client.bucket_exists(MINIO_BUCKET):
                _minio_client.make_bucket(MINIO_BUCKET)
        except Exception as e:
            print(f"MinIO connection failed: {e}")
            return None
    return _minio_client

# Pydantic Models
class FieldMapping(BaseModel):
    pdf_field: str
    data_path: str
    label: Optional[str] = None
    format: Optional[str] = None  # date, currency, uppercase

class TemplateConfig(BaseModel):
    template_id: str
    scheme_id: str
    title: str
    fields: List[FieldMapping]

class GeneratePDFRequest(BaseModel):
    scheme_id: str
    applicant_data: Dict[str, Any]
    template_id: Optional[str] = None

class GeneratePDFResponse(BaseModel):
    success: bool
    pdf_uri: Optional[str] = None
    message: str
    generated_at: str

# Pre-defined template configurations
TEMPLATE_CONFIGS = {
    "widow_pension": TemplateConfig(
        template_id="widow_pension_v1",
        scheme_id="widow_pension",
        title="Widow Pension Application Form",
        fields=[
            FieldMapping(pdf_field="applicant_name", data_path="name", label="Applicant Name"),
            FieldMapping(pdf_field="father_name", data_path="father_name", label="Father's Name"),
            FieldMapping(pdf_field="husband_name", data_path="husband_name", label="Husband's Name"),
            FieldMapping(pdf_field="date_of_birth", data_path="date_of_birth", label="Date of Birth", format="date"),
            FieldMapping(pdf_field="age", data_path="age", label="Age"),
            FieldMapping(pdf_field="address", data_path="address", label="Address"),
            FieldMapping(pdf_field="aadhar_number", data_path="aadhar", label="Aadhar Number"),
            FieldMapping(pdf_field="bank_account", data_path="bank_account", label="Bank Account"),
            FieldMapping(pdf_field="income", data_path="monthly_income", label="Monthly Income", format="currency"),
        ]
    ),
    "old_age_pension": TemplateConfig(
        template_id="old_age_pension_v1",
        scheme_id="old_age_pension",
        title="Old Age Pension Application Form",
        fields=[
            FieldMapping(pdf_field="applicant_name", data_path="name", label="Applicant Name"),
            FieldMapping(pdf_field="date_of_birth", data_path="date_of_birth", label="Date of Birth", format="date"),
            FieldMapping(pdf_field="age", data_path="age", label="Age"),
            FieldMapping(pdf_field="address", data_path="address", label="Address"),
            FieldMapping(pdf_field="aadhar_number", data_path="aadhar", label="Aadhar Number"),
            FieldMapping(pdf_field="bank_account", data_path="bank_account", label="Bank Account"),
            FieldMapping(pdf_field="income", data_path="monthly_income", label="Monthly Income", format="currency"),
        ]
    ),
    "disability_pension": TemplateConfig(
        template_id="disability_pension_v1",
        scheme_id="disability_pension",
        title="Disability Pension Application Form",
        fields=[
            FieldMapping(pdf_field="applicant_name", data_path="name", label="Applicant Name"),
            FieldMapping(pdf_field="disability_type", data_path="disability_type", label="Type of Disability"),
            FieldMapping(pdf_field="disability_percentage", data_path="disability_percentage", label="Disability %"),
            FieldMapping(pdf_field="date_of_birth", data_path="date_of_birth", label="Date of Birth", format="date"),
            FieldMapping(pdf_field="address", data_path="address", label="Address"),
            FieldMapping(pdf_field="aadhar_number", data_path="aadhar", label="Aadhar Number"),
        ]
    )
}

def get_nested_value(data: Dict, path: str) -> Any:
    """Get value from nested dict using dot notation."""
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value

def format_value(value: Any, fmt: Optional[str]) -> str:
    """Format value based on type."""
    if value is None:
        return ""
    
    if fmt == "date":
        return str(value)
    elif fmt == "currency":
        return f"₹{value:,.2f}" if isinstance(value, (int, float)) else f"₹{value}"
    elif fmt == "uppercase":
        return str(value).upper()
    else:
        return str(value)

def generate_application_pdf(config: TemplateConfig, data: Dict[str, Any]) -> BytesIO:
    """Generate a filled PDF application form."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm,
                           topMargin=1*cm, bottomMargin=1*cm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,  # Center
        spaceAfter=20
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        textColor=colors.grey
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("GOVERNMENT OF TAMIL NADU", title_style))
    elements.append(Paragraph(config.title.upper(), title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Form fields as table
    form_data = []
    for field in config.fields:
        value = get_nested_value(data, field.data_path)
        formatted = format_value(value, field.format)
        form_data.append([
            field.label or field.pdf_field,
            formatted or "_________________"
        ])
    
    table = Table(form_data, colWidths=[3*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    
    elements.append(Spacer(1, 0.5*inch))
    
    # Declaration
    declaration = """
    I hereby declare that:
    1. All information provided above is true and correct.
    2. I am not receiving any similar benefits from other schemes.
    3. I understand that providing false information may result in cancellation.
    """
    elements.append(Paragraph("DECLARATION", styles['Heading2']))
    elements.append(Paragraph(declaration, styles['Normal']))
    
    elements.append(Spacer(1, 0.5*inch))
    
    # Signatures
    sig_data = [
        ["Applicant Signature", "Date", "CHW Signature"],
        ["", "", ""],
    ]
    sig_table = Table(sig_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 30),
    ]))
    elements.append(sig_table)
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    footer = Paragraph(
        f"Application ID: {data.get('application_id', 'AUTO-GENERATED')} | "
        f"Scheme: {config.scheme_id}",
        subtitle_style
    )
    elements.append(footer)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.get("/health")
def health_check():
    minio_ok = False
    try:
        client = get_minio_client()
        if client:
            minio_ok = client.bucket_exists(MINIO_BUCKET)
    except:
        pass
    
    return {
        "status": "healthy",
        "service": "pdf-service",
        "minio_connected": minio_ok,
        "templates_loaded": len(TEMPLATE_CONFIGS)
    }

@app.get("/templates")
async def list_templates():
    """List available PDF templates."""
    return {
        "templates": [
            {
                "template_id": config.template_id,
                "scheme_id": config.scheme_id,
                "title": config.title,
                "field_count": len(config.fields)
            }
            for config in TEMPLATE_CONFIGS.values()
        ]
    }

@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get template configuration."""
    for config in TEMPLATE_CONFIGS.values():
        if config.template_id == template_id:
            return config
    raise HTTPException(404, f"Template not found: {template_id}")

@app.post("/generate", response_class=StreamingResponse)
async def generate_pdf(request: GeneratePDFRequest):
    """
    Generate a filled PDF form from template and applicant data.
    Returns the PDF file directly.
    """
    scheme_id = request.scheme_id
    
    if scheme_id not in TEMPLATE_CONFIGS:
        raise HTTPException(404, f"No template for scheme: {scheme_id}")
    
    config = TEMPLATE_CONFIGS[scheme_id]
    
    try:
        pdf_buffer = generate_application_pdf(config, request.applicant_data)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{scheme_id}_application.pdf"'
            }
        )
    except Exception as e:
        raise HTTPException(500, f"PDF generation failed: {str(e)}")

@app.post("/generate-and-store", response_model=GeneratePDFResponse)
async def generate_and_store_pdf(request: GeneratePDFRequest):
    """
    Generate PDF and store in MinIO.
    Returns the MinIO URI.
    """
    scheme_id = request.scheme_id
    
    if scheme_id not in TEMPLATE_CONFIGS:
        raise HTTPException(404, f"No template for scheme: {scheme_id}")
    
    config = TEMPLATE_CONFIGS[scheme_id]
    
    try:
        pdf_buffer = generate_application_pdf(config, request.applicant_data)
        
        # Upload to MinIO
        client = get_minio_client()
        if not client:
            raise HTTPException(503, "MinIO not available")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"{scheme_id}/{timestamp}_application.pdf"
        
        pdf_buffer.seek(0)
        client.put_object(
            MINIO_BUCKET,
            object_name,
            pdf_buffer,
            length=pdf_buffer.getbuffer().nbytes,
            content_type="application/pdf"
        )
        
        pdf_uri = f"minio://{MINIO_BUCKET}/{object_name}"
        
        return GeneratePDFResponse(
            success=True,
            pdf_uri=pdf_uri,
            message=f"PDF generated and stored successfully",
            generated_at=datetime.utcnow().isoformat()
        )
        
    except S3Error as e:
        raise HTTPException(500, f"MinIO error: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"PDF generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
