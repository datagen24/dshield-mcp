# health_check_manager

Health check manager for DShield MCP server dependencies.

## HealthCheckManager

Manages health checks for all dependencies.

#### __init__

```python
def __init__(self)
```

Initialize the health check manager.

#### get_health_summary

```python
def get_health_summary(self)
```

Get a summary of current health status.

        Returns:
            Dict[str, Any]: Health status summary

#### is_service_healthy

```python
def is_service_healthy(self, service_name)
```

Check if a specific service is healthy.

        Args:
            service_name: Name of the service to check

        Returns:
            bool: True if service is healthy, False otherwise

#### get_service_details

```python
def get_service_details(self, service_name)
```

Get detailed health information for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            Optional[Dict[str, Any]]: Service health details or None if not found
