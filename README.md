# Buyer Request Workflow with Audit Log

A RESTful API for managing buyer requests, evidence documents, and maintaining audit logs.

## Repository Structure
This repository contains both Phase-AA and Phase-BB implementations. The current `main` branch contains the latest Phase-BB code. If you need to access the Phase-AA code, you can find it at commit `e844d39`.

For more details on working with different versions, see the [Git Workflow Documentation](#git-workflow-documentation) section below.

# Phase AA. Title: Buyer Request Workflow + Audit Log (Truth-at-Source Controls)
## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup and Installation](#setup-and-installation)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
  - [Authentication](#authentication)
  - [Evidence Endpoints](#evidence-endpoints)
  - [Request Endpoints](#request-endpoints)
  - [Factory Request Endpoints](#factory-request-endpoints)
  - [Audit Logs](#audit-logs)
- [Project Documentation](#project-documentation)

## Project Documentation

## Features
- User authentication with JWT
- Role-based access control (Buyer, Factory, Admin)
- Evidence document management with versioning
- Request workflow management
- Comprehensive audit logging
- Swagger API documentation

## Prerequisites
- Python 3.8+
- pip (Python package manager)
- Virtualenv (recommended)

## Setup and Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/mehedishovon01/Buyer-Request-Workflow-with-Audit-Log.git
   cd Buyer-Request-Workflow-with-Audit-Log
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root with the following variables:
   ```
   cp .env.example .env
   ```
   Edit the `.env` file and add your environment variables.

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (admin)**
   ```bash
   python manage.py createsuperuser
   ```

## Running the Application

1. **Start the development server**
   ```bash
   python manage.py runserver
   ```

2. **Access the API documentation**
   - Swagger UI: http://127.0.0.1:8000/api/v1/schema/swagger/
   - ReDoc: http://127.0.0.1:8000/api/v1/schema/redoc/

## API Documentation (curl commands)

### Authentication

#### Login and Get JWT Token
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": "admin", "role": "admin", "factoryId": "F001"}'
```

#### Refresh Token
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "your_refresh_token"}'
```

### Evidence Endpoints

#### List All Evidence
```bash
curl -X GET http://127.0.0.1:8000/api/v1/compliance/evidence/ \
  -H "Authorization: Bearer your_access_token"
```

#### Create New Evidence
```bash
curl -X POST http://127.0.0.1:8000/api/v1/compliance/evidence/ \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "doc_type": "txt", "notes": "notes", "expiry": "2026-10-01"}'
```

#### Add Version to Evidence
```bash
curl -X POST http://127.0.0.1:8000/api/v1/compliance/evidence/1/versions/ \
  -H "Authorization: Bearer your_access_token" \
  -F "file=@path/to/your/file.txt"
```

### Request Endpoints

#### List All Requests
```bash
curl -X GET http://127.0.0.1:8000/api/v1/compliance/requests/ \
  -H "Authorization: Bearer your_access_token"
```

#### Create New Request
```bash
curl -X POST http://127.0.0.1:8000/api/v1/compliance/requests/ \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{"factory_id": "admin", "title": "This", "items": [{"docType": "txt"}]}'
```

#### Fulfill Request Item
```bash
curl -X POST http://127.0.0.1:8000/api/v1/compliance/requests/1/items/1/fulfill/ \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{"evidence_id": 2, "version_id": 1}'
```

### Factory Request Endpoints

#### List Factory Requests
```bash
curl -X GET http://127.0.0.1:8000/api/v1/compliance/factory/requests/ \
  -H "Authorization: Bearer your_access_token"
```

#### List Pending Requests
```bash
curl -X GET http://127.0.0.1:8000/api/v1/compliance/factory/requests/pending/ \
  -H "Authorization: Bearer your_access_token"
```

### Audit Logs

#### View Audit Logs (Paginated)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/auth/audit/?page=1&page_size=10" \
  -H "Authorization: Bearer your_access_token"
```

## Error Handling
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Invalid or missing authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error


# Phase BB: Title: Phase A “Thin Slice” + Decisions + Change Request
- [Part A - Mini Design Document](./phase-BB/part_A_1_page_Mini_Design_Doc.md)
- [Part B - Implementation Details](./phase-BB/Part%20B%20%E2%80%94%20Implement%20ONE%20thin%20slice%20%28Required%29.md)
- [Part C - Change Request](./phase-BB/Part%20C%20%E2%80%94%20Change%20Request.md)

## Git Workflow Documentation

### Viewing Commit History

#### View Compact Commit History
```bash
git log --oneline
# Example output:
# e4d2151 (HEAD -> main, origin/main, origin/HEAD) Phase-BB
# 53b83d6 fix: swagger issue, add readme for documentation
# e844d39 initial:commit setup the full system
# 67c8019 Initial commit
```

### Working with Commits

#### Checkout a Specific Commit
```bash
git checkout <commit-hash>
# Example:
git checkout 53b83d6  # Checks out the specific commit
```

### Accessing Phase-AA Code
To work with the Phase-AA implementation, use:
```bash
git checkout e844d39  # Checkout Phase-AA code
```

### Viewing Changes

#### See Changes in Working Directory
```bash
git status  # Shows current branch and changes

#### Return to the Latest Commit
```bash
git checkout main  # Or your branch name
```

## License
This project is licensed under the MIT License - see the LICENSE file for details
