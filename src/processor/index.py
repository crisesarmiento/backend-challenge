"""
SQS Lambda event processor for task queue.
Processes tasks from FIFO queue with ordering guarantees and error handling.
"""

import os
import json
import logging
from typing import Dict, Any, List, Set
from datetime import datetime, timezone

import boto3
from pythonjsonlogger import jsonlogger
from botocore.exceptions import ClientError


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
DLQ_URL = os.getenv("DLQ_URL")  # Optional for custom DLQ handling
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Initialize SQS client (if needed for custom DLQ operations)
sqs_client = boto3.client("sqs")

logger.info(
    "Processor initialized",
    extra={"log_level": LOG_LEVEL, "dlq_configured": DLQ_URL is not None},
)


# ========================================
# Idempotency Tracking
# ========================================
# In-memory set to track processed task IDs
# Production would use DynamoDB with TTL for persistence
processed_tasks: Set[str] = set()


# ========================================
# Task Processing Logic
# ========================================
def process_task(task_data: Dict[str, Any]) -> None:
    """
    Process a single task.

    Args:
        task_data: Dictionary containing task information

    Raises:
        Exception: If processing fails
    """
    task_id = task_data.get("task_id", "unknown")

    logger.info(
        "Processing task",
        extra={
            "task_id": task_id,
            "title": task_data.get("title"),
            "priority": task_data.get("priority"),
            "due_date": task_data.get("due_date"),
            "created_at": task_data.get("created_at"),
        },
    )

    # Check idempotency - skip if already processed
    if task_id in processed_tasks:
        logger.warning("Task already processed, skipping", extra={"task_id": task_id})
        return

    # Simulate task processing
    # In production, this would be actual business logic:
    # - Send notifications
    # - Update database
    # - Call external APIs
    # - Generate reports, etc.

    logger.info(
        "Task processing simulation",
        extra={
            "task_id": task_id,
            "title": task_data.get("title"),
            "description": task_data.get("description"),
            "priority": task_data.get("priority"),
            "processing_time": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Mark as processed (idempotency)
    processed_tasks.add(task_id)

    logger.info(
        "Task processed successfully",
        extra={"task_id": task_id, "processed_count": len(processed_tasks)},
    )


# ========================================
# Lambda Handler
# ========================================
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for processing SQS messages.

    Processes tasks from FIFO queue with ordering guarantees.
    Returns batch item failures for retry logic.

    Args:
        event: Lambda event containing SQS records
        context: Lambda context object

    Returns:
        Dictionary with batchItemFailures list for SQS retry handling
    """
    logger.info(
        "Lambda invocation started",
        extra={
            "request_id": (context.request_id if hasattr(context, "request_id") else None),
            "function_name": (context.function_name if hasattr(context, "function_name") else None),
            "remaining_time_ms": (
                context.get_remaining_time_in_millis()
                if hasattr(context, "get_remaining_time_in_millis")
                else None
            ),
        },
    )

    # Extract records from event
    records = event.get("Records", [])
    logger.info("Processing batch", extra={"record_count": len(records)})

    # Track failed message IDs for partial batch failure reporting
    batch_item_failures: List[Dict[str, str]] = []

    # Process each record
    for record in records:
        message_id = record.get("messageId", "unknown")
        receipt_handle = record.get("receiptHandle", "unknown")

        try:
            # Parse message body
            message_body = record.get("body", "{}")
            task_data = json.loads(message_body)

            task_id = task_data.get("task_id", "unknown")

            logger.info(
                "Processing record",
                extra={
                    "message_id": message_id,
                    "task_id": task_id,
                    "message_group_id": record.get("attributes", {}).get("MessageGroupId"),
                    "sequence_number": record.get("attributes", {}).get("SequenceNumber"),
                },
            )

            # Process the task
            process_task(task_data)

            logger.info(
                "Record processed successfully",
                extra={"message_id": message_id, "task_id": task_id},
            )

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse message body",
                extra={
                    "message_id": message_id,
                    "error": str(e),
                    "error_type": "JSONDecodeError",
                    "body_preview": message_body[:200] if message_body else None,
                },
            )
            # Add to failures for retry
            batch_item_failures.append({"itemIdentifier": message_id})

        except KeyError as e:
            logger.error(
                "Missing required field in task data",
                extra={
                    "message_id": message_id,
                    "error": str(e),
                    "error_type": "KeyError",
                    "missing_field": str(e),
                },
            )
            # Add to failures for retry
            batch_item_failures.append({"itemIdentifier": message_id})

        except Exception as e:
            logger.error(
                "Unexpected error processing record",
                extra={
                    "message_id": message_id,
                    "task_id": (
                        task_data.get("task_id", "unknown")
                        if "task_data" in locals()
                        else "unknown"
                    ),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            # Add to failures for retry
            batch_item_failures.append({"itemIdentifier": message_id})

    # Log summary
    successful_count = len(records) - len(batch_item_failures)
    logger.info(
        "Batch processing completed",
        extra={
            "total_records": len(records),
            "successful": successful_count,
            "failed": len(batch_item_failures),
            "batch_item_failures": batch_item_failures,
        },
    )

    # Return batch item failures for SQS retry handling
    # Empty list = all succeeded, SQS will delete all messages
    # Non-empty list = partial failure, SQS will retry only failed messages
    return {"batchItemFailures": batch_item_failures}
