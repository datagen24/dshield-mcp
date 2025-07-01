import os
import yaml
from .op_secrets import OnePasswordSecrets

class ConfigError(Exception):
    pass

def get_config(config_path: str = None) -> dict:
    """
    Load the MCP YAML config file. Raise ConfigError if missing or invalid.
    By default, looks for 'mcp_config.yaml' in the project root.
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mcp_config.yaml')
    if not os.path.exists(config_path):
        raise ConfigError(f"Config file not found: {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ConfigError("Config file is not a valid YAML mapping.")
        
        # Resolve secrets using 1Password CLI
        config = _resolve_secrets(config)
        
        return config
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}")

def _resolve_secrets(config: dict) -> dict:
    """
    Recursively resolve op:// URLs in config values using 1Password CLI.
    """
    op_secrets = OnePasswordSecrets()
    
    def _resolve_value(value):
        if isinstance(value, str):
            return op_secrets.resolve_environment_variable(value)
        elif isinstance(value, dict):
            return {k: _resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_resolve_value(v) for v in value]
        else:
            return value
    
    return _resolve_value(config) 