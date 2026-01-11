import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as path from 'path';

export class CdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ========================================
    // 1. Dead Letter Queue (FIFO)
    // ========================================
    const deadLetterQueue = new sqs.Queue(this, 'TasksDLQ', {
      queueName: 'tasks-dlq.fifo',
      fifo: true,
      contentBasedDeduplication: true,
      retentionPeriod: cdk.Duration.days(14), // Keep failed messages for 14 days
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev/test purposes
    });

    // ========================================
    // 2. Main Task Queue (FIFO for ordering)
    // ========================================
    const taskQueue = new sqs.Queue(this, 'TaskQueue', {
      queueName: 'tasks.fifo',
      fifo: true,
      contentBasedDeduplication: true,
      visibilityTimeout: cdk.Duration.seconds(300), // 5 minutes
      retentionPeriod: cdk.Duration.days(4), // Keep messages for 4 days
      receiveMessageWaitTime: cdk.Duration.seconds(20), // Long polling
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: 3, // Retry up to 3 times before moving to DLQ
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev/test purposes
    });

    // ========================================
    // 3. API Lambda Function (Python)
    // ========================================
    const apiLambda = new lambda.Function(this, 'ApiLambda', {
      functionName: 'task-api-handler',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../src/api')),
      timeout: cdk.Duration.seconds(30),
      memorySize: 512,
      environment: {
        QUEUE_URL: taskQueue.queueUrl,
        LOG_LEVEL: 'INFO',
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
      tracing: lambda.Tracing.ACTIVE,
    });

    // Grant API Lambda permission to send messages to the queue
    taskQueue.grantSendMessages(apiLambda);

    // ========================================
    // 4. API Gateway REST API
    // ========================================
    const api = new apigateway.RestApi(this, 'TasksApi', {
      restApiName: 'Task Management API',
      description: 'API for managing tasks with ordered queue processing',
      deployOptions: {
        stageName: 'prod',
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: ['POST', 'OPTIONS'],
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token',
        ],
      },
    });

    // Create /tasks resource
    const tasksResource = api.root.addResource('tasks');

    // Add POST method to /tasks
    const apiIntegration = new apigateway.LambdaIntegration(apiLambda, {
      proxy: true,
      integrationResponses: [
        {
          statusCode: '200',
        },
        {
          statusCode: '400',
          selectionPattern: '.*\\[BadRequest\\].*',
        },
        {
          statusCode: '500',
          selectionPattern: '.*\\[InternalError\\].*',
        },
      ],
    });

    tasksResource.addMethod('POST', apiIntegration, {
      methodResponses: [
        { statusCode: '200' },
        { statusCode: '400' },
        { statusCode: '500' },
      ],
    });

    // ========================================
    // 5. Queue Processor Lambda Function
    // ========================================
    const processorLambda = new lambda.Function(this, 'ProcessorLambda', {
      functionName: 'task-processor-handler',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../src/processor')),
      timeout: cdk.Duration.seconds(300),
      memorySize: 512,
      environment: {
        LOG_LEVEL: 'INFO',
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
      tracing: lambda.Tracing.ACTIVE,
    });

    // Configure SQS event source for the processor Lambda
    const eventSource = new lambdaEventSources.SqsEventSource(taskQueue, {
      batchSize: 1, // Process one message at a time to maintain ordering
      reportBatchItemFailures: true, // Enable partial batch failure reporting
    });

    processorLambda.addEventSource(eventSource);

    // Grant processor Lambda permissions to receive and delete messages from queue
    taskQueue.grantConsumeMessages(processorLambda);

    // Grant processor Lambda permission to send to DLQ if needed (for custom error handling)
    deadLetterQueue.grantSendMessages(processorLambda);

    // ========================================
    // 6. Additional IAM Policies (Least Privilege)
    // ========================================
    
    // API Lambda only needs SendMessage permission (already granted above via grantSendMessages)
    // This includes: sqs:SendMessage, sqs:GetQueueAttributes, sqs:GetQueueUrl
    
    // Queue Processor Lambda only needs ReceiveMessage, DeleteMessage, ChangeMessageVisibility
    // (already granted above via grantConsumeMessages)
    
    // Add CloudWatch Logs permissions (implicitly added by CDK for Lambda functions)
    // Add X-Ray permissions (implicitly added when tracing is enabled)

    // ========================================
    // 7. Outputs
    // ========================================
    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: api.url,
      description: 'API Gateway endpoint URL',
      exportName: 'TaskApiEndpoint',
    });

    new cdk.CfnOutput(this, 'QueueUrl', {
      value: taskQueue.queueUrl,
      description: 'Task queue URL',
      exportName: 'TaskQueueUrl',
    });

    new cdk.CfnOutput(this, 'DLQUrl', {
      value: deadLetterQueue.queueUrl,
      description: 'Dead letter queue URL',
      exportName: 'TaskDLQUrl',
    });

    new cdk.CfnOutput(this, 'ApiLambdaArn', {
      value: apiLambda.functionArn,
      description: 'API Lambda function ARN',
      exportName: 'ApiLambdaArn',
    });

    new cdk.CfnOutput(this, 'ProcessorLambdaArn', {
      value: processorLambda.functionArn,
      description: 'Queue processor Lambda function ARN',
      exportName: 'ProcessorLambdaArn',
    });
  }
}
