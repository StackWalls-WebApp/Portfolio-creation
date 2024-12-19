import re
import io
import requests
import json
import logging
from PyPDF2 import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from config import Config

# Services Mapping and Tools List (as provided)
SERVICES_MAPPING = {
    "GRAPHIC DESIGNING (2D/3D)": [
        "Logos", "Business Cards", "Banners", "Brochures", "Social Media Posts",
        "Infographics (2D/3D)", "Flvers", "Posters", "Packaging Design",
        "Illustrations (2D/3D)", "Merch Design", "3D Modelling", "Animation (2D/3D)"
    ],
    # ... (rest of the services)
}

TOOLS_LIST = [
    "Adalo", "Andromo", "AppGyver", "Airtable", "ActiveCampaign", "Appian", "Appsheet",
    # ... (rest of the tools)
]

def extract_text_from_pdf_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        pdf_reader = PdfReader(io.BytesIO(response.content))
        
        text_content = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content.append(page_text)
    
        all_text = "\n".join(text_content)
        # Normalize whitespace
        all_text = re.sub(r"[ \t]+", " ", all_text)
        all_text = re.sub(r"(\r\n|\r|\n)+", "\n", all_text)
    
        lines = all_text.split("\n")
        cleaned_lines = []
        for line in lines:
            parts = line.split(" ")
            single_chars = sum(len(p) == 1 for p in parts if p.strip())
            if len(parts) > 1 and single_chars > (len(parts) / 2):
                new_line_words = []
                current_word_chars = []
                for token in parts:
                    if len(token) == 1:
                        current_word_chars.append(token)
                    else:
                        if current_word_chars:
                            new_line_words.append("".join(current_word_chars))
                            current_word_chars = []
                        new_line_words.append(token)
                if current_word_chars:
                    new_line_words.append("".join(current_word_chars))
                cleaned_lines.append(" ".join(new_line_words))
            else:
                cleaned_lines.append(line)
    
        cleaned_text = "\n".join(l.strip() for l in cleaned_lines if l.strip())
        return cleaned_text
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        raise e

def map_services_and_tools(skills):
    try:
        matched_services = []
        for category, items in SERVICES_MAPPING.items():
            category_matches = [s for s in skills if s in items]
            if category_matches:
                matched_services.append({
                    "category": category,
                    "services": category_matches
                })
        matched_tools = [t for t in skills if t in TOOLS_LIST]
        return matched_services, matched_tools
    except Exception as e:
        logging.error(f"Error mapping services and tools: {e}")
        raise e

def initialize_llm(api_key):
    try:
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            verbose=False,
            temperature=0.5,
            google_api_key=api_key
        )
    except Exception as e:
        logging.error(f"Error initializing LLM: {e}")
        raise e

def generate_portfolio(data, resume_text):
    try:
        instructions = f"""
You are an AI assistant. You have the following data about a freelancer:

Full Name: {data['full_name']}
About (raw): {data['about']}
Github link: {data.get('github_link')}
Behance link: {data.get('behance_link')}
Dribbble link: {data.get('dribbble_link')}
Portfolio link: {data.get('portfolio_link')}
LinkedIn link: {data.get('linkedin_link')}
Profile Photo: {data.get('profile_photo')}

Services (Matched from freelancer skills):
{json.dumps(data['services'], indent=2)}

Tools (Matched from freelancer tools):
{json.dumps(data['tools'], indent=2)}

Resume Text (raw):
{resume_text}

Your task:
1. Create a professional and creative portfolio in JSON format with these fields:
   - full_name
   - about: A compelling, professional, and creative narrative using all known data.
   - profile_photo (if available)
   - github_link (if present)
   - behance_link (if present)
   - dribbble_link (if present)
   - linkedin_link (if present)
   - portfolio_link (if present and not Behance or Dribbble)
   - services: array of {{ "category": "CategoryName", "services": ["service1","service2",...] }}
   - tools: array of tools (strings)
   - projects: array of {{ "title": "...", "description": ["bullet1","bullet2",...], (optional) "link":"...", (optional)"files":"..." }}
     Make each bullet point a substantial, well-structured sentence that clearly explains the work done, the context, and the value provided.
   - experience: array of {{ "title": "...", "company_name": "...", "description": ["bullet1","bullet2",...], "start_date": "MM/YYYY", "end_date": "MM/YYYY or empty if currently working" }}
     Similarly, make each bullet point more detailed and descriptive, explaining responsibilities, achievements, and the impact made.

2. Ensure no repeated fields or invalid JSON. The description arrays should contain multiple, well-structured sentences in bullet form, each providing meaningful detail.

3. Produce only a valid JSON object with no extra formatting, no code fences, and no markdown.
"""
        llm = initialize_llm(Config.GOOGLE_API_KEY)
        ai_message = llm.invoke(instructions)
        response_text = ai_message.content

        cleaned_response = response_text.strip()
        cleaned_response = re.sub(r"```[\s\S]*?```", "", cleaned_response).strip()

        parsed_json = json.loads(cleaned_response)
        return parsed_json
    except json.JSONDecodeError as je:
        logging.error(f"JSON decoding failed: {je}")
        raise je
    except Exception as e:
        logging.error(f"Error generating portfolio: {e}")
        raise e