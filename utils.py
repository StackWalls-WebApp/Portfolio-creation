from flask import jsonify
import logging

def error_response(message, status_code=400):
    response = jsonify({"error": message})
    response.status_code = status_code
    return response

def success_response(data, status_code=200):
    response = jsonify(data)
    response.status_code = status_code
    return response

def setup_logging():
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s %(levelname)s %(name)s %(message)s',
                        handlers=[
                            logging.StreamHandler()
                        ])