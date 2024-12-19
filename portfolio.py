
import os
import re
import io
import json
import logging
import requests
import traceback
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from flask_cors import CORS
from langchain_google_genai import ChatGoogleGenerativeAI

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
logging.basicConfig(level=logging.ERROR)

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set.")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

# ---------------------------------------------------------
# MongoDB Connection
# ---------------------------------------------------------
try:
    client = MongoClient(MONGO_URI)
    db = client["stackwalls"]
    freelancers_collection = db["freelancers"]
    users_collection = db["users"]
    print("Data successfully loaded from MongoDB!")
except Exception as e:
    print(f"An error occurred while connecting to MongoDB: {e}")
    exit()

# ---------------------------------------------------------
# PDF Text Extraction Function
# ---------------------------------------------------------
def extract_text_from_pdf_url(url):
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

# ---------------------------------------------------------
# Gemini Initialization
# ---------------------------------------------------------
def initialize_llm(api_key):
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        verbose=False,
        temperature=0.5,
        google_api_key=api_key
    )

# ---------------------------------------------------------
# Services and Tools Mapping
# ---------------------------------------------------------
services_mapping = {
    "GRAPHIC DESIGNING (2D/3D)": [
        "Logos", "Business Cards", "Banners", "Brochures", "Social Media Posts",
        "Infographics (2D/3D)", "Flvers", "Posters", "Packaging Design",
        "Illustrations (2D/3D)", "Merch Design", "3D Modelling", "Animation (2D/3D)"
    ],
    "UI/UX DESIGNING": [
        "Mobile App UI/UX", "WebApp UI/UX", "Custom Software UI/UX"
    ],
    "NO-CODE/LOW-CODE DEVELOPMENT": [
        "Bubble", "Wordpress", "Webflow", "Shopify", "Framer", "Wix", "Notion",
        "Cardd", "Softr.io", "Glide", "Outsystems", "Retool", "AppSmith"
    ],
    "Mobile app development": [
        "Android", "IOS"
    ],
    "VIDEO EDITING (2D/3D)": [
        "Reels/Shorts", "Youtube Videos", "Marketing Videos", "Product Demos",
        "Wedding Documentary", "Film Editing"
    ],
    "DIGITAL MARKETING": [
        "SEO", "SEM", "Social Media Marketing", "Content Marketing", "Email Marketing",
        "Affiliate Marketing", "PPC ads", "Influencer marketing"
    ],
    "CONTENT WRITING": [
        "Blogs", "Copywriting", "Technical Writing", "Ghostwriting", "SEO Writing",
        "Product Descriptions", "Press Releases", "Academic Writing"
    ],
    "CUSTOM SOFTWARE DEVELOPMENT": [
        "ERP development", "CRM development", "SaaS development", "Enterprise Software",
        "Desktop Application", "Cloud-based Software"
    ],
    "AUTOMATION": [
        "Zoho", "Hubspot", "Salesforce", "Airtable", "Zapier", "Odoo", "Looker Studio"
    ],
    "PHOTOGRAPHY/VIDEOGRAPHY": [
        "Event", "Wedding", "Product", "Real Estate", "Travel",
        "Fashion", "Food", "Corporate"
    ],
    "CA/LEGAL SERVICES": [
        "Tax Consultation", "Audit Services", "Company Formation and Registration",
        "Compliance and Regulatory Services", "Legal Documentation",
        "Contract Drafting and Review", "Intellectual Property Services", "Legal Advisory",
        "Corporate Law Services"
    ],
    "WEB DEVELOPMENT": [
        "HTML/CSS/JavaScript", "React", "Next.js", "Vue.js", "Angular", "Node.js", "PHP",
        "Python", "Java/.NET", "Ruby (Ruby on Rails)", "Go (Golang)", "Scala (Play Framework)",
        "Django (Python framework)", "Spring Boot (Java framework)",
        "MEAN Stack (MongoDB, Express.js, Angular, Node.js)",
        "MERN Stack (MongoDB, Express.js, React, Node.js)",
        "LAMP Stack (Linux, Apache, MySQL, PHP)",
        "MEVN Stack (MongoDB, Express.js, Vue.js, Node.js)",
        "Django Stack (Python, Django, PostgreSQL/MySQL)",
        "Ruby on Rails (Ruby, PostgreSQL/MySQL, JavaScript)",
        "PERN Stack (PostgreSQL, Express.js, React, Node.js)"
    ]
}

