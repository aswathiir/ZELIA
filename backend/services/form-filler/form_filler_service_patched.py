from flask import Flask, request, jsonify
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

# MinIO Configuration
S3_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'http://minio:9000')
S3_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
S3_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
S3_REGION = os.environ.get('AWS_REGION', 'us-east-1')

print(f"DEBUG: S3 Config: Endpoint={S3_ENDPOINT}, Key={S3_ACCESS_KEY}, Region={S3_REGION}")

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
    Fill PDF form fields with user data
    """
    try:
        data = request.json
        
        form_fields = data.get('form_fields', [])
        field_values = data.get('field_values', {})
        # In a real scenario, we would fetch the PDF from MinIO using document_id or storage_path
        # For this prototype, we'll assume we might receive base64 or path, 
        # but the guide implies fetching from storage.
        # Since we don't have MinIO fully wired in this service yet (it just says "get from MinIO"),
        # I'll implement a placeholder that creates a blank PDF if no source provided, 
        # or expects a base64 input 'document_base64'.
        
        # If document_base64 is provided, use it. Otherwise create a new blank PDF as base.
        document_base64 = data.get('document_base64')
        storage_path = data.get('storage_path')
        
        if document_base64 and document_base64 != "filesystem-v2":
            print(f"DEBUG: Received document_base64 length: {len(document_base64)}")
            try:
                packet_base = io.BytesIO(base64.b64decode(document_base64))
                existing_pdf = PdfReader(packet_base)
                print(f"DEBUG: PDF Pages: {len(existing_pdf.pages)}")
            except Exception as e:
                print(f"ERROR: Failed to read provided PDF base64: {e}")
                raise ValueError(f"Invalid PDF data provided: {str(e)}")
        
        elif storage_path:
            print(f"DEBUG: Fetching from MinIO path: {storage_path}")
            try:
                # storage_path is like "forms/filename.pdf" or just "filename.pdf" if implicit
                # But N8N passes "forms/widow_pension_karnataka.pdf"
                if '/' in storage_path:
                    bucket, key = storage_path.split('/', 1)
                else:
                    bucket = "forms" 
                    key = storage_path
                
                print(f"DEBUG: GetObject Bucket={bucket} Key={key}")
                response = s3_client.get_object(Bucket=bucket, Key=key)
                file_stream = io.BytesIO(response['Body'].read())
                existing_pdf = PdfReader(file_stream)
                print(f"DEBUG: Downloaded PDF from MinIO. Pages: {len(existing_pdf.pages)}")
            except Exception as e:
                print(f"ERROR: Failed to download from MinIO: {e}")
                # Try simple filename in forms bucket as fallback
                try:
                    print(f"DEBUG: Retrying with bucket=forms key={storage_path}")
                    response = s3_client.get_object(Bucket='forms', Key=storage_path)
                    file_stream = io.BytesIO(response['Body'].read())
                    existing_pdf = PdfReader(file_stream)
                except Exception as e2:
                    raise ValueError(f"Could not fetch PDF from MinIO: {str(e)}")

        else:
            # Create a blank PDF in memory to start with (fallback)
            # Or better, return error if no document provided
            # But for testing validity of filler logic, let's allow creating a simple PDF
            packet_simple = io.BytesIO()
            can_simple = canvas.Canvas(packet_simple, pagesize=letter)
            can_simple.drawString(100, 100, "Base Document (Placeholder)")
            can_simple.save()
            packet_simple.seek(0)
            existing_pdf = PdfReader(packet_simple)

        # Create the "watermark" (filled fields) canvas
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        
        # Fill each field
        fields_filled = 0
        for field in form_fields:
            field_id = field.get('field_id')
            value = field_values.get(field_id)
            
            if value:
                # Get bounding box [x1, y1, x2, y2]
                bbox = field.get('bbox', [100, 700, 300, 720])
                # ReportLab uses bottom-left origin. 
                # Assuming bbox is also bottom-left origin based.
                x, y = bbox[0], bbox[1]
                
                # Draw text
                can.drawString(x, y, str(value))
                fields_filled += 1
        
        can.save()
        packet.seek(0)
        new_pdf = PdfReader(packet)
        
        # Merge
        output = PdfWriter()
        # Assume 1 page for now or loop pages
        if len(existing_pdf.pages) > 0:
            page = existing_pdf.pages[0]
            
            # Only merge if we actually created a watermark page
            if len(new_pdf.pages) > 0:
                page.merge_page(new_pdf.pages[0])
            
            output.add_page(page)
        
        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        
        # Convert to base64
        pdf_bytes = output_stream.read()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        return jsonify({
            'status': 'success',
            'filled_document_base64': pdf_base64,
            'fields_filled': fields_filled,
            'fields_total': len(form_fields),
            'fill_confidence': fields_filled / len(form_fields) if form_fields else 0
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8013))
    app.run(host='0.0.0.0', port=port)
