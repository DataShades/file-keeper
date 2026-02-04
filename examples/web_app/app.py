"""File Upload Web Application Example.

This example demonstrates how to use file-keeper in a web application with Flask.
It shows file uploads, storage management, and security best practices.
"""

import os

from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename

import file_keeper as fk
from file_keeper import exc

app = Flask(__name__)

# Initialize storage - in a real app, this would come from config
STORAGE_TYPE = os.getenv('STORAGE_TYPE', 'fs')  # 'fs', 'memory', 's3', etc.

if STORAGE_TYPE == 'memory':
    # Use memory storage for testing
    storage = fk.make_storage("web_app", {
        "type": "file_keeper:memory"
    })
elif STORAGE_TYPE == 'fs':
    # Use filesystem storage for production
    storage = fk.make_storage("web_app", {
        "type": "file_keeper:fs",
        "path": os.getenv('STORAGE_PATH', './uploads'),
        "initialize": True
    })
else:
    raise ValueError(f"Unsupported storage type: {STORAGE_TYPE}")

# Define allowed file types
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'
}
ALLOWED_MIME_TYPES = [
    'text/plain',
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/gif',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_mime_type(content_type):
    """Check if MIME type is allowed."""
    return content_type in ALLOWED_MIME_TYPES

def validate_file_size(upload, max_size_mb=10):
    """Validate file size."""
    return upload.size <= (max_size_mb * 1024 * 1024)

def secure_filename_custom(filename):
    """Additional security validation for filename."""
    # Use werkzeug's secure_filename for basic sanitization
    secure_name = secure_filename(filename)

    # Additional checks
    if not secure_name or secure_name in ('.', '..'):
        return None

    return secure_name

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload."""
    try:
        # Check if file was sent
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400

        # Secure filename
        secure_name = secure_filename_custom(file.filename)
        if not secure_name:
            return jsonify({'error': 'Invalid filename'}), 400

        # Create upload object
        upload = fk.make_upload(file)

        # Validate file size
        if not validate_file_size(upload, max_size_mb=10):
            return jsonify({'error': 'File too large'}), 400

        # Validate MIME type
        if not allowed_mime_type(upload.content_type):
            return jsonify({'error': 'File type not allowed'}), 400

        # Upload file
        file_info = storage.upload(secure_name, upload)

        return jsonify({
            'success': True,
            'location': file_info.location,
            'size': file_info.size,
            'content_type': file_info.content_type,
            'hash': file_info.hash
        }), 201

    except exc.FilesError as e:
        return jsonify({'error': f'File operation failed: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/files', methods=['GET'])
def list_files():
    """List all uploaded files."""
    try:
        if not storage.supports(fk.Capability.SCAN):
            return jsonify({'error': 'Listing files not supported'}), 400

        files = []
        for location in storage.scan():
            try:
                file_info = storage.analyze(location)
                files.append({
                    'location': file_info.location,
                    'size': file_info.size,
                    'content_type': file_info.content_type,
                    'hash': file_info.hash
                })
            except exc.MissingFileError:
                # File disappeared between scan and analyze
                continue

        return jsonify({'files': files}), 200

    except exc.FilesError as e:
        return jsonify({'error': f'File operation failed: {str(e)}'}), 500

@app.route('/file/<path:filename>', methods=['GET'])
def get_file(filename):
    """Download a file."""
    try:
        # Find the file in storage
        available_files = list(storage.scan())
        if filename not in available_files:
            return jsonify({'error': 'File not found'}), 404

        # Get file info
        file_info = storage.analyze(filename)

        # Get file content
        content = storage.content(file_info)

        # Determine content type
        content_type = file_info.content_type or 'application/octet-stream'

        # Send file
        from io import BytesIO
        buffer = BytesIO(content)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype=content_type,
            as_attachment=True,
            download_name=file_info.location
        )

    except exc.MissingFileError:
        return jsonify({'error': 'File not found'}), 404
    except exc.FilesError as e:
        return jsonify({'error': f'File operation failed: {str(e)}'}), 500

@app.route('/file/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a file."""
    try:
        if not storage.supports(fk.Capability.REMOVE):
            return jsonify({'error': 'Deleting files not supported'}), 400

        # Find the file in storage
        available_files = list(storage.scan())
        if filename not in available_files:
            return jsonify({'error': 'File not found'}), 404

        # Get file info
        file_info = storage.analyze(filename)

        # Remove file
        success = storage.remove(file_info)

        if success:
            return jsonify({'success': True}), 200
        return jsonify({'error': 'Failed to delete file'}), 500

    except exc.MissingFileError:
        return jsonify({'error': 'File not found'}), 404
    except exc.FilesError as e:
        return jsonify({'error': f'File operation failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Test basic storage functionality
        test_upload = fk.make_upload(b"health check")
        test_info = storage.upload("health_test.txt", test_upload)

        # Clean up
        if storage.supports(fk.Capability.REMOVE):
            storage.remove(test_info)

        return jsonify({
            'status': 'healthy',
            'storage_type': STORAGE_TYPE,
            'capabilities': str(storage.capabilities)
        }), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0', port=5000)
