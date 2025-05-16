from flask import Flask, request, render_template, send_file, session, redirect, url_for
from generate_stl import generate_stl_from_scan
import os
import uuid
import tempfile
import csv
import io
from functools import wraps

app = Flask(__name__, static_folder='.', template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing')

# Create a temp directory for file storage
UPLOAD_FOLDER = tempfile.gettempdir()

# License validation function
def is_valid_license(key):
    # Get the license keys from environment variable
    license_csv = os.environ.get('LICENSE_KEYS', '')
    
    # If the license_csv is empty, use a default for development
    if not license_csv and app.debug:
        license_csv = "TEST123,USER456,DEMO789"
    
    # Parse the CSV content
    csv_file = io.StringIO(license_csv)
    reader = csv.reader(csv_file)
    
    # Look for the key in the CSV
    for row in reader:
        if key in row:
            return True
    
    return False

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login')
def login():
    error = request.args.get('error')
    return render_template('login.html', error=error)

@app.route('/validate-license', methods=['POST'])
def validate_license():
    license_key = request.form.get('license_key', '')
    
    if is_valid_license(license_key):
        # Generate unique session ID if not exists
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        
        # Mark as authenticated
        session['authenticated'] = True
        
        # Redirect to main page
        return redirect(url_for('index'))
    else:
        return redirect(url_for('login', error='Invalid license key. Please try again.'))

@app.route('/')
def index():
    # Check if authenticated
    if 'authenticated' not in session or not session['authenticated']:
        return redirect(url_for('login'))
    
    return render_template('index.html')

@app.route('/save', methods=['POST'])
@login_required
def save_data():
    data = request.json.get('data', '')
    
    # Use session ID to create unique filenames
    user_id = session.get('user_id', str(uuid.uuid4()))
    input_file = os.path.join(UPLOAD_FOLDER, f'serial_output_{user_id}.txt')
    
    with open(input_file, 'w') as f:
        f.write(data)
    
    # Store the filename in session for later use
    session['input_file'] = input_file
    
    return "Data saved successfully"

@app.route('/process', methods=['POST'])
@login_required
def process_data():
    user_id = session.get('user_id', str(uuid.uuid4()))
    
    # Get file paths using session ID
    input_path = session.get('input_file', os.path.join(UPLOAD_FOLDER, f'serial_output_{user_id}.txt'))
    cleaned_path = os.path.join(UPLOAD_FOLDER, f'cleaned_data_{user_id}.txt')
    stl_path = os.path.join(UPLOAD_FOLDER, f'generated_model_{user_id}.stl')
    
    # Check if input file exists
    if not os.path.exists(input_path):
        return "No data found. Please save data first.", 400
    
    # Step 1: Clean empty lines
    with open(input_path, 'r') as file:
        lines = file.readlines()
    
    cleaned_lines = [line for line in lines if line.strip()]
    
    with open(cleaned_path, 'w') as file:
        file.writelines(cleaned_lines)
    
    # Step 2: Generate STL using Python version of processScanDistance.m
    try:
        generate_stl_from_scan(cleaned_path, stl_path)
        session['stl_path'] = stl_path
        return "Scan processed and STL file generated."
    except Exception as e:
        return f"Processing failed: {e}", 500

@app.route('/download-stl')
@login_required
def download_stl():
    user_id = session.get('user_id', str(uuid.uuid4()))
    stl_path = session.get('stl_path', os.path.join(UPLOAD_FOLDER, f'generated_model_{user_id}.stl'))
    
    if os.path.exists(stl_path):
        # Check if this is a direct download (attachment) or for 3D preview
        is_attachment = 't' not in request.args
        return send_file(
            stl_path, 
            as_attachment=is_attachment, 
            download_name="generated_model.stl" if is_attachment else None
        )
    else:
        return "STL file not found. Please process data first.", 404

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Port configuration for Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)