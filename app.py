import boto3
import json
import os
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# Configure allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           

def extract_text_from_file(file_path):
    """
    Extract text from a given file based on its extension.
    Supports .txt, .pdf, and .docx files.
    """
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    elif ext == '.pdf':
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"pdfplumber failed to read the PDF: {e}. Trying PyPDF2...")
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                print(f"PyPDF2 also failed to read the PDF: {e}.")
    elif ext == '.docx':
        try:
            from docx2python import docx2python
            doc_result = docx2python(file_path)
            text = doc_result.text
            if isinstance(text, bytes):
                text = text.decode('utf-8')
        except Exception as e:
            print(f"Failed to read DOCX file: {e}.")
    else:
        raise ValueError("Unsupported file format. Please provide a .txt, .pdf, or .docx file")
    
    return text.strip()

def test_sagemaker_endpoint(endpoint_name, region, input_payload=None, file_path=None, content_type="application/json"):
    """
    Invokes a SageMaker endpoint with the given input and returns the response.
    """
    # Initialize the SageMaker runtime client
    runtime_client = boto3.client('sagemaker-runtime', region_name=region)

    try:
        if file_path:
            # For file-based input, read the file and set the content type
            with open(file_path, 'rb') as file:
                response = runtime_client.invoke_endpoint(
                    EndpointName=endpoint_name,
                    ContentType=content_type,
                    Body=file.read()
                )
        elif input_payload:
            # For JSON input, serialize the input data to JSON
            payload = json.dumps(input_payload)
            response = runtime_client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType=content_type,
                Body=payload
            )
        else:
            raise ValueError("Either 'input_payload' or 'file_path' must be provided.")

        # Deserialize the response
        result = json.loads(response['Body'].read())
        return result

    except Exception as e:
        print(f"Error invoking the endpoint: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Determine whether the user submitted text or a file
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join('uploads', filename)
                
                # Create 'uploads' directory if it doesn't exist
                os.makedirs('uploads', exist_ok=True)
                
                file.save(file_path)
                
                # Determine the content type based on file extension
                ext = filename.rsplit('.', 1)[1].lower()
                if ext == 'pdf':
                    content_type = 'application/pdf'
                elif ext == 'docx':
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                else:
                    content_type = 'text/plain'
                
                # Invoke SageMaker endpoint with file input
                prediction = test_sagemaker_endpoint(
                    endpoint_name=os.getenv('ENDPOINT_NAME', 'StackWalls-recommendation-endpoint-2024-12-12-14-22-59'),
                    region=os.getenv('AWS_REGION', 'eu-north-1'),
                    file_path=file_path,
                    content_type=content_type
                )
                
                # Remove the uploaded file after processing
                os.remove(file_path)
                
                if prediction:
                    # Check if prediction is a dict with 'recommendations' key or a list
                    if isinstance(prediction, dict) and 'recommendations' in prediction:
                        recommendations = prediction.get('recommendations', [])
                    elif isinstance(prediction, list):
                        recommendations = prediction
                    else:
                        recommendations = []
                    
                    return render_template('result.html', predictions=recommendations)
                else:
                    flash("Failed to get prediction with file input.", "danger")
                    return redirect(url_for('index'))
            else:
                flash("Invalid file type. Please upload a .txt, .pdf, or .docx file.", "danger")
                return redirect(url_for('index'))
        elif 'text_input' in request.form and request.form['text_input'].strip() != '':
            text_input = request.form['text_input'].strip()
            
            # Invoke SageMaker endpoint with JSON input
            input_data = {
                "Clients": text_input
            }
            prediction = test_sagemaker_endpoint(
                endpoint_name=os.getenv('ENDPOINT_NAME', 'StackWalls-recommendation-endpoint-2024-12-12-14-22-59'),
                region=os.getenv('AWS_REGION', 'eu-north-1'),
                input_payload=input_data,
                content_type='application/json'
            )
            
            if prediction:
                # Check if prediction is a dict with 'recommendations' key or a list
                if isinstance(prediction, dict) and 'recommendations' in prediction:
                    recommendations = prediction.get('recommendations', [])
                elif isinstance(prediction, list):
                    recommendations = prediction
                else:
                    recommendations = []
                
                return render_template('result.html', predictions=recommendations)
            else:
                flash("Failed to get prediction with JSON input.", "danger")
                return redirect(url_for('index'))
        else:
            flash("Please provide either text input or upload a file.", "warning")
            return redirect(url_for('index'))
    
    return render_template('index.html')

if __name__ == '__main__':
    # Ensure the 'uploads' directory exists
    os.makedirs('uploads', exist_ok=True)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
