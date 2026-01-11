"""Unit tests for API Lambda handler."""

import os
import sys
import importlib.util
from typing import Dict, Any, Generator
from unittest.mock import MagicMock, patch

import pytest

# ✅ SET QUEUE_URL BEFORE IMPORTING APPLICATION CODE
# This is required because src/api/index validates QUEUE_URL at module load time
# The actual mock SQS queue URL from the fixture will be used during test execution
os.environ.setdefault(
    "QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/dummy-queue.fifo")

from moto.core.decorator import mock_aws
import boto3
from fastapi.testclient import TestClient


# Add src/api to path explicitly for this import
api_path = os.path.join(os.path.dirname(__file__), "../../src/api")
if api_path not in sys.path:
    sys.path.insert(0, api_path)

# Import after setting env vars
import src.api.index as index


@pytest.fixture
def sqs_queue() -> Generator[str, None, None]:
    """Create mock SQS FIFO queue."""
    with mock_aws():
        sqs = boto3.client("sqs", region_name="us-east-1")
        response = sqs.create_queue(
            QueueName="tasks.fifo",
            Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
        )
        queue_url = response["QueueUrl"]
        yield queue_url


@pytest.fixture
def client(sqs_queue: str) -> TestClient:
    """Create FastAPI test client with mocked SQS."""
    # Set environment variable before importing
    os.environ["QUEUE_URL"] = sqs_queue
    os.environ["LOG_LEVEL"] = "ERROR"  # Reduce log noise in tests

    importlib.reload(index)  # Reload to get fresh module with new env vars

    return TestClient(index.app)


@pytest.fixture
def valid_task_data() -> Dict[str, Any]:
    """Valid task creation data."""
    return {
        "title": "Test Task",
        "description": "Test task description for unit testing",
        "priority": "high",
        "due_date": "2026-01-15T12:00:00Z",
    }


@pytest.fixture
def valid_task_data_no_due_date() -> Dict[str, Any]:
    """Valid task without due date."""
    return {
        "title": "Test Task No Date",
        "description": "Test task without due date",
        "priority": "medium",
    }