tools_list = [
    "Adalo", "Andromo", "AppGyver", "Airtable", "ActiveCampaign", "Appian", "Appsheet",
    "Appy Pie", "Backendless", "Betty Blocks", "Bildr", "Bizness Apps", "Boundless",
    "Bravo Studio", "Bubble", "Bubble Pages", "BuildFire", "Carrd", "BuildBox",
    "Builderall", "Caspio", "ClickFunnels", "Coda", "Constant Contact", "Contentful",
    "Convertkit", "Creatio", "Draftbit", "Drapcode", "Drip", "Duda", "Elementor",
    "Fliplet", "Flodesk", "Flutterflow", "Formbakery", "Framer", "Freshsales",
    "GetResponse", "Glide", "Gloo", "Grapedrop", "Gravity Forms", "HubSpot",
    "Indigo.Design", "Infusionsoft (Keap)", "Integromat (now Make)", "Jellyfish",
    "Jotform", "Kajabi", "Kartra", "Klaviyo", "Knack", "Landbot", "Landen", "Leadpages",
    "Mailchimp", "Makerpad", "Marketo", "Memberstack", "Mendix", "Microsoft Power Apps",
    "Microsoft Dynamics 365", "Mobincube", "Noodl", "Morpheus", "Notion", "Odoo",
    "Ontraport", "Outfit7", "Parabola", "Pardot", "Pega", "Pipedrive", "Pixpa",
    "Plasmic", "Podio", "Pory", "Quickbase", "OutSystems", "Quixy", "Racket", "Retool",
    "Salesforce", "Salesforce Lightning", "SendinBlue", "ServiceNow", "Sheet2Site",
    "Shopify", "Shoutem", "Softr", "Squarespace", "Stacker", "Strikingly", "Substack",
    "SugarCRM", "Swoogo", "Tapkit", "Thunkable", "Tilda", "Tonkean", "Typedream",
    "Typeform", "Ukit", "Umso", "Unqork", "Versoly", "Voiceflow", "Weebly", "Webflow",
    "Weweb", "Widen Collective", "Wix", "WordPress", "Xano", "Xtensio", "Zoho",
    "Amazon Web Services (AWS)", "Apache Kafka", "Ansible", "AppDynamics",
    "Azure DevOps", "Bamboo", "BitBucket", "Chef", "CircleCI", "Datadog", "Docker",
    "Elasticsearch", "GitLab", "Google Cloud Platform (GCP)", "Grafana", "HashiCorp Terraform",
    "Jenkins", "Jira", "Kubernetes", "Logstash", "Microsoft Azure", "Nagios",
    "New Relic", "Prometheus", "Puppet", "Red Hat OpenShift", "SaltStack", "Sentry",
    "Splunk", "TeamCity", "Travis CI", "Vagrant", "VMware vSphere", "Adobe After Effects",
    "Adobe Animate", "Adobe Color", "Adobe Character Animator", "Adobe InDesign",
    "Adobe Illustrator", "Adobe Photoshop", "Adobe Premiere Pro", "Adobe XD",
    "Affinity Designer", "Apple Final Cut Pro", "Autodesk 3ds Max", "Autodesk Maya",
    "Avid Media Composer", "Axure RP", "Balsamiq", "Blackmagic DaVinci Resolve",
    "Blender", "Camtasia", "Canva", "Cinema 4D", "Coolors", "CorelDRAW", "Figma",
    "Filmora", "FontForge", "Gravit Designer", "Houdini", "iMovie", "Inkscape",
    "InVision", "Lightworks", "Marvel", "Nuke", "Mockplus", "OpenShot", "Proto.io",
    "ProtoPie", "Sketch", "SketchUp", "Sony Vegas Pro", "Toon Boom Harmony", "UXPin",
    "Zeplin", "ZBrush", "LAMP (Linux, Apache, MySQL, PHP)", "MEAN (MongoDB, Express.js, Angular, Node.js)",
    "MERN (MongoDB, Express.js, React, Node.js)", "JAMstack (JavaScript, APIs, Markup)",
    "Ruby on Rails", "Django", "ASP.NET Core", "Spring Boot", "Laravel", "Symfony",
    "Express.js", "Vue.js", "Angular", "React", "Next.js", "Nuxt.js", "Flutter", "Ionic",
    "React Native", "Electron", "Meteor", "Phoenix (Elixir)", "Flask", "FastAPI", "Svelte",
    "Ember.js", "Backbone.js", "Ruby on Sinatra", "Koa.js", "Sails.js", "Grails",
    "Play Framework", "CakePHP", "CodeIgniter", "Zend Framework", "Yii", "Nest.js",
    "Quasar Framework", "Gatsby", "Xamarin", "Qt"
]

