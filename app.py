# app.py
import os
import json
import re
import google.generativeai as genai
import mimetypes
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image
import io
from whitenoise import WhiteNoise

load_dotenv()
app = Flask(__name__)
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')
CORS(app)

api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("🔴 Warning: GEMINI_API_KEY not found. API calls will fail.")

# --- SPECIFIC PROMPTS FOR EACH ANALYSIS TYPE ---
PLANNING_PROMPTS = {
    "swot": """
Act as a senior business strategist. First, perform a detailed SWOT analysis based on the provided documents. The analysis should be in Markdown and include at least 3-5 bullet points for each category (Strengths, Weaknesses, Opportunities, Threats).

After the text analysis, add the separator '---CHART_PLAN---'.

Next, propose a JSON array of 2-3 charts to visualize the SWOT findings. For each chart, provide a 'title' and a 'prompt'. A good idea would be a bar chart counting the points in each category, and perhaps a radar chart to show the balance of the four categories.
""",
    "financial": """
Act as an expert financial analyst. First, conduct a thorough financial analysis based on the provided documents (e.g., balance sheets, income statements). The analysis in Markdown should cover key areas like Revenue, Profitability, Liquidity, and Key Financial Ratios.

After the text analysis, add the separator '---CHART_PLAN---'.

Next, propose a JSON array of 3-4 highly relevant financial charts. For each chart, provide a 'title' and a 'prompt'. Examples include a pie chart for 'Revenue Composition', a bar chart for 'Profitability Trend (e.g., Gross vs. Net Profit)', and a line chart for 'Quarterly Revenue Growth'.
""",
    "future": """
Act as a forward-thinking growth consultant. First, create a "Future Planning" report in Markdown based on the provided documents. This report should outline 3-5 concrete, actionable strategic recommendations for the next business quarter, focusing on product, marketing, and operations.

After the text analysis, add the separator '---CHART_PLAN---'.

Next, propose a JSON array of 2-3 charts to support your recommendations. For each chart, provide a 'title' and a 'prompt'. Good ideas include a doughnut chart showing the 'Impact vs. Effort' for your recommendations, or a timeline/roadmap visualization.
"""
}

CHART_GENERATION_PROMPT_TEMPLATE = """
Your sole task is to generate a valid JSON object for a Chart.js chart based on the user's prompt and the provided data.
The user's prompt is: '{chart_prompt}'.
IMPORTANT: You MUST use one of the following chart types: 'bar', 'line', 'pie', 'doughnut', 'polarArea', or 'radar'.
Do NOT output any text, explanation, or markdown formatting. Only output the raw JSON object.
"""

CHART_EXPLANATION_PROMPT_TEMPLATE = """
You are an expert data analyst. Based on the provided documents and the data from the charts, your task is to explain what the charts are showing.
Provide a clear, concise, and insightful explanation for the charts in Markdown. Explain the key takeaways and what the data implies.
The data for the charts is as follows:
{charts_data}
"""

def process_files(files):
    file_contents = []
    for file in files:
        file_bytes = file.read()
        file.seek(0)
        img_or_text = None
        mime_type = file.mimetype
        if mime_type in ['image/jpeg', 'image/png']:
            img_or_text = Image.open(io.BytesIO(file_bytes))
        elif mime_type == 'application/pdf':
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            img_or_text = "".join(page.get_text() for page in doc)
            doc.close()
        else:
            img_or_text = file_bytes.decode('utf-8')
        file_contents.append(img_or_text)
    return file_contents

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analysis/<analysis_type>')
def analysis_page(analysis_type):
    titles = {"swot": "SWOT Analysis", "future": "Future Planning", "financial": "Financial Planning"}
    page_title = titles.get(analysis_type, "Business Analysis")
    return render_template('analysis.html', page_title=page_title, analysis_type=analysis_type)

@app.route('/api/generate', methods=['POST'])
def generate_analysis():
    if not api_key: return jsonify({"error": "API key not configured."}), 500
    files = request.files.getlist('files[]')
    if not files or files[0].filename == '': return jsonify({"error": "No files selected."}), 400

    analysis_type = request.form.get('analysis_type')
    planning_prompt = PLANNING_PROMPTS.get(analysis_type)
    if not planning_prompt: return jsonify({"error": "Invalid analysis type."}), 400
    
    try:
        model_input = process_files(files)
        model_input.insert(0, planning_prompt)
        
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        planning_response = model.generate_content(model_input)
        
        text_report, chart_plan = "", []
        if '---CHART_PLAN---' in planning_response.text:
            parts = planning_response.text.split('---CHART_PLAN---', 1)
            text_report = parts[0].strip()
            
            # --- THIS IS THE FINAL, ROBUST FIX ---
            # It finds the array (from '[' to ']') and ignores any mistakes around it.
            match = re.search(r'\[.*\]', parts[1], re.DOTALL)
            if match:
                json_string = match.group(0)
                try:
                    chart_plan = json.loads(json_string)
                except json.JSONDecodeError:
                    print("Error: Failed to parse the extracted JSON array from the AI plan.")
                    text_report = planning_response.text # Fallback
            else:
                text_report = planning_response.text # Fallback
        else:
            text_report = planning_response.text

        charts_data = []
        if chart_plan:
            file_contents_for_charts = process_files(files)
            for chart_request in chart_plan:
                try:
                    chart_prompt = CHART_GENERATION_PROMPT_TEMPLATE.format(chart_prompt=chart_request['prompt'])
                    chart_model_input = file_contents_for_charts + [chart_prompt]
                    chart_response = model.generate_content(chart_model_input)
                    match = re.search(r'\{.*\}', chart_response.text, re.DOTALL)
                    if match:
                        json_string = match.group(0)
                        chart_data = json.loads(json_string)
                        chart_data['title'] = chart_request.get('title', 'Chart')
                        charts_data.append(chart_data)
                except Exception as chart_err: 
                    print(f"Skipping chart due to error: {chart_err}")
        
        return jsonify({"analysis_result": text_report, "charts_data": charts_data})
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": f"Failed to analyze data. Error: {str(e)}"}), 500

@app.route('/api/explain_charts', methods=['POST'])
def explain_charts():
    if not api_key: return jsonify({"error": "API key not configured."}), 500
    files = request.files.getlist('files[]')
    charts_data_str = request.form.get('charts_data')
    if not files or not charts_data_str: return jsonify({"error": "Files and chart data are required."}), 400

    try:
        model_input = process_files(files)
        prompt = CHART_EXPLANATION_PROMPT_TEMPLATE.format(charts_data=charts_data_str)
        model_input.insert(0, prompt)
        
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content(model_input)
        
        return jsonify({"explanation": response.text})
    except Exception as e:
        print(f"An error occurred during chart explanation: {e}")
        return jsonify({"error": f"Failed to explain charts. Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)