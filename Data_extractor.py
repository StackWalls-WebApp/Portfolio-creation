from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json
from bson import ObjectId, json_util  # To handle MongoDB ObjectId serialization
import io
import requests
from PyPDF2 import PdfReader
import re

# Load environment variables
load_dotenv()

# MongoDB connection string
connection_string = os.getenv("MONGO_URI")

try:
    # Connect to MongoDB
    client = MongoClient(connection_string)
    db = client["stackwalls"]

    # Define collections
    freelancers_collection = db["freelancers"]
    users_collection = db["users"]

    print("Data successfully loaded from MongoDB!")

except Exception as e:
    print(f"An error occurred while connecting to MongoDB: {e}")
    exit()


def extract_text_from_pdf_url(url):
    response = requests.get(url)
    response.raise_for_status()
    pdf_reader = PdfReader(io.BytesIO(response.content))
    
    text_content = []
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_content.append(page_text)

    # Join all page texts
    all_text = "\n".join(text_content)

    # Normalize whitespace
    all_text = re.sub(r"[ \t]+", " ", all_text)
    all_text = re.sub(r"(\r\n|\r|\n)+", "\n", all_text)
    
    # Process line by line
    lines = all_text.split("\n")
    cleaned_lines = []
    
    for line in lines:
        # Split line by space
        parts = line.split(" ")
        
        # Heuristic: If most of the tokens are single characters, we assume they need to be rejoined
        single_chars = sum(len(p) == 1 for p in parts if p.strip())
        # Consider a threshold - if more than half of the tokens are single chars, try to rejoin them
        if len(parts) > 1 and single_chars > (len(parts) / 2):
            # Rejoin logic:
            new_line_words = []
            current_word_chars = []
            
            for token in parts:
                if len(token) == 1:
                    # Likely part of a word
                    current_word_chars.append(token)
                else:
                    # A multi-char token might indicate a separate word or break
                    if current_word_chars:
                        new_line_words.append("".join(current_word_chars))
                        current_word_chars = []
                    new_line_words.append(token)
            
            # If we ended with a partially collected word
            if current_word_chars:
                new_line_words.append("".join(current_word_chars))
            
            # Join the reconstructed line
            cleaned_lines.append(" ".join(new_line_words))
        else:
            # This line doesn't seem to be mostly single chars, leave it as is
            cleaned_lines.append(line)

    # Final cleaned text
    cleaned_text = "\n".join(l.strip() for l in cleaned_lines if l.strip())
    return cleaned_text


def search_user_data(user_id_str):
    try:
        # Convert the input string to ObjectId
        user_id = ObjectId(user_id_str)
        
        # Search in 'freelancers' collection
        freelancer = freelancers_collection.find_one({"user_id": user_id})
        
        # Search in 'users' collection
        user = users_collection.find_one({"_id": user_id})

        # Prepare output data
        output_data = {}

        output_data["user"] = user if user else None
        output_data["freelancer"] = freelancer if freelancer else None

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
        
        output_data["resume_text"] = resume_text

        # Print all data in JSON format
        print(json.dumps(output_data, indent=4, default=json_util.default))

    except Exception as e:
        print(f"An error occurred while searching: {e}")


# Input: User ID to search
user_id_input = input("Enter the User ID to search: ")
search_user_data(user_id_input)
