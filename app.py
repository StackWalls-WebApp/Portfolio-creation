from flask import Flask, request
from flask_cors import CORS
from config import Config
from db import Database
from services import extract_text_from_pdf_url, map_services_and_tools, generate_portfolio
from utils import error_response, success_response, setup_logging
import logging
import json
import re
from bson import ObjectId  # Ensure ObjectId is imported

app = Flask(__name__)
CORS(app)
setup_logging()

# Validate configuration on startup
try:
    Config.validate()
except ValueError as ve:
    logging.error(f"Configuration Error: {ve}")
    exit(1)

db = Database()

def validate_user_data(user, freelancer):
    if user:
        required_user_fields = ['first_name', 'last_name', 'github_profile', 'profile_photo']
        for field in required_user_fields:
            if field not in user:
                logging.warning(f"User data missing field: {field}")
    if freelancer:
        required_freelancer_fields = ['name', 'work_description', 'portfolio_website', 'skills', 'tools']
        for field in required_freelancer_fields:
            if field not in freelancer:
                logging.warning(f"Freelancer data missing field: {field}")

@app.route('/generate_portfolio', methods=['POST'])
def generate_portfolio_api():
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return error_response("Missing 'user_id' in request data.", 400)
        
        user_id = data['user_id'].strip()
        if not user_id:
            return error_response("Empty 'user_id' provided.", 400)
        
        # Validate user_id format
        if not ObjectId.is_valid(user_id):
            return error_response("Invalid 'user_id' format.", 400)

        # Fetch user and freelancer data
        freelancer = db.get_freelancer(user_id)
        user = db.get_user(user_id)

        if not freelancer and not user:
            return error_response("User not found.", 404)

        # Validate fetched data
        validate_user_data(user, freelancer)

        # Extract resume text if available
        resume_text = None
        if freelancer and "resume" in freelancer and isinstance(freelancer["resume"], dict):
            resume_info = freelancer["resume"]
            resume_url = resume_info.get("url")
            if resume_url:
                try:
                    resume_text = extract_text_from_pdf_url(resume_url)
                except Exception as e:
                    logging.error(f"Error extracting resume text: {e}")
                    resume_text = None

        # Construct freelancer name
        freelancer_name = "N/A"
        if user:
            first_name = user.get("first_name", "").strip()
            last_name = user.get("last_name", "").strip()
            full_name = (first_name + " " + last_name).strip()
            if full_name:
                freelancer_name = full_name
        if (freelancer_name == "N/A" or not freelancer_name) and freelancer:
            freelancer_name = freelancer.get("name", "N/A")

        # Safeguard the 'work_description' processing
        about = ""
        if freelancer and "work_description" in freelancer:
            work_description = freelancer["work_description"]
            if isinstance(work_description, str):
                about = re.sub(r"<.*?>", "", work_description).strip()
            else:
                logging.warning(f"'work_description' is not a string: {work_description}")
                about = ""

        # Extract other details
        github_link = user.get("github_profile") if user else None
        portfolio_website = freelancer.get("portfolio_website") if freelancer else ""
        portfolio_website = portfolio_website or ""  # Ensure string
        project_links = freelancer.get("project_links") if freelancer else ""
        project_links = project_links or ""  # Ensure string
        linkedin_link = freelancer.get("linkedIn_profile") if freelancer else None

        behance_link = portfolio_website if "behance.net" in portfolio_website else None
        dribbble_link = project_links if "dribbble.com" in project_links else None
        portfolio_link = portfolio_website if portfolio_website.strip() and not behance_link and not dribbble_link else None

        freelancer_skills = freelancer.get("skills", []) if freelancer else []
        freelancer_tools = freelancer.get("tools", []) if freelancer else []
        combined_skills = freelancer_skills + freelancer_tools
        matched_services, matched_tools = map_services_and_tools(combined_skills)

        profile_photo = user.get("profile_photo") if user and "profile_photo" in user else None
        if not profile_photo and freelancer and "profile_photo" in freelancer:
            profile_photo = freelancer["profile_photo"]

        # Prepare data for AI
        portfolio_data = {
            "full_name": freelancer_name,
            "about": about,
            "github_link": github_link,
            "behance_link": behance_link,
            "dribbble_link": dribbble_link,
            "portfolio_link": portfolio_link,
            "linkedin_link": linkedin_link,
            "profile_photo": profile_photo,
            "services": matched_services,
            "tools": matched_tools
        }

        # Generate portfolio using AI
        portfolio_json = generate_portfolio(portfolio_data, resume_text)

        return success_response(portfolio_json)
    
    except ValueError as ve:
        logging.error(f"ValueError: {ve}")
        return error_response(str(ve), 400)
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        return error_response("Internal Server Error.", 500)
    
    finally:
        pass  # Optionally, perform any cleanup here

@app.errorhandler(404)
def not_found(e):
    return error_response("Endpoint not found.", 404)

@app.errorhandler(405)
def method_not_allowed(e):
    return error_response("Method not allowed.", 405)

@app.errorhandler(500)
def internal_error(e):
    return error_response("Internal server error.", 500)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
