Authentication
==============

The ETL Watcher SDK handles authentication automatically when deployed in cloud environments. The Watcher framework itself doesn't require authentication - instead, authentication is handled by the cloud provider (GCP, Azure, AWS) when your application is running in their managed services.

Overview
--------

The SDK automatically detects your cloud environment and configures the appropriate authentication method. You can also explicitly provide authentication credentials if needed.

Supported Cloud Environments
----------------------------

- **Google Cloud Platform (GCP)**: For GKE and Cloud Run deployments
- **Microsoft Azure**: For AKS and Container Instances  
- **Amazon Web Services (AWS)**: For EKS and ECS deployments
- **Local Development**: No authentication required

Basic Usage
-----------

The SDK automatically handles authentication when deployed in cloud environments:

.. code-block:: python

    from watcher import Watcher, PipelineConfig, Pipeline

    # Auto-detect cloud environment and configure authentication
    watcher = Watcher("https://api.watcher.com")
    
    # Use with OrchestratedETL
    pipeline_config = PipelineConfig(
        pipeline=Pipeline(name="my-pipeline", pipeline_type_name="etl"),
        default_watermark="2024-01-01"
    )
    
    from watcher import OrchestratedETL
    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

Explicit Authentication Configuration
------------------------------------

For local development or custom deployments, you can provide explicit credentials:

.. code-block:: python

    from watcher import Watcher

    # Bearer token for custom authentication
    watcher = Watcher("https://api.watcher.com", "your-bearer-token")

    # GCP service account file for local development
    watcher = Watcher("https://api.watcher.com", "/path/to/service-account.json")

Cloud-Specific Configuration
----------------------------

The SDK automatically detects and handles authentication for each cloud provider:

**Google Cloud Platform (GCP)**
- Uses metadata server for GKE/Cloud Run deployments
- Falls back to service account key files when provided

**Microsoft Azure**  
- Uses managed identity for AKS/Container Instances
- Falls back to service principal credentials

**Amazon Web Services (AWS)**
- Uses IAM roles for EKS/ECS deployments
- Falls back to environment variables

**Local Development**
- No authentication required
- Can provide bearer token or service account file for testing

Environment Variables
--------------------

The SDK can automatically detect cloud environments based on environment variables:

**GCP:**
- ``GOOGLE_APPLICATION_CREDENTIALS``: Path to service account key file

**Azure:**
- ``AZURE_TENANT_ID``: Azure tenant ID
- ``AZURE_CLIENT_ID``: Azure client ID
- ``AZURE_CLIENT_SECRET``: Azure client secret

**AWS:**
- ``AWS_ACCESS_KEY_ID``: AWS access key ID
- ``AWS_SECRET_ACCESS_KEY``: AWS secret access key
- ``AWS_SESSION_TOKEN``: AWS session token (optional)
- ``AWS_REGION``: AWS region

Installation with Cloud Dependencies
------------------------------------

To use cloud-specific authentication, install the appropriate optional dependencies:

.. code-block:: bash

    # Install all cloud dependencies
    pip install etl-watcher-sdk[cloud]

    # Install specific cloud provider dependencies
    pip install etl-watcher-sdk[gcp]    # For Google Cloud Platform
    pip install etl-watcher-sdk[azure]  # For Microsoft Azure
    pip install etl-watcher-sdk[aws]    # For Amazon Web Services

Orchestration Integration
-------------------------

The authentication system works seamlessly with orchestration frameworks:

.. code-block:: python

    from watcher import OrchestratedETL, PipelineConfig, Pipeline

    # Configure pipeline
    pipeline_config = PipelineConfig(
        pipeline=Pipeline(name="cloud-etl", pipeline_type_name="etl"),
        default_watermark="2024-01-01"
    )

    # Auto-detect authentication
    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # Or provide explicit credentials
    etl = OrchestratedETL("https://api.watcher.com", pipeline_config, "/path/to/service-account.json")

Error Handling
--------------

Authentication errors are raised as ``AuthenticationError`` exceptions:

.. code-block:: python

    from watcher import AuthenticationError, Watcher

    try:
        watcher = Watcher("https://api.watcher.com", "/path/to/service-account.json")
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")

Common Issues
-------------

1. **Missing Dependencies**: Ensure you have installed the appropriate cloud dependencies.

2. **Incorrect Credentials**: Verify that your service account or credentials have the necessary permissions.

3. **Network Access**: Ensure your deployment can access the cloud metadata servers or authentication endpoints.

4. **Token Expiry**: The SDK automatically refreshes tokens, but ensure your credentials are valid.

Best Practices
--------------

1. **Use Auto-Detection**: Let the SDK auto-detect your cloud environment when possible.

2. **Secure Credentials**: Store sensitive credentials in environment variables or secure key management systems.

3. **Minimal Permissions**: Use service accounts with minimal required permissions.

4. **Token Refresh**: The SDK handles token refresh automatically, but monitor for authentication failures.

5. **Error Handling**: Always handle ``AuthenticationError`` exceptions in your code.

Example: Complete Cloud Deployment
----------------------------------

Here's a complete example for a cloud deployment:

.. code-block:: python

    from watcher import OrchestratedETL, PipelineConfig, Pipeline

    def my_etl_function(watcher_context):
        # Your ETL logic here
        return ETLResult(completed_successfully=True, inserts=100)

    # Configure pipeline
    pipeline_config = PipelineConfig(
        pipeline=Pipeline(name="cloud-etl", pipeline_type_name="etl"),
        default_watermark="2024-01-01"
    )

    # Auto-detect and configure authentication
    etl = OrchestratedETL("https://api.watcher.com", pipeline_config)

    # Execute ETL with automatic authentication
    result = etl.execute_etl(my_etl_function)
    print(f"Execution completed: {result.result.completed_successfully}")

This example will automatically detect whether you're running on GCP, Azure, or AWS and configure the appropriate authentication method.