# Task Management API - Backend Challenge

A serverless task management system built with AWS CDK, featuring ordered message processing, comprehensive error handling, and production-ready architecture.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Testing & Validation](#testing--validation)
- [Design Decisions](#design-decisions)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)

---

## 🚀 Quick Start

**For evaluators and quick testing:**

```bash
# 1. Automated setup (recommended)
./setup.sh

# 2. Activate virtual environment
source venv/bin/activate

# 3. Run all validations
./validate.sh
```

**What this does:**
- ✅ Sets up Python virtual environment
- ✅ Installs all dependencies (Python + Node.js)
- ✅ Runs 29 unit tests
- ✅ Type checks all code
- ✅ Validates CDK infrastructure

**Result:** Complete validation in ~2 minutes!

For detailed manual setup, see [Setup Instructions](#setup-instructions) below.

---

## 🏗️ Architecture Overview

This solution implements a serverless task management API with guaranteed message ordering and at-least-once processing semantics.

### System Components

```
┌─────────────┐      ┌──────────────┐      ┌────────────┐      ┌─────────────────┐
│   Client    │─────▶│ API Gateway  │─────▶│ API Lambda │─────▶│  SQS FIFO Queue │
└─────────────┘      └──────────────┘      └────────────┘      └─────────────────┘
                                                                          │
                                                                          ▼
                                                                  ┌─────────────────┐
                                                                  │ Processor Lambda│
                                                                  └─────────────────┘
                                                                          │
                                                                          ▼
                                                                  ┌─────────────────┐
                                                                  │   Dead Letter   │
                                                                  │      Queue      │
                                                                  └─────────────────┘
```

### Key Features

- ✅ **Ordered Processing**: SQS FIFO queue ensures tasks are processed in the exact order received
- ✅ **At-Least-Once Delivery**: SQS guarantees with visibility timeout and retry logic
- ✅ **Error Handling**: Dead letter queue captures failed tasks after 3 retry attempts
- ✅ **Idempotency**: Content-based deduplication prevents duplicate task processing
- ✅ **Least Privilege IAM**: Granular permissions for each component
- ✅ **Observability**: CloudWatch Logs + X-Ray tracing enabled

---

## 🛠️ Tech Stack

### Infrastructure
- **AWS CDK v2** (TypeScript) - Infrastructure as Code
- **AWS Lambda** - Serverless compute (Python 3.12)
- **Amazon SQS FIFO** - Message queue with ordering guarantees
- **Amazon API Gateway** - REST API endpoint

### Backend
- **Python 3.12** - Runtime environment
- **FastAPI** - Modern web framework for API
- **Pydantic** - Data validation and serialization
- **Boto3** - AWS SDK for Python

### Testing & Quality
- **pytest** - Testing framework
- **moto** - AWS service mocking
- **pyright** - Static type checking
- **black** - Code formatting

---

## 📁 Project Structure

```
backend-challenge/
├── cdk/                          # AWS CDK Infrastructure
│   ├── bin/
│   │   └── cdk.ts               # CDK app entry point
│   ├── lib/
│   │   └── cdk-stack.ts         # Main infrastructure stack
│   ├── cdk.json                 # CDK configuration
│   └── package.json             # Node.js dependencies
│
├── src/
│   ├── api/                     # API Lambda handler
│   │   ├── index.py            # FastAPI application
│   │   └── models.py           # Pydantic models
│   │
│   └── processor/              # Queue processor Lambda
│       └── index.py            # SQS event handler
│
├── tests/
│   └── unit/
│       ├── test_api.py         # API Lambda tests (20 tests)
│       └── test_processor.py   # Processor Lambda tests (9 tests)
│
├── setup.sh                     # Automated setup script
├── validate.sh                  # Automated validation script
├── pytest.ini                   # Pytest configuration
├── pyproject.toml              # Python tooling configuration
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
└── README.md                   # This file
```

---

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.12+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **AWS CLI** (optional for deployment) - [Install Guide](https://aws.amazon.com/cli/)

### Option A: Automated Setup (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd backend-challenge

# Run setup script
./setup.sh
```

This single command will:
- ✅ Create and activate virtual environment
- ✅ Install all Python dependencies
- ✅ Install CDK dependencies
- ✅ Build TypeScript code

### Option B: Manual Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd backend-challenge
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Set Up CDK Infrastructure

```bash
cd cdk

# Install Node.js dependencies
npm install

# Build TypeScript
npm run build
```

---

## 🧪 Testing & Validation

### Option A: Automated Validation (Recommended)

```bash
# Run complete validation suite
./validate.sh
```

This single command will:
- ✅ Run all 29 unit tests
- ✅ Run type checking with pyright
- ✅ Validate CDK infrastructure synthesis

**Expected Output:**
- ✅ All validations passed
- ✅ Summary of test results
- ✅ Ready for deployment confirmation

### Option B: Manual Validation

### Run Unit Tests

```bash
# From project root, with virtual environment activated
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=term-missing
```

**Expected Output:**
- ✅ 29 tests passing (20 API + 9 Processor)
- ✅ 90%+ code coverage

### Run Type Checking

```bash
# Type check Python code
pyright src/
```

**Expected Output:**
- ✅ 0 errors, 0 warnings

### Validate CDK Infrastructure

```bash
cd cdk

# Synthesize CloudFormation template
npm run cdk synth
```

**Expected Output:**
- ✅ Valid CloudFormation template generated
- ✅ No synthesis errors

### Code Formatting (Optional)

```bash
# Check formatting
black --check src/ tests/

# Apply formatting
black src/ tests/
```

---

## 🎯 Design Decisions

### 1. SQS FIFO Queue for Ordering

**Decision:** Use SQS FIFO queue instead of standard queue.

**Rationale:**
- Challenge requires tasks to be "processed in the order they were received"
- FIFO queues guarantee First-In-First-Out delivery
- Content-based deduplication provides automatic idempotency

**Trade-offs:**
- FIFO queues have lower throughput (300 TPS) vs standard queues (unlimited)
- For this use case, ordering guarantees are more critical than throughput

### 2. Batch Size of 1 for Processor Lambda

**Decision:** Process one message at a time (`batchSize: 1`).

**Rationale:**
- Maintains strict ordering guarantees
- Simplifies error handling (no partial batch failures)
- Prevents out-of-order processing if batch contains multiple messages

**Trade-offs:**
- Lower throughput compared to batch processing
- Higher Lambda invocation costs
- Acceptable for task management use case where ordering is critical

### 3. Standard Lambda Functions vs PythonFunction

**Decision:** Use `lambda.Function` with `Code.fromAsset()` instead of `@aws-cdk/aws-lambda-python-alpha` PythonFunction.

**Rationale:**
- No Docker dependency for `cdk synth` validation
- Simpler, more maintainable infrastructure code
- No external pip dependencies to bundle (using AWS-provided packages)

**Production Consideration:**
- For production with external dependencies, would add a build step to create deployment package

### 4. Dead Letter Queue with 3 Retries

**Decision:** Configure DLQ with `maxReceiveCount: 3`.

**Rationale:**
- Balances reliability (retries for transient failures) with efficiency (don't retry forever)
- 14-day retention in DLQ allows investigation of systematic failures
- Follows AWS best practices for SQS error handling

### 5. FastAPI for REST API

**Decision:** Use FastAPI instead of Flask or Django.

**Rationale:**
- Native async support (better Lambda performance)
- Built-in Pydantic validation (type-safe)
- Automatic OpenAPI documentation
- Modern Python framework with excellent type hinting

### 6. Least Privilege IAM Permissions

**Decision:** Use CDK's `grant*` methods instead of broad permissions.

**Rationale:**
- API Lambda: Only `sqs:SendMessage` to task queue
- Processor Lambda: Only `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:ChangeMessageVisibility` on task queue
- Follows AWS security best practices
- Reduces attack surface if Lambda is compromised

---

## 📦 Deployment

> **Note:** Actual deployment is not required for this challenge. The infrastructure is designed to be deployable but evaluation focuses on code quality and architecture.

### Deployment Steps (If Needed)

```bash
cd cdk

# Bootstrap CDK (first time only)
npx cdk bootstrap

# Deploy stack
npx cdk deploy

# Outputs will include:
# - API Gateway endpoint URL
# - SQS queue URLs
# - Lambda function ARNs
```

### Environment Variables

No environment-specific configuration required. The stack uses CloudFormation pseudo-parameters:
- `AWS::AccountId` - Automatically resolved to deployment account
- `AWS::Region` - Automatically resolved to deployment region

---

## 📖 API Documentation

### POST /tasks

Create a new task and add it to the processing queue.

**Request Body:**

```json
{
  "title": "Complete project documentation",
  "description": "Write comprehensive documentation for the API",
  "priority": "high",
  "due_date": "2026-01-15T18:00:00Z"
}
```

**Field Validation:**
- `title`: Required, 1-200 characters
- `description`: Required, 1-2000 characters
- `priority`: Required, one of: `"low"`, `"medium"`, `"high"`
- `due_date`: Optional, ISO 8601 timestamp

**Success Response (200):**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Complete project documentation",
  "description": "Write comprehensive documentation for the API",
  "priority": "high",
  "due_date": "2026-01-15T18:00:00Z",
  "created_at": "2026-01-10T12:00:00Z",
  "status": "queued"
}
```

**Error Responses:**

- `400 Bad Request` - Invalid input (missing fields, wrong types, validation errors)
- `500 Internal Server Error` - Server error (queue unavailable, etc.)

### GET /health

Health check endpoint.

**Success Response (200):**

```json
{
  "status": "healthy",
  "timestamp": "2026-01-10T12:00:00Z"
}
```

---

## 🧑‍💻 Development

### Running Tests During Development

```bash
# Watch mode (re-run on file changes)
pytest-watch

# Run specific test file
pytest tests/unit/test_api.py -v

# Run tests matching pattern
pytest -k "test_create_task" -v
```

### Debugging

**API Lambda:**
```python
# Set LOG_LEVEL environment variable
os.environ["LOG_LEVEL"] = "DEBUG"
```

**Processor Lambda:**
```python
# Check CloudWatch Logs for detailed processing logs
# Logs include task_id, processing status, and error details
```

---

## 📊 Test Coverage

Current test coverage: **90%+**

### API Lambda Tests (20 tests)
- ✅ Health endpoint
- ✅ Task creation (success cases)
- ✅ Input validation (all required fields)
- ✅ Priority validation (low/medium/high)
- ✅ Field length validation (title, description)
- ✅ Whitespace trimming
- ✅ SQS error handling
- ✅ Unique ID generation
- ✅ Timestamp generation
- ✅ ISO 8601 date validation

### Processor Lambda Tests (9 tests)
- ✅ Successful task processing
- ✅ Invalid JSON handling
- ✅ Idempotency (duplicate message handling)
- ✅ Missing task_id handling
- ✅ Multiple records processing
- ✅ Partial batch failure reporting
- ✅ Empty records handling
- ✅ Process task function
- ✅ All priority levels

---

## 🔒 Security Considerations

### Implemented Security Features

1. **Input Validation**: Pydantic models with strict validation rules
2. **Input Sanitization**: Automatic whitespace trimming, length limits
3. **Least Privilege IAM**: Minimal permissions for each Lambda function
4. **CORS Configuration**: Configured with appropriate headers
5. **No Hardcoded Secrets**: All configuration via environment variables
6. **X-Ray Tracing**: Enabled for security monitoring and debugging

### Production Recommendations

- Add API authentication (AWS Cognito, API Keys, or custom authorizer)
- Implement rate limiting and throttling
- Add request validation at API Gateway level
- Enable AWS WAF for API Gateway
- Implement encryption at rest for SQS queues
- Add CloudWatch alarms for DLQ depth

---

## 🐛 Troubleshooting

### CDK Synth Fails

**Issue:** `cdk synth` fails with validation errors

**Solution:**
```bash
cd cdk
npm install
npm run build
npm run cdk synth
```

### Tests Fail with "QUEUE_URL not set"

**Issue:** Tests fail during import with environment variable error

**Solution:**
Environment variable is set in test file before imports. Ensure you're running from project root with virtual environment activated:
```bash
source venv/bin/activate
pytest -v
```

### Type Checking Errors

**Issue:** `pyright` reports type errors

**Solution:**
Ensure all dependencies are installed and you're using Python 3.12:
```bash
pip install -r requirements.txt
pyright src/
```

---

## 📝 Challenge Requirements Checklist

### Infrastructure as Code ✅
- [x] AWS CDK v2 with TypeScript
- [x] Compute resources (Lambda)
- [x] REST API (API Gateway)
- [x] Message queue with ordering (SQS FIFO)
- [x] Logging and monitoring (CloudWatch + X-Ray)
- [x] Supports `cdk synth` validation
- [x] No hardcoded account IDs or regions
- [x] Environment-specific configurations via CDK context

### Core API ✅
- [x] POST /tasks endpoint
- [x] Task model with all required fields
- [x] Comprehensive input validation (Pydantic)
- [x] Send to queue with ordering guarantees
- [x] Return unique task_id
- [x] At-least-once delivery
- [x] Proper error handling and HTTP status codes
- [x] Unit tests with pytest
- [x] Type hints throughout

### Queue Processing System ✅
- [x] Process tasks in order
- [x] At-least-once processing
- [x] Retry logic and DLQ
- [x] Maintain ordering with retries
- [x] Type hints throughout
- [x] Dead letter queue implementation
- [x] Comprehensive error handling and logging
- [x] Idempotent processing

### Code Quality ✅
- [x] Python formatted with black
- [x] Type checking with pyright (0 errors)
- [x] Comprehensive README
- [x] Proper logging

### Testing ✅
- [x] Unit tests for all business logic (29 tests)
- [x] Integration tests with mocked AWS services (moto)
- [x] 90%+ test coverage

### Security ✅
- [x] Input validation and sanitization
- [x] Environment variables for configuration
- [x] Least privilege IAM policies
- [x] CORS configuration

---

## 📄 License

This project was created as part of a technical challenge.

---

## 👤 Author

**Cristian Sarmiento**

- Challenge completed: January 2026
- AI assistance: Used Claude Code (as encouraged by challenge)

---

## 🙏 Acknowledgments

- Built with AWS CDK, FastAPI, and Python 3.12
- Tested with pytest and moto
- AI assistance from Claude Code for development workflow
