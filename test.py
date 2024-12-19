from portfolio import lambda_handler

# Sample event
event = {
    "httpMethod": "POST",
    "body": '{"user_id": "66c5e449ebeefff23d264ead"}'
}

# Sample context (can be empty or mock as needed)
context = {}

# Invoke the handler
response = lambda_handler(event, context)
print(response)
