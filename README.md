# Backend Engineering Challenge

Welcome to our backend engineering challenge! This project is designed to assess your skills in **Python**, **TypeScript**, **AWS**, and **AWS CDK**.

## Overview

You will build a task management API system with these components:
- AWS CDK infrastructure deployment
- REST API endpoint for task creation
- Message queue with ordered processing
- Background task processor

## Challenge Requirements

### 1. Infrastructure as Code (AWS CDK)

Create AWS CDK stacks that deploy your entire infrastructure:

#### Stack Components
- Compute resources (Python for all backend logic)
- REST API with single POST endpoint
- Message queue for ordered task processing
- Logging and basic monitoring

#### Requirements
- Use AWS CDK v2 with TypeScript
- Implement proper stack organization (separate stacks for different concerns)
- Include environment-specific configurations
- Document deployment process
- **Must support `cdk synth` command to validate infrastructure code**
- **No hardcoded account IDs, regions, or environment-specific values**
- **Infrastructure should be deployable but actual deployment is not required for evaluation**

### 2. Core API (Python)

Create a REST API endpoint using Python:

#### Endpoint
- `POST /tasks` - Accept and validate a new task, then send it to a processing queue

#### Task Model
```json
{
  "title": "string",
  "description": "string",
  "priority": "low | medium | high",
  "due_date": "ISO 8601 timestamp (optional)"
}
```

#### Requirements
- Choose appropriate AWS compute services for the API
- Implement comprehensive input validation and sanitization
- Send validated tasks to a message queue that preserves ordering
- Return a unique task id to the requester
- Ensure at-least-once delivery guarantees
- Implement proper error handling and return appropriate HTTP status codes
- Include unit tests using pytest
- Use type hints throughout your Python code

### 3. Queue Processing System (Python)

Create a queue processing system using Python that:

#### Functionality
- Processes tasks from the queue *in the order they were received*
- Implements at-least-once processing guarantees
- Implements proper retry logic and dead letter handling for failed processing of tasks
- Maintains ordering guarantees even with retries

#### Requirements
- Use Python with proper type hints
- Choose appropriate AWS compute services for queue processing
- Implement dead letter queue for failed messages
- Include comprehensive error handling and logging
- Include unit tests using pytest
- Ensure idempotent processing to handle duplicate deliveries

### 4. Documentation and Best Practices

#### Code Quality
- **Python code must be formatted using a documented formatter (e.g., black, autopep8, ruff)**
- **Python code should pass standard type check from pyright**
- Follow TypeScript/ESLint best practices for CDK infrastructure code
- Include comprehensive README files
- Implement proper logging

#### Testing
- Unit tests for all business logic
- Integration tests for REST endpoints using mocked AWS services
- Mock external dependencies appropriately (use moto, localstack, or similar for AWS mocking)
- **Achieve 90% test coverage for Python code using pytest**

#### Security
- Implement input validation and sanitization
- Use environment variables for configuration
- Follow AWS security best practices
- **Implement least privilege access controls for all AWS resources**
- Implement proper CORS configuration

## Architecture Focus

Your solution should demonstrate:

- **Ordering Guarantees**: Tasks must be processed in the exact order they are received
- **At-Least-Once Processing**: Every valid task must be processed at least once
- **Error Handling**: Robust error handling with appropriate retries and dead letter queues
- **Validation**: Comprehensive input validation before queueing tasks

## Getting Started

1. **Create a private fork of this repository** to your own GitHub account
2. **Set up your development environment** with AWS CDK, Python, and necessary dependencies
3. **Implement the solution** following the requirements
4. **Test thoroughly** and ensure all tests pass (use mocks for AWS services)
5. **Validate CDK synthesis** by running `cdk synth` to ensure infrastructure code is valid
6. **Document your solution** including setup and deployment instructions
7. **Zip the repository** and deliver it to the hiring manager.

## Evaluation Criteria

You will be evaluated in the following order of priority:

### Infrastructure Validity and Functionality
- **CDK infrastructure synthesizes successfully** using `cdk synth` without errors
- **API endpoint logic works as expected** - accepts valid tasks and handles errors properly (tested with mocks)
- **Queue processing system functions correctly** - processes tasks in order with proper retry logic (tested with mocks)
- **All components integrate properly** - end-to-end functionality works with mocked AWS services

### Code Quality and Testing
- **Code quality** - Clean, readable, well-structured Python and TypeScript code
- **Test coverage** - Comprehensive test suite with full coverage as specified
- **Type safety** - Proper type hints and passes pyright type checking
- **Code formatting** - Consistent formatting using documented formatter

### Additional Considerations
- **Architecture** - Proper separation of concerns and scalable design
- **Security** - Least privilege access controls and input validation
- **Documentation** - Clear setup instructions and architectural decisions
- **AWS best practices** - Effective use of AWS services and patterns

## Bonus Points

- Implement API authentication
- Add comprehensive monitoring and observability
- Implement CI/CD pipeline
- Add API rate limiting and throttling

## Time Expectation

This challenge is designed to take approximately **1-2 hours** to complete. Focus on demonstrating your understanding of the core technologies rather than implementing every possible feature. **No actual AWS deployment is required** - the evaluation focuses on code quality, architecture, and the ability to synthesize valid CloudFormation templates.

## Questions?

If you have any questions about the requirements or need clarification on any aspect of the challenge, please create an issue in this repository or reach out to your point of contact.

Good luck! 🚀