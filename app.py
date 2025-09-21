import os
import google.generativeai as genai
import mimetypes
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image
import io
from whitenoise import WhiteNoise # <--- ADDED

# Load environment variables from .env file
load_dotenv()
app = Flask(__name__)
# ADDED THIS LINE TO ACTIVATE WHITENOISE
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/') 
CORS(app) 

# --- Configure Generative AI ---
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    print("🔴 FATAL ERROR: GEMINI_API_KEY not found. Make sure you have set it in your .env file.")
    exit()

# --- A dictionary to hold all our prompts ---
ANALYSIS_PROMPTS = {
    "swot": {
        "title": "SWOT Analysis",
        "prompt": """Act as a senior business strategist. Your sole task is to perform a comprehensive SWOT analysis based on the provided documents and/or images. Synthesize all the information provided. Present the output in clear, well-structured Markdown.
- **Strengths:** Identify clear winners from the data. What is the business doing well?
- **Weaknesses:** Identify underperforming areas. Where are the vulnerabilities?
- **Opportunities:** What growth avenues can be inferred?
- **Threats:** What are the risks? (e.g., over-reliance on a single product)."""
    },
    "future": {
        "title": "Future Planning",
        "prompt": """Act as a growth consultant. Based on all the provided documents and/or images, create a "Future Planning" report in Markdown. Your report should contain 3 to 5 concrete, actionable recommendations for the next quarter. Focus on product, marketing, and operational strategy."""
    },
    "financial": {
        "title": "Financial Planning",
        "prompt": """Act as a financial analyst. Based on all the provided documents and/or images, create a "Financial Planning" report in Markdown. Focus exclusively on financial insights like revenue drivers, pricing analysis, and profit maximization strategies."""
    }
}

# --- Main Page Route ---
@app.route('/')
def index():
    return render_template('index.html')

# --- Dynamic Route for all Analysis Pages ---
@app.route('/analysis/<analysis_type>')
def analysis_page(analysis_type):
    config = ANALYSIS_PROMPTS.get(analysis_type)
    if not config:
        return "Analysis type not found", 404
    
    return render_template('analysis.html', 
                           page_title=config['title'], 
                           analysis_type=analysis_type)

# --- SINGLE API Endpoint for AI Generation ---
@app.route('/api/generate', methods=['POST'])
def generate_analysis():
    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        return jsonify({"error": "No files selected."}), 400

    analysis_type = request.form.get('analysis_type')
    user_context = request.form.get('context', '')

    prompt_template = ANALYSIS_PROMPTS.get(analysis_type, {}).get('prompt')
    if not prompt_template:
        return jsonify({"error": "Invalid analysis type specified."}), 400

    try:
        model_input = []
        
        for file in files:
            file_bytes = file.read()
            mime_type = file.mimetype

            if mime_type in ['image/jpeg', 'image/png']:
                img = Image.open(io.BytesIO(file_bytes))
                model_input.append(img)
            
            elif mime_type == 'application/pdf':
                doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
                extracted_text = "".join(page.get_text() for page in doc)
                doc.close()
                model_input.append(f"\n--- Content from {file.filename} ---\n{extracted_text}")

            else: # Assume text file
                extracted_text = file_bytes.decode('utf-8')
                model_input.append(f"\n--- Content from {file.filename} ---\n{extracted_text}")
        
        full_prompt = f"{prompt_template}\n\nAdditional context from the user: '{user_context}'\n\nPlease analyze the following content from all the uploaded files:"
        model_input.insert(0, full_prompt)

        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content(model_input)
        
        return jsonify({"analysis_result": response.text})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": f"Failed to analyze data. Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)