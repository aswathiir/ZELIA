from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import base64
import os
import traceback

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

app = Flask(__name__)
CORS(app)

# MinIO Configuration
S3_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'http://minio:9000')
S3_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
S3_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
S3_REGION = os.environ.get('AWS_REGION', 'us-east-1')

s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
    config=Config(signature_version='s3v4')
)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'form-filler'})

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload base64 encoded file to MinIO
    Expects JSON: { "bucket": "...", "filename": "...", "document_data": "base64..." }
    """
    try:
        data = request.json
        bucket_name = data.get('bucket', 'completed-forms')
        filename = data.get('filename')
        document_base64 = data.get('document_data')
        
        if not filename or not document_base64:
            return jsonify({'error': 'Missing filename or document_data'}), 400
            
        # Decode base64
        file_data = base64.b64decode(document_base64)
        file_stream = io.BytesIO(file_data)
        
        # Ensure bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except ClientError:
            # Create bucket if it doesn't exist
            s3_client.create_bucket(Bucket=bucket_name)
            
        # Upload
        s3_client.upload_fileobj(
            file_stream,
            bucket_name,
            filename,
            ExtraArgs={'ContentType': 'application/pdf'}
        )
        
        # Generate URL (internal)
        storage_path = f"{bucket_name}/{filename}"
        
        return jsonify({
            'status': 'success',
            'storage_path': storage_path,
            'message': f'Successfully uploaded to {bucket_name}/{filename}'
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/fill-form', methods=['POST'])
def fill_form():
    """
    Fill PDF form fields with user data.
    Supports multi-page templates via 'page' attribute on fields (1-based).
    Supports template_path for local filesystem PDFs.
    """
    try:
        data = request.json
        
        form_fields = data.get('form_fields', [])
        field_values = data.get('field_values', {})
        document_base64 = data.get('document_base64')
        storage_path = data.get('storage_path')
        template_path = data.get('template_path')
        
        # --- Load the base/template PDF ---
        existing_pdf = None
        
        # Priority 1: Local template_path
        if template_path and os.path.exists(template_path):
            print(f"DEBUG: Loading template from local path: {template_path}")
            existing_pdf = PdfReader(template_path)
            print(f"DEBUG: Template pages: {len(existing_pdf.pages)}")
        
        # Priority 2: Base64 document
        elif document_base64 and document_base64 != "filesystem-v2":
            print(f"DEBUG: Received document_base64 length: {len(document_base64)}")
            try:
                packet_base = io.BytesIO(base64.b64decode(document_base64))
                existing_pdf = PdfReader(packet_base)
                print(f"DEBUG: PDF Pages: {len(existing_pdf.pages)}")
            except Exception as e:
                print(f"ERROR: Failed to read provided PDF base64: {e}")
                raise ValueError(f"Invalid PDF data provided: {str(e)}")
        
        # Priority 3: Fetch from MinIO
        elif storage_path:
            print(f"DEBUG: Fetching from MinIO path: {storage_path}")
            try:
                if '/' in storage_path:
                    bucket, key = storage_path.split('/', 1)
                else:
                    bucket = "forms" 
                    key = storage_path
                
                response = s3_client.get_object(Bucket=bucket, Key=key)
                file_stream = io.BytesIO(response['Body'].read())
                existing_pdf = PdfReader(file_stream)
                print(f"DEBUG: Downloaded PDF from MinIO. Pages: {len(existing_pdf.pages)}")
            except Exception as e:
                print(f"ERROR: Failed to download from MinIO: {e}")
                try:
                    print(f"DEBUG: Retrying with bucket=forms key={storage_path}")
                    response = s3_client.get_object(Bucket='forms', Key=storage_path)
                    file_stream = io.BytesIO(response['Body'].read())
                    existing_pdf = PdfReader(file_stream)
                except Exception as e2:
                    raise ValueError(f"Could not fetch PDF from MinIO: {str(e)}")

        # Fallback: blank placeholder PDF
        if existing_pdf is None:
            packet_simple = io.BytesIO()
            can_simple = canvas.Canvas(packet_simple, pagesize=letter)
            can_simple.drawString(100, 100, "Base Document (Placeholder)")
            can_simple.save()
            packet_simple.seek(0)
            existing_pdf = PdfReader(packet_simple)

        num_pages = len(existing_pdf.pages)
        page_width, page_height = letter  # 612 x 792
        
        # --- Group fields by page number ---
        fields_by_page = {}  # page_num (1-based) -> [(field, value)]
        fields_filled = 0
        fields_empty = []
        
        for field in form_fields:
            field_id = field.get('field_id')
            value = field_values.get(field_id, '')
            pg = field.get('page', 1)  # Default to page 1
            
            if value:
                if pg not in fields_by_page:
                    fields_by_page[pg] = []
                fields_by_page[pg].append((field, str(value)))
                fields_filled += 1
            else:
                fields_empty.append(field_id)
        
        # --- Create per-page overlay canvases and merge ---
        output = PdfWriter()
        
        for page_idx in range(num_pages):
            page = existing_pdf.pages[page_idx]
            page_num = page_idx + 1  # 1-based
            
            page_fields = fields_by_page.get(page_num, [])
            
            if page_fields:
                # Create overlay for this page
                overlay_buf = io.BytesIO()
                overlay_can = canvas.Canvas(overlay_buf, pagesize=letter)
                
                for field, value in page_fields:
                    # Support both bbox [x1,y1,x2,y2] and x/y coordinate formats
                    bbox = field.get('bbox')
                    if bbox:
                        x, y = bbox[0], bbox[1]
                    else:
                        x = field.get('x', 100)
                        y_top = field.get('y', 100)
                        height = field.get('height', 20)
                        # Convert top-left origin (y) to bottom-left origin for ReportLab
                        y = page_height - y_top - height
                    
                    overlay_can.setFont("Helvetica", 10)
                    overlay_can.drawString(x, y, value)
                
                overlay_can.save()
                overlay_buf.seek(0)
                overlay_pdf = PdfReader(overlay_buf)
                
                if len(overlay_pdf.pages) > 0:
                    page.merge_page(overlay_pdf.pages[0])
            
            output.add_page(page)
        
        # --- Serialize output ---
        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        
        pdf_bytes = output_stream.read()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        fill_confidence = fields_filled / len(form_fields) if form_fields else 0
        
        return jsonify({
            'status': 'success',
            'filled_document_base64': pdf_base64,
            'fields_filled': fields_filled,
            'fields_total': len(form_fields),
            'fields_empty': fields_empty,
            'fill_confidence': fill_confidence
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8013))
    app.run(host='0.0.0.0', port=port)
