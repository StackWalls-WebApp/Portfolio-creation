# Freelancer Portfolio API

A Flask-based API that generates professional and creative portfolios for freelancers by extracting data from MongoDB and processing resumes in PDF format. The API leverages Google's Generative AI capabilities to produce detailed portfolio information.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Running the Application](#running-the-application)
- [Deployment](#deployment)
- [API Usage](#api-usage)
- [License](#license)

## Features

- **PDF Text Extraction:** Extracts and cleans text from resume PDFs hosted online.
- **Service and Tool Mapping:** Maps freelancer skills and tools to predefined categories.
- **AI-Powered Portfolio Generation:** Uses Google's Generative AI to create comprehensive portfolio data.
- **Dockerized Setup:** Easily deployable using Docker and Docker Compose.
- **Modular Codebase:** Clean and maintainable code structure.
- **Error Handling:** Robust error and exception handling with logging.

## Prerequisites

- **Docker:** [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose:** [Install Docker Compose](https://docs.docker.com/compose/install/)
- **AWS EC2 Instance (Optional):** For deployment on AWS.

## Project Structure

