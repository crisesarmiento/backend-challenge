"""
FastAPI Lambda handler for the Task Management API.
Handles task creation and queues tasks to SQS for processing.
"""

import os
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from mangum import Mangum
from pythonjsonlogger import jsonlogger
from botocore.exceptions import ClientError

from .models import TaskCreate, TaskResponse, HealthResponse


# ========================================
# Logging Configuration
# ========================================
def setup_logging() -> logging.Logger:
    """Configure JSON logging for CloudWatch."""
    log = logging.getLogger()

    # Set log level from environment or default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log.setLevel(log_level)

    # Clear existing handlers
    if log.handlers:
        for log_handler in log.handlers:
            log.removeHandler(log_handler)

    # Create console handler with JSON formatter
    log_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s", timestamp=True
    )
    log_handler.setFormatter(formatter)
    log.addHandler(log_handler)

    return log


logger = setup_logging()


# ========================================
# Environment Variables & AWS Setup
# ========================================
QUEUE_URL = os.getenv("QUEUE_URL")
if not QUEUE_URL:
    logger.error("QUEUE_URL environment variable is not set")
    raise ValueError("QUEUE_URL environment variable is required")

# Initialize SQS client
sqs_client = boto3.client("sqs")

logger.info("Initialized SQS client", extra={"queue_url": QUEUE_URL})


# ========================================
# FastAPI Application
# ========================================
app = FastAPI(
    title="Task Management API",
    description="API for managing tasks with ordered queue processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ========================================
# API Key Authentication Middleware
# ========================================
# Note: In production deployment, API Gateway handles authentication.
# This middleware simulates API Gateway behavior for testing purposes.
from fastapi import Request

ENABLE_API_KEY_CHECK = os.getenv("ENABLE_API_KEY_CHECK", "false").lower() == "true"
VALID_API_KEY = os.getenv("API_KEY", "test-api-key-12345")


@app.middleware("http")
async def validate_api_key(request: Request, call_next):
    """
    Middleware to validate API key in x-api-key header.

    In production, API Gateway validates the API key before reaching Lambda.
    This middleware simulates that behavior for testing.
    """
    # Skip authentication for health endpoint and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    # Only check API key if enabled (for testing)
    if ENABLE_API_KEY_CHECK:
        api_key = request.headers.get("x-api-key")

        if not api_key:
            logger.warning(
                "Missing API key", extra={"path": request.url.path, "method": request.method}
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Forbidden",
                    "message": "Missing API Key. Include x-api-key header.",
                },
            )

        if api_key != VALID_API_KEY:
            logger.warning(
                "Invalid API key",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "api_key_provided": api_key[:8] + "..." if len(api_key) > 8 else api_key,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "Forbidden", "message": "Invalid API Key."},
            )

        logger.debug("API key validated", extra={"path": request.url.path})

    return await call_next(request)


# ========================================
# Exception Handlers
# ========================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with proper error messages."""
    logger.warning("Validation error", extra={"path": request.url.path, "errors": exc.errors()})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.error(
        "HTTP error",
        extra={
            "path": request.url.path,
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP Error", "message": str(exc.detail)},
    )


# ========================================
# API Endpoints
# ========================================
@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Create a new task and queue it for processing",
)
async def create_task(task: TaskCreate) -> TaskResponse:
    """
    Create a new task and send it to the SQS FIFO queue for processing.

    Args:
        task: Task creation data

    Returns:
        TaskResponse with task_id and creation timestamp

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Creating new task",
        extra={"task_id": task_id, "title": task.title, "priority": task.priority},
    )

    # Prepare message body
    message_body: Dict[str, Any] = {
        "task_id": task_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "due_date": task.due_date,
        "created_at": created_at,
        "status": "queued",
    }

    try:
        # Send message to SQS FIFO queue
        response = sqs_client.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message_body),
            MessageGroupId="tasks",  # All tasks in same group for ordering
            MessageDeduplicationId=task_id,  # Use task_id for deduplication
        )

        logger.info(
            "Task queued successfully",
            extra={
                "task_id": task_id,
                "message_id": response.get("MessageId"),
                "sequence_number": response.get("SequenceNumber"),
            },
        )

        # Return task response
        return TaskResponse(
            task_id=task_id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            due_date=task.due_date,
            created_at=created_at,
            status="queued",
        )

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        logger.error(
            "Failed to send message to SQS",
            extra={
                "task_id": task_id,
                "error_code": error_code,
                "error_message": error_message,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue task: {error_message}",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error creating task",
            extra={"task_id": task_id, "error": str(e), "error_type": type(e).__name__},
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the task",
        ) from e


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the API is running and healthy",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with status and timestamp
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.debug("Health check performed", extra={"timestamp": timestamp})

    return HealthResponse(status="healthy", timestamp=timestamp)


# ========================================
# Lambda Handler
# ========================================
# Wrap FastAPI app with Mangum for AWS Lambda
mangum_handler = Mangum(app, lifespan="off")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function.

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        API Gateway response
    """
    logger.info(
        "Lambda invocation",
        extra={
            "request_id": (context.request_id if hasattr(context, "request_id") else None),
            "function_name": (context.function_name if hasattr(context, "function_name") else None),
        },
    )

    return mangum_handler(event, context)