@pytest.mark.unit
def test_health_endpoint(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.unit
def test_create_task_success(
    client: TestClient, valid_task_data: Dict[str, Any]
) -> None:
    """Test successful task creation."""
    with mock_aws():
        response = client.post("/tasks", json=valid_task_data)

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "task_id" in data
        assert data["title"] == valid_task_data["title"]
        assert data["description"] == valid_task_data["description"]
        assert data["priority"] == valid_task_data["priority"]
        assert data["due_date"] == valid_task_data["due_date"]
        assert data["status"] == "queued"
        assert "created_at" in data


@pytest.mark.unit
def test_create_task_no_due_date(
    client: TestClient, valid_task_data_no_due_date: Dict[str, Any]
) -> None:
    """Test task creation without due date."""
    with mock_aws():
        response = client.post("/tasks", json=valid_task_data_no_due_date)

        assert response.status_code == 201
        data = response.json()

        assert "task_id" in data
        assert data["due_date"] is None


@pytest.mark.unit
def test_create_task_all_priorities(client: TestClient) -> None:
    """Test task creation with all priority levels."""
    priorities = ["low", "medium", "high"]

    with mock_aws():
        for priority in priorities:
            task_data = {
                "title": f"Task {priority}",
                "description": f"Task with {priority} priority",
                "priority": priority,
            }
            response = client.post("/tasks", json=task_data)

            assert response.status_code == 201
            data = response.json()
            assert data["priority"] == priority


@pytest.mark.unit
def test_create_task_missing_title(client: TestClient) -> None:
    """Test validation error for missing title."""
    invalid_data = {"description": "Test Description", "priority": "high"}

    response = client.post("/tasks", json=invalid_data)

    assert response.status_code == 400  # Validation error


@pytest.mark.unit
def test_create_task_missing_description(client: TestClient) -> None:
    """Test validation error for missing description."""
    invalid_data = {"title": "Test Title", "priority": "high"}

    response = client.post("/tasks", json=invalid_data)

    assert response.status_code == 400  # Validation error


@pytest.mark.unit
def test_create_task_missing_priority(client: TestClient) -> None:
    """Test validation error for missing priority."""
    invalid_data = {"title": "Test Title", "description": "Test Description"}

    response = client.post("/tasks", json=invalid_data)

    assert response.status_code == 400  # Validation error


@pytest.mark.unit
def test_create_task_invalid_priority(client: TestClient) -> None:
    """Test validation error for invalid priority."""
    invalid_data = {
        "title": "Test Title",
        "description": "Test Description",
        "priority": "urgent",  # Invalid - not in low/medium/high
    }

    response = client.post("/tasks", json=invalid_data)

    assert response.status_code == 400  # Validation error


@pytest.mark.unit
def test_create_task_empty_title(client: TestClient) -> None:
    """Test validation error for empty title."""
    invalid_data = {"title": "", "description": "Test Description", "priority": "high"}

    response = client.post("/tasks", json=invalid_data)

    assert response.status_code == 400  # Validation error


@pytest.mark.unit
def test_create_task_empty_description(client: TestClient) -> None:
    """Test validation error for empty description."""
    invalid_data = {"title": "Test Title", "description": "", "priority": "high"}

    response = client.post("/tasks", json=invalid_data)

    assert response.status_code == 400  # Validation error


@pytest.mark.unit
def test_create_task_title_too_long(client: TestClient) -> None:
    """Test validation error for title exceeding max length."""
    invalid_data = {
        "title": "x" * 201,  # Max is 200
        "description": "Test Description",
        "priority": "high",
    }

    response = client.post("/tasks", json=invalid_data)

    assert response.status_code == 400  # Validation error


@pytest.mark.unit
def test_create_task_description_too_long(client: TestClient) -> None:
    """Test validation error for description exceeding max length."""
    invalid_data = {
        "title": "Test Title",
        "description": "x" * 2001,  # Max is 2000
        "priority": "high",
    }

    response = client.post("/tasks", json=invalid_data)

    assert response.status_code == 400  # Validation error


@pytest.mark.unit
def test_create_task_whitespace_trimming(client: TestClient) -> None:
    """Test that whitespace is trimmed from title and description."""
    task_data = {
        "title": "  Test Title  ",
        "description": "  Test Description  ",
        "priority": "high",
    }

    with mock_aws():
        response = client.post("/tasks", json=task_data)

        assert response.status_code == 201
        data = response.json()

        # Whitespace should be trimmed
        assert data["title"] == "Test Title"
        assert data["description"] == "Test Description"


@pytest.mark.unit
def test_create_task_sqs_error_handling(
    client: TestClient, valid_task_data: Dict[str, Any]
) -> None:
    """Test error handling when SQS fails."""
    # Mock SQS send_message to raise exception
    with patch("boto3.client") as mock_boto_client:
        mock_sqs = MagicMock()
        mock_sqs.send_message.side_effect = Exception("SQS error")
        mock_boto_client.return_value = mock_sqs

        # Re-import to get patched client
        import importlib

        importlib.reload(index)

        test_client = TestClient(index.app)
        response = test_client.post("/tasks", json=valid_task_data)

        assert response.status_code == 500


@pytest.mark.unit
def test_create_task_generates_unique_ids(
    client: TestClient, valid_task_data: Dict[str, Any]
) -> None:
    """Test that each task gets a unique ID."""
    with mock_aws():
        response1 = client.post("/tasks", json=valid_task_data)
        response2 = client.post("/tasks", json=valid_task_data)

        assert response1.status_code == 201
        assert response2.status_code == 201

        data1 = response1.json()
        data2 = response2.json()

        # IDs should be different
        assert data1["task_id"] != data2["task_id"]


@pytest.mark.unit
def test_create_task_returns_created_at_timestamp(
    client: TestClient, valid_task_data: Dict[str, Any]
) -> None:
    """Test that task includes created_at timestamp."""
    with mock_aws():
        response = client.post("/tasks", json=valid_task_data)

        assert response.status_code == 201
        data = response.json()

        assert "created_at" in data
        # Verify it's a valid ISO 8601 timestamp
        from datetime import datetime

        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))


