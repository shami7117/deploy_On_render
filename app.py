from flask import Flask, request, render_template, send_file, session
from generate_stl import generate_stl_from_scan
import os
import uuid
import tempfile

app = Flask(__name__, static_folder='.', template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing')

# Create a temp directory for file storage
UPLOAD_FOLDER = tempfile.gettempdir()

@app.route('/')
def index():
    # Generate unique session ID if not exists
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/save', methods=['POST'])
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
def download_stl():
    user_id = session.get('user_id', str(uuid.uuid4()))
    stl_path = session.get('stl_path', os.path.join(UPLOAD_FOLDER, f'generated_model_{user_id}.stl'))
    
    if os.path.exists(stl_path):
        return send_file(stl_path, as_attachment=True, download_name="generated_model.stl")
    else:
        return "STL file not found. Please process data first.", 404

# Port configuration for Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)