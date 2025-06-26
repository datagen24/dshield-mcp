#!/usr/bin/env python3
"""
Configuration script for DShield MCP - Elastic SIEM Integration
Helps users set up environment variables and test connections.
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv, set_key

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from elasticsearch_client import ElasticsearchClient
from dshield_client import DShieldClient


class ConfigManager:
    """Manage configuration for DShield MCP."""
    
    def __init__(self):
        self.env_file = Path(".env")
        self.env_example = Path("env.example")
        
    def setup_environment(self):
        """Interactive setup of environment variables."""
        print("=== DShield MCP Configuration Setup ===\n")
        
        # Create .env file if it doesn't exist
        if not self.env_file.exists():
            if self.env_example.exists():
                print("Creating .env file from template...")
                with open(self.env_example, 'r') as f:
                    template = f.read()
                with open(self.env_file, 'w') as f:
                    f.write(template)
            else:
                print("Creating new .env file...")
                self._create_default_env()
        
        # Load current environment
        load_dotenv()
        
        # Configure Elasticsearch
        print("=== Elasticsearch Configuration ===")
        self._configure_elasticsearch()
        
        # Configure DShield
        print("\n=== DShield Configuration ===")
        self._configure_dshield()
        
        # Configure MCP Server
        print("\n=== MCP Server Configuration ===")
        self._configure_mcp_server()
        
        # Configure Security Settings
        print("\n=== Security Configuration ===")
        self._configure_security()
        
        print("\n=== Configuration Complete ===")
        print("You can now run the MCP server with: python mcp_server.py")
        
    def _create_default_env(self):
        """Create default .env file."""
        default_config = """# Elasticsearch Configuration
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=
ELASTICSEARCH_VERIFY_SSL=true
ELASTICSEARCH_CA_CERTS=

# DShield API Configuration
DSHIELD_API_KEY=
DSHIELD_API_URL=https://dshield.org/api

# MCP Server Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8000
MCP_SERVER_DEBUG=false

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security Configuration
RATE_LIMIT_REQUESTS_PER_MINUTE=60
MAX_QUERY_RESULTS=1000
QUERY_TIMEOUT_SECONDS=30

# Data Processing Configuration
DEFAULT_TIME_RANGE_HOURS=24
MAX_IP_ENRICHMENT_BATCH_SIZE=100
CACHE_TTL_SECONDS=300

