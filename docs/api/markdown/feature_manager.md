# feature_manager

Feature manager for DShield MCP server.

## FeatureManager

Manages feature availability based on dependency health.

#### __init__

```python
def __init__(self, health_manager)
```

Initialize the feature manager.

        Args:
            health_manager: Health check manager instance

#### is_feature_available

```python
def is_feature_available(self, feature)
```

Check if a feature is available.

        Args:
            feature: Name of the feature to check

        Returns:
            bool: True if feature is available, False otherwise

#### get_available_features

```python
def get_available_features(self)
```

Get list of available features.

        Returns:
            List[str]: List of available feature names

#### get_unavailable_features

```python
def get_unavailable_features(self)
```

Get list of unavailable features.

        Returns:
            List[str]: List of unavailable feature names

#### get_feature_dependencies

```python
def get_feature_dependencies(self, feature)
```

Get dependencies required for a feature.

        Args:
            feature: Name of the feature

        Returns:
            List[str]: List of dependency names

#### get_feature_details

```python
def get_feature_details(self, feature)
```

Get detailed information about a feature.

        Args:
            feature: Name of the feature

        Returns:
            Optional[Dict[str, Any]]: Feature details or None if not found

#### get_all_feature_details

```python
def get_all_feature_details(self)
```

Get details for all features.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of all feature details

#### get_feature_summary

```python
def get_feature_summary(self)
```

Get a summary of feature availability.

        Returns:
            Dict[str, Any]: Feature availability summary

#### refresh_feature_status

```python
def refresh_feature_status(self)
```

Refresh feature status based on current health checks.

        This method can be called to update feature availability
        without re-initializing the entire manager.

#### is_initialized

```python
def is_initialized(self)
```

Check if the feature manager has been initialized.

        Returns:
            bool: True if initialized, False otherwise
