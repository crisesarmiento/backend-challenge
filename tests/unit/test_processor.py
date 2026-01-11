"""Unit tests for queue processor Lambda handler."""

import json
import os
import sys
import uuid
from typing import Dict, Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/processor"))

import src.processor.index as index


@pytest.fixture
def lambda_context() -> MagicMock:
    """Mock Lambda context."""
    context = MagicMock()
    context.request_id = "test-request-id"
    context.function_name = "test-processor"
    context.get_remaining_time_in_millis = MagicMock(return_value=30000)
    return context


@pytest.fixture
def sample_task_data() -> Dict[str, Any]:
    """Sample task data."""
    return {
        "task_id": str(uuid.uuid4()),
        "title": "Test Task",
        "description": "Test Description",
        "priority": "high",
        "due_date": "2026-01-15T12:00:00Z",
        "created_at": "2026-01-10T12:00:00Z",
        "status": "queued",
    }


@pytest.fixture
def sqs_event(sample_task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create mock SQS event."""
    return {
        "Records": [
            {
                "messageId": str(uuid.uuid4()),
                "receiptHandle": "test-receipt-handle",
                "body": json.dumps(sample_task_data),
                "attributes": {"MessageGroupId": "tasks", "SequenceNumber": "1"},
            }
        ]
    }


@pytest.fixture(autouse=True)
def clear_processed_tasks():
    """Clear processed tasks set before each test."""
    index.processed_tasks.clear()
    yield
    index.processed_tasks.clear()


@pytest.mark.unit
def test_lambda_handler_success(sqs_event: Dict[str, Any], lambda_context: MagicMock) -> None:
    """Test successful task processing."""
    result = index.lambda_handler(sqs_event, lambda_context)

    assert "batchItemFailures" in result
    assert result["batchItemFailures"] == []
    assert len(index.processed_tasks) == 1


@pytest.mark.unit
def test_lambda_handler_invalid_json(lambda_context: MagicMock) -> None:
    """Test handling of invalid JSON."""
    message_id = str(uuid.uuid4())
    event = {
        "Records": [
            {
                "messageId": message_id,
                "receiptHandle": "test-receipt-handle",
                "body": "invalid json{{{",
                "attributes": {"MessageGroupId": "tasks", "SequenceNumber": "1"},
            }
        ]
    }

    result = index.lambda_handler(event, lambda_context)

    assert "batchItemFailures" in result
    assert len(result["batchItemFailures"]) == 1
    assert result["batchItemFailures"][0]["itemIdentifier"] == message_id


@pytest.mark.unit
def test_idempotency(sqs_event: Dict[str, Any], lambda_context: MagicMock) -> None:
    """Test idempotent processing."""
    # Process first time
    result1 = index.lambda_handler(sqs_event, lambda_context)
    assert result1["batchItemFailures"] == []
    assert len(index.processed_tasks) == 1

    # Process second time (same task)
    result2 = index.lambda_handler(sqs_event, lambda_context)
    assert result2["batchItemFailures"] == []
    # Task count shouldn't increase (idempotency)
    assert len(index.processed_tasks) == 1


@pytest.mark.unit
def test_lambda_handler_missing_task_id(lambda_context: MagicMock) -> None:
    """Test handling of task data missing task_id."""
    message_id = str(uuid.uuid4())
    event = {
        "Records": [
            {
                "messageId": message_id,
                "receiptHandle": "test-receipt-handle",
                "body": json.dumps(
                    {
                        "title": "Test Task",
                        "description": "Test Description",
                        "priority": "high",
                        # Missing task_id
                    }
                ),
                "attributes": {"MessageGroupId": "tasks", "SequenceNumber": "1"},
            }
        ]
    }

    result = index.lambda_handler(event, lambda_context)

    # Should still process successfully with task_id defaulting to "unknown"
    assert "batchItemFailures" in result
    assert result["batchItemFailures"] == []


@pytest.mark.unit
def test_lambda_handler_multiple_records(
    sample_task_data: Dict[str, Any], lambda_context: MagicMock
) -> None:
    """Test processing multiple records in batch."""
    task_data_2 = sample_task_data.copy()
    task_data_2["task_id"] = str(uuid.uuid4())
    task_data_2["title"] = "Test Task 2"

    event = {
        "Records": [
            {
                "messageId": str(uuid.uuid4()),
                "receiptHandle": "test-receipt-handle-1",
                "body": json.dumps(sample_task_data),
                "attributes": {"MessageGroupId": "tasks", "SequenceNumber": "1"},
            },
            {
                "messageId": str(uuid.uuid4()),
                "receiptHandle": "test-receipt-handle-2",
                "body": json.dumps(task_data_2),
                "attributes": {"MessageGroupId": "tasks", "SequenceNumber": "2"},
            },
        ]
    }

    result = index.lambda_handler(event, lambda_context)

    assert "batchItemFailures" in result
    assert result["batchItemFailures"] == []
    assert len(index.processed_tasks) == 2


@pytest.mark.unit
def test_lambda_handler_partial_batch_failure(
    sample_task_data: Dict[str, Any], lambda_context: MagicMock
) -> None:
    """Test partial batch failure where some records succeed and some fail."""
    invalid_message_id = str(uuid.uuid4())

    event = {
        "Records": [
            {
                "messageId": str(uuid.uuid4()),
                "receiptHandle": "test-receipt-handle-1",
                "body": json.dumps(sample_task_data),
                "attributes": {"MessageGroupId": "tasks", "SequenceNumber": "1"},
            },
            {
                "messageId": invalid_message_id,
                "receiptHandle": "test-receipt-handle-2",
                "body": "invalid json{{{",
                "attributes": {"MessageGroupId": "tasks", "SequenceNumber": "2"},
            },
        ]
    }

    result = index.lambda_handler(event, lambda_context)

    assert "batchItemFailures" in result
    assert len(result["batchItemFailures"]) == 1
    assert result["batchItemFailures"][0]["itemIdentifier"] == invalid_message_id
    # First record should be processed successfully
    assert len(index.processed_tasks) == 1


@pytest.mark.unit
def test_lambda_handler_empty_records(lambda_context: MagicMock) -> None:
    """Test handling of empty Records list."""
    event = {"Records": []}

    result = index.lambda_handler(event, lambda_context)

    assert "batchItemFailures" in result
    assert result["batchItemFailures"] == []
    assert len(index.processed_tasks) == 0


@pytest.mark.unit
def test_process_task_function(sample_task_data: Dict[str, Any]) -> None:
    """Test process_task function directly."""
    # Clear processed tasks first
    index.processed_tasks.clear()

    # Process task
    index.process_task(sample_task_data)

    # Verify task was added to processed set
    task_id = sample_task_data["task_id"]
    assert task_id in index.processed_tasks
    assert len(index.processed_tasks) == 1

    # Process same task again (idempotency check)
    index.process_task(sample_task_data)

    # Should still only have one task
    assert len(index.processed_tasks) == 1


@pytest.mark.unit
def test_lambda_handler_all_priorities(lambda_context: MagicMock) -> None:
    """Test processing tasks with different priority levels."""
    priorities = ["low", "medium", "high"]
    records = []

    for i, priority in enumerate(priorities):
        task_data = {
            "task_id": str(uuid.uuid4()),
            "title": f"Task {i+1}",
            "description": f"Description {i+1}",
            "priority": priority,
            "due_date": "2026-01-15T12:00:00Z",
            "created_at": "2026-01-10T12:00:00Z",
            "status": "queued",
        }
        records.append(
            {
                "messageId": str(uuid.uuid4()),
                "receiptHandle": f"test-receipt-handle-{i}",
                "body": json.dumps(task_data),
                "attributes": {"MessageGroupId": "tasks", "SequenceNumber": str(i + 1)},
            }
        )

    event = {"Records": records}
    result = index.lambda_handler(event, lambda_context)

    assert "batchItemFailures" in result
    assert result["batchItemFailures"] == []
    assert len(index.processed_tasks) == 3