# Optional: Proxy Configuration
HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=localhost,127.0.0.1
"""
        with open(self.env_file, 'w') as f:
            f.write(default_config)
    
    def _configure_elasticsearch(self):
        """Configure Elasticsearch settings."""
        current_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        url = input(f"Elasticsearch URL [{current_url}]: ").strip()
        if url:
            set_key(self.env_file, "ELASTICSEARCH_URL", url)
        
        current_username = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
        username = input(f"Elasticsearch Username [{current_username}]: ").strip()
        if username:
            set_key(self.env_file, "ELASTICSEARCH_USERNAME", username)
        
        password = input("Elasticsearch Password (leave empty if none): ").strip()
        if password:
            set_key(self.env_file, "ELASTICSEARCH_PASSWORD", password)
        
        verify_ssl = input("Verify SSL certificates? (y/n) [y]: ").strip().lower()
        if verify_ssl in ['n', 'no']:
            set_key(self.env_file, "ELASTICSEARCH_VERIFY_SSL", "false")
        else:
            set_key(self.env_file, "ELASTICSEARCH_VERIFY_SSL", "true")
    
    def _configure_dshield(self):
        """Configure DShield API settings."""
        current_url = os.getenv("DSHIELD_API_URL", "https://dshield.org/api")
        url = input(f"DShield API URL [{current_url}]: ").strip()
        if url:
            set_key(self.env_file, "DSHIELD_API_URL", url)
        
        api_key = input("DShield API Key (optional): ").strip()
        if api_key:
            set_key(self.env_file, "DSHIELD_API_KEY", api_key)
    
    def _configure_mcp_server(self):
        """Configure MCP server settings."""
        current_host = os.getenv("MCP_SERVER_HOST", "localhost")
        host = input(f"MCP Server Host [{current_host}]: ").strip()
        if host:
            set_key(self.env_file, "MCP_SERVER_HOST", host)
        
        current_port = os.getenv("MCP_SERVER_PORT", "8000")
        port = input(f"MCP Server Port [{current_port}]: ").strip()
        if port:
            set_key(self.env_file, "MCP_SERVER_PORT", port)
        
        debug = input("Enable debug mode? (y/n) [n]: ").strip().lower()
        if debug in ['y', 'yes']:
            set_key(self.env_file, "MCP_SERVER_DEBUG", "true")
        else:
            set_key(self.env_file, "MCP_SERVER_DEBUG", "false")
    
    def _configure_security(self):
        """Configure security settings."""
        current_rate_limit = os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60")
        rate_limit = input(f"Rate limit (requests per minute) [{current_rate_limit}]: ").strip()
        if rate_limit and rate_limit.isdigit():
            set_key(self.env_file, "RATE_LIMIT_REQUESTS_PER_MINUTE", rate_limit)
        
        current_max_results = os.getenv("MAX_QUERY_RESULTS", "1000")
        max_results = input(f"Maximum query results [{current_max_results}]: ").strip()
        if max_results and max_results.isdigit():
            set_key(self.env_file, "MAX_QUERY_RESULTS", max_results)
    
    async def test_connections(self):
        """Test connections to Elasticsearch and DShield."""
        print("=== Testing Connections ===\n")
        
        # Load environment
        load_dotenv()
        
        # Test Elasticsearch
        print("Testing Elasticsearch connection...")
        try:
            es_client = ElasticsearchClient()
            await es_client.connect()
            
            # Get cluster info
            info = await es_client.cluster.info()
            print(f"✓ Connected to Elasticsearch cluster: {info['cluster_name']}")
            print(f"  Version: {info['version']['number']}")
            
            # Test query
            try:
                events = await es_client.query_security_events(time_range_hours=1, size=1)
                print(f"✓ Successfully queried {len(events)} security events")
            except Exception as e:
                print(f"⚠ Query test failed: {str(e)}")
            
            await es_client.close()
            
        except Exception as e:
            print(f"✗ Elasticsearch connection failed: {str(e)}")
        
        # Test DShield
        print("\nTesting DShield API connection...")
        try:
            dshield_client = DShieldClient()
            await dshield_client.connect()
            
            # Test with a known IP (Google DNS)
            test_ip = "8.8.8.8"
            reputation = await dshield_client.get_ip_reputation(test_ip)
            
            if reputation.get('reputation_score') is not None:
                print(f"✓ Successfully queried DShield for IP {test_ip}")
                print(f"  Reputation score: {reputation.get('reputation_score')}")
            else:
                print(f"✓ DShield API responded (no reputation data for {test_ip})")
            
            await dshield_client.close()
            
        except Exception as e:
            print(f"✗ DShield connection failed: {str(e)}")
        
        print("\n=== Connection Test Complete ===")
    
    def show_configuration(self):
        """Show current configuration (without sensitive data)."""
        print("=== Current Configuration ===")
        
        load_dotenv()
        
        config = {
            "Elasticsearch": {
                "URL": os.getenv("ELASTICSEARCH_URL"),
                "Username": os.getenv("ELASTICSEARCH_USERNAME"),
                "Verify SSL": os.getenv("ELASTICSEARCH_VERIFY_SSL"),
            },
            "DShield": {
                "API URL": os.getenv("DSHIELD_API_URL"),
                "API Key": "***" if os.getenv("DSHIELD_API_KEY") else "Not set",
            },
            "MCP Server": {
                "Host": os.getenv("MCP_SERVER_HOST"),
                "Port": os.getenv("MCP_SERVER_PORT"),
                "Debug": os.getenv("MCP_SERVER_DEBUG"),
            },
            "Security": {
                "Rate Limit": os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE"),
                "Max Results": os.getenv("MAX_QUERY_RESULTS"),
                "Query Timeout": os.getenv("QUERY_TIMEOUT_SECONDS"),
            }
        }
        
        for section, settings in config.items():
            print(f"\n{section}:")
            for key, value in settings.items():
                print(f"  {key}: {value}")
    
    def validate_configuration(self) -> bool:
        """Validate configuration and return True if valid."""
        print("=== Validating Configuration ===")
        
        load_dotenv()
        
        errors = []
        
        # Check required fields
        required_fields = [
            ("ELASTICSEARCH_URL", "Elasticsearch URL"),
            ("ELASTICSEARCH_USERNAME", "Elasticsearch Username"),
        ]
        
        for env_var, name in required_fields:
            if not os.getenv(env_var):
                errors.append(f"Missing required field: {name}")
        
        # Check URL formats
        es_url = os.getenv("ELASTICSEARCH_URL")
        if es_url and not (es_url.startswith("http://") or es_url.startswith("https://")):
            errors.append("Elasticsearch URL must start with http:// or https://")
        
        dshield_url = os.getenv("DSHIELD_API_URL")
        if dshield_url and not (dshield_url.startswith("http://") or dshield_url.startswith("https://")):
            errors.append("DShield API URL must start with http:// or https://")
        
        # Check numeric fields
        numeric_fields = [
            ("RATE_LIMIT_REQUESTS_PER_MINUTE", "Rate Limit"),
            ("MAX_QUERY_RESULTS", "Max Query Results"),
            ("QUERY_TIMEOUT_SECONDS", "Query Timeout"),
        ]
        
        for env_var, name in numeric_fields:
            value = os.getenv(env_var)
            if value and not value.isdigit():
                errors.append(f"{name} must be a number")
        
        if errors:
            print("Configuration errors found:")
            for error in errors:
                print(f"  ✗ {error}")
            return False
        else:
            print("✓ Configuration is valid")
            return True


def main():
    """Main function for configuration script."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python config.py setup     - Interactive configuration setup")
        print("  python config.py test      - Test connections")
        print("  python config.py show      - Show current configuration")
        print("  python config.py validate  - Validate configuration")
        return
    
    config_manager = ConfigManager()
    command = sys.argv[1].lower()
    
    if command == "setup":
        config_manager.setup_environment()
    elif command == "test":
        asyncio.run(config_manager.test_connections())
    elif command == "show":
        config_manager.show_configuration()
    elif command == "validate":
        config_manager.validate_configuration()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: setup, test, show, validate")


if __name__ == "__main__":
    main() 