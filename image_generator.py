from flask import Flask, request, render_template, send_file, jsonify
from PIL import Image
import os
import io
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024 

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file_path, width, height, target_size_kb, original_extension):
    try:
        img = Image.open(file_path)
        img = img.resize((width, height), Image.LANCZOS)
    
        target_size = target_size_kb * 1024
        output = io.BytesIO()

        img_format = original_extension.lower()
        if img_format == 'jpg':
            img_format = 'jpeg' 

        if img_format == 'jpeg':
            quality = 95
            while True:
                output.seek(0)
                output.truncate(0)
                img.save(output, format='JPEG', quality=quality)
                size = output.tell()
                if size <= target_size or quality <= 5:
                    break
                quality -= 5
        else:
            img.save(output, format='PNG')
        
        output_path = os.path.join(PROCESSED_FOLDER, f"processed_{uuid.uuid4()}.{img_format}")
        with open(output_path, 'wb') as f:
            f.write(output.getvalue())
        
        return output_path
    except Exception as e:
        raise Exception(f"Failed to process image: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html', error=None, processed_image=None, uploaded_image=None)

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file format. Only JPEG and PNG are allowed'}), 400
    if len(file.read()) > MAX_FILE_SIZE:
        return jsonify({'error': 'File size exceeds 10 MB'}), 400
    
    file.seek(0)  # Reset file pointer
    try:
        extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"upload_{uuid.uuid4()}.{extension}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        return jsonify({'uploaded_image': f"/{file_path}"})
    except Exception as e:
        return jsonify({'error': f'Error uploading image: {str(e)}'}), 500

@app.route('/process', methods=['POST'])
def process_image_route():
    error = None
    processed_image = None
    
    try:
        uploaded_image = request.form.get('uploaded_image')
        width = int(request.form.get('width', 0))
        height = int(request.form.get('height', 0))
        target_size = int(request.form.get('target_size', 0))
        
        if not uploaded_image:
            error = 'No image uploaded for processing'
        elif width <= 0 or height <= 0 or target_size <= 0:
            error = 'Invalid parameters. Width, height, and target size must be positive'
        else:
            file_path = uploaded_image.lstrip('/')
            if not os.path.exists(file_path):
                error = 'Uploaded image not found'
            else:
                extension = file_path.rsplit('.', 1)[1].lower()
                processed_path = process_image(file_path, width, height, target_size, extension)
                processed_image = f"/{processed_path}"
    
    except ValueError:
        error = 'Invalid input parameters. Please enter valid numbers'
    except Exception as e:
        error = str(e)
    
    return render_template('index.html', error=error, processed_image=processed_image, uploaded_image=uploaded_image)

@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename))

@app.route('/processed/<path:filename>')
def download_file(filename):
    return send_file(os.path.join(PROCESSED_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    import webbrowser
    webbrowser.open('http://localhost:5000')  # Открывает браузер
    app.run(host='0.0.0.0', port=5000)