@pytest.mark.unit
def test_api_invalid_endpoint(client: TestClient) -> None:
    """Test 404 for invalid endpoint."""
    response = client.get("/invalid")

    assert response.status_code == 404


@pytest.mark.unit
def test_create_task_validates_json_content_type(client: TestClient) -> None:
    """Test that API expects JSON content type."""
    # Send invalid JSON
    response = client.post(
        "/tasks", content=b"not json", headers={"Content-Type": "application/json"}
    )

    # Should fail validation since content is not valid JSON
    assert response.status_code == 400


@pytest.mark.unit
def test_create_task_valid_iso8601_with_z(client: TestClient) -> None:
    """Test valid ISO 8601 date with Z suffix."""
    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "priority": "high",
        "due_date": "2026-01-15T12:00:00Z",
    }

    with mock_aws():
        response = client.post("/tasks", json=task_data)

        assert response.status_code == 201


@pytest.mark.unit
def test_create_task_valid_iso8601_with_timezone(client: TestClient) -> None:
    """Test valid ISO 8601 date with timezone offset."""
    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "priority": "high",
        "due_date": "2026-01-15T12:00:00+05:00",
    }

    with mock_aws():
        response = client.post("/tasks", json=task_data)

        assert response.status_code == 201


# ========================================
# API Authentication Tests (Bonus Feature)
# ========================================
@pytest.fixture
def authenticated_client(sqs_queue: str) -> TestClient:
    """Create FastAPI test client with API key authentication enabled."""
    os.environ["QUEUE_URL"] = sqs_queue
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ["ENABLE_API_KEY_CHECK"] = "true"
    os.environ["API_KEY"] = "test-api-key-12345"

    importlib.reload(index)
    return TestClient(index.app)


@pytest.mark.unit
def test_create_task_missing_api_key(
    authenticated_client: TestClient, valid_task_data: Dict[str, Any]
) -> None:
    """Test that request without API key is rejected."""
    with mock_aws():
        response = authenticated_client.post("/tasks", json=valid_task_data)

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert "Missing API Key" in data["message"]


@pytest.mark.unit
def test_create_task_invalid_api_key(
    authenticated_client: TestClient, valid_task_data: Dict[str, Any]
) -> None:
    """Test that request with invalid API key is rejected."""
    with mock_aws():
        response = authenticated_client.post(
            "/tasks",
            json=valid_task_data,
            headers={"x-api-key": "invalid-key-12345"},
        )

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert "Invalid API Key" in data["message"]


@pytest.mark.unit
def test_create_task_valid_api_key(
    authenticated_client: TestClient, valid_task_data: Dict[str, Any]
) -> None:
    """Test that request with valid API key succeeds."""
    with mock_aws():
        response = authenticated_client.post(
            "/tasks",
            json=valid_task_data,
            headers={"x-api-key": "test-api-key-12345"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"


@pytest.mark.unit
def test_health_endpoint_no_api_key_required(authenticated_client: TestClient) -> None:
    """Test that health endpoint doesn't require API key."""
    response = authenticated_client.get("/health")

    # Health endpoint should work without API key
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.unit
def test_docs_endpoint_no_api_key_required(authenticated_client: TestClient) -> None:
    """Test that docs endpoint doesn't require API key."""
    response = authenticated_client.get("/docs")

    # Docs endpoint should work without API key
    assert response.status_code == 200


@pytest.mark.unit
def test_api_key_validation_only_on_protected_endpoints(
    authenticated_client: TestClient, valid_task_data: Dict[str, Any]
) -> None:
    """Test that API key is only required for protected endpoints."""
    with mock_aws():
        # Health should work without key
        health_response = authenticated_client.get("/health")
        assert health_response.status_code == 200

        # Tasks endpoint should require key
        tasks_response = authenticated_client.post("/tasks", json=valid_task_data)
        assert tasks_response.status_code == 403

        # Tasks with valid key should work
        tasks_with_key = authenticated_client.post(
            "/tasks",
            json=valid_task_data,
            headers={"x-api-key": "test-api-key-12345"},
        )
        assert tasks_with_key.status_code == 201