def map_services_and_tools(skills):
    matched_services = []
    for category, items in services_mapping.items():
        category_matches = [s for s in skills if s in items]
        if category_matches:
            matched_services.append({
                "category": category,
                "services": category_matches
            })
    matched_tools = [t for t in skills if t in tools_list]
    return matched_services, matched_tools

def search_user_data(user_id_str):
    try:
        if not user_id_str.strip():
            print("No User ID provided.")
            return

        user_id = ObjectId(user_id_str.strip())
        
        freelancer = freelancers_collection.find_one({"user_id": user_id})
        user = users_collection.find_one({"_id": user_id})

        resume_text = None
        if freelancer and "resume" in freelancer and isinstance(freelancer["resume"], dict):
            resume_info = freelancer["resume"]
            resume_url = resume_info.get("url")
            if resume_url:
                try:
                    resume_text = extract_text_from_pdf_url(resume_url)
                except Exception as e:
                    print(f"An error occurred while extracting resume text: {e}")
                    resume_text = None

        freelancer_name = None
        if user:
            first_name = user.get("first_name", "").strip()
            last_name = user.get("last_name", "").strip()
            freelancer_name = (first_name + " " + last_name).strip()
        if (not freelancer_name or freelancer_name == "") and freelancer:
            freelancer_name = freelancer.get("name", None)
        if not freelancer_name:
            freelancer_name = "N/A"

        about = ""
        if freelancer and "work_description" in freelancer:
            about = re.sub(r"<.*?>", "", freelancer["work_description"]).strip()

        github_link = user.get("github_profile", None) if user else None
        portfolio_website = freelancer.get("portfolio_website", "") if freelancer else ""
        project_links = freelancer.get("project_links", "") if freelancer else ""
        linkedin_link = freelancer.get("linkedIn_profile", None) if freelancer else None

        behance_link = None
        dribbble_link = None
        portfolio_link = None

        if "behance.net" in portfolio_website:
            behance_link = portfolio_website
        elif "dribbble.com" in project_links:
            dribbble_link = project_links
        else:
            if portfolio_website.strip():
                portfolio_link = portfolio_website

        freelancer_skills = freelancer.get("skills", []) if freelancer else []
        freelancer_tools = freelancer.get("tools", []) if freelancer else []
        combined_skills = freelancer_skills + freelancer_tools
        matched_services, matched_tools = map_services_and_tools(combined_skills)

        profile_photo = None
        if user and "profile_photo" in user:
            profile_photo = user["profile_photo"]
        elif freelancer and "profile_photo" in freelancer:
            profile_photo = freelancer["profile_photo"]

        # Updated instructions to produce more substantial bullet points for projects and experience
        instructions = f"""
        You are an AI assistant. You have the following data about a freelancer:

        Full Name: {freelancer_name}
        About (raw): {about}
        Github link: {github_link}
        Behance link: {behance_link}
        Dribbble link: {dribbble_link}
        Portfolio link: {portfolio_link}
        LinkedIn link: {linkedin_link}
        Profile Photo: {profile_photo}

        Services (Matched from freelancer skills):
        {json.dumps(matched_services, indent=2)}

        Tools (Matched from freelancer tools):
        {json.dumps(matched_tools, indent=2)}

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

        llm = initialize_llm(GOOGLE_API_KEY)
        ai_message = llm.invoke(instructions)
        response_text = ai_message.content

        cleaned_response = response_text.strip()
        cleaned_response = re.sub(r"```[\s\S]*?```", "", cleaned_response).strip()

        parsed_json = json.loads(cleaned_response)
        print(json.dumps(parsed_json, indent=2))

    except Exception as e:
        print(f"An error occurred while searching: {e}")
        traceback.print_exc()

    finally:
        client.close()

if __name__ == "__main__":
    user_id_input = input("Enter the User ID to search: ")
    search_user_data(user_id_input)
