# API Key Management Implementation

## Overview

This document describes the implementation of persistent API key management with 1Password integration for the DShield MCP server. The system provides secure, persistent storage of API keys with configurable permissions, expiration, and rate limiting.

## Architecture

### Components

1. **Secrets Abstraction Layer** (`src/secrets/`)
   - `BaseSecretsManager`: Abstract interface for secrets management providers
   - `APIKey`: Dataclass representing an API key with metadata
   - `OnePasswordCLIManager`: 1Password CLI implementation

2. **Enhanced API Key Management** (`src/op_secrets.py`)
   - `OnePasswordAPIKeyManager`: High-level API key management interface
   - Backward compatibility with existing `OnePasswordSecrets` class

3. **Server Integration** (`src/connection_manager.py`, `src/tcp_auth.py`)
   - Updated connection manager with persistent API key storage
   - Enhanced TCP authentication with dynamic key validation

4. **TUI Integration** (`src/tui/`)
   - API key generation dialog (`screens/api_key_screen.py`)
   - API key management panel (`api_key_panel.py`)
   - Enhanced connection panel with key management

5. **Configuration** (`src/user_config.py`)
   - New `APIKeyManagementSettings` class
   - User-configurable vault and default settings

## Key Features

### 1. Persistent Storage
- API keys are stored in 1Password using the `op` CLI
- Keys survive server restarts and are automatically loaded
- Structured storage with metadata (name, permissions, expiration)

### 2. Configurable Permissions
- **Read Tools**: Access to MCP tools and resources
- **Write Back**: Ability to write data back to Elasticsearch
- **Admin Access**: Server management and configuration
- **Rate Limiting**: Configurable requests per minute per key

### 3. Expiration Management
- Configurable expiration periods (30 days, 90 days, 1 year, never)
- Automatic validation of expired keys
- Optional auto-cleanup of expired keys

### 4. Security Features
- Secure key generation using `secrets.token_urlsafe()`
- No hardcoded secrets in configuration
- 1Password CLI authentication required
- Key revocation with session termination

### 5. TUI Management
- Visual API key generation with permission selection
- Key listing with status and expiration information
- Key deletion with confirmation
- Real-time updates and notifications

## Implementation Details

### Secrets Abstraction Layer

The abstraction layer provides a consistent interface for different secrets management providers:

```python
@dataclass
class APIKey:
    key_id: str
    key_value: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime]
    permissions: Dict[str, Any]
    metadata: Dict[str, Any]

class BaseSecretsManager(ABC):
    @abstractmethod
    async def store_api_key(self, api_key: APIKey) -> bool:
        pass
    
    @abstractmethod
    async def retrieve_api_key(self, key_id: str) -> Optional[APIKey]:
        pass
    
    @abstractmethod
    async def list_api_keys(self) -> List[APIKey]:
        pass
    
    @abstractmethod
    async def delete_api_key(self, key_id: str) -> bool:
        pass
    
    @abstractmethod
    async def update_api_key(self, api_key: APIKey) -> bool:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass
```

### 1Password CLI Integration

The `OnePasswordCLIManager` uses the `op` CLI exclusively:

```python
class OnePasswordCLIManager(BaseSecretsManager):
    def __init__(self, vault: str) -> None:
        self.vault = vault
        self._verify_op_cli()
    
    async def store_api_key(self, api_key: APIKey) -> bool:
        # Create structured item in 1Password
        item_data = {
            "title": f"dshield-mcp-key-{api_key.key_id}",
            "category": "API_CREDENTIAL",
            "vault": {"name": self.vault},
            "tags": ["dshield-mcp-api-key"],
            "fields": [
                {"id": "key_value", "type": "CONCEALED", "value": api_key.key_value},
                {"id": "key_name", "type": "STRING", "value": api_key.name},
                {"id": "permissions", "type": "STRING", "value": json.dumps(api_key.permissions)},
                # ... other fields
            ]
        }
        
        # Use op CLI to create item
        return self._run_op_command(['item', 'create', '--vault', self.vault, json.dumps(item_data)])
```

### Connection Manager Integration

The connection manager now uses the new API key management system:

```python
class ConnectionManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.api_key_manager = OnePasswordAPIKeyManager(
            vault=config.get("vault", "DShield-MCP") if config else "DShield-MCP"
        )
        # Load existing keys on startup
        asyncio.create_task(self._load_api_keys())
    
    async def generate_api_key(self, name: str, permissions: Optional[Dict[str, Any]] = None, 
                              expiration_days: Optional[int] = None, rate_limit: Optional[int] = None) -> Optional[APIKey]:
        # Generate key using the API key manager
        key_value = await self.api_key_manager.generate_api_key(
            name=name,
            permissions=permissions,
            expiration_days=expiration_days,
            rate_limit=rate_limit
        )
        
        if key_value:
            # Retrieve full key info and create local APIKey instance
            key_info = await self.api_key_manager.validate_api_key(key_value)
            if key_info:
                api_key = APIKey(
                    key_id=key_info["key_id"],
                    key_value=key_value,
                    permissions=key_info["permissions"],
                    expires_days=90
                )
                # Store in memory cache
                self.api_keys[key_value] = api_key
                return api_key
        
        return None
```

### TUI Integration

The TUI provides a user-friendly interface for API key management:

```python
class APIKeyGenerationScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Container(id="api-key-dialog"):
            yield Static("Generate API Key", id="title")
            
            with Vertical(id="form-container"):
                yield Label("Key Name:")
                yield Input(placeholder="Enter a name for this API key", id="key-name")
                
                yield Label("Permissions:")
                with Vertical(id="permissions-container"):
                    yield Checkbox("Read Tools", id="perm-read", value=True)
                    yield Checkbox("Write Back", id="perm-write")
                    yield Checkbox("Admin Access", id="perm-admin")
                
                yield Label("Rate Limit (requests per minute):")
                yield Input(placeholder="60", id="rate-limit", value="60")
                
                yield Label("Expiration:")
                yield Select([
                    ("30 days", 30),
                    ("90 days", 90),
                    ("1 year", 365),
                    ("Never", None)
                ], prompt="Select expiration period", id="expiration")
            
            with Horizontal(id="button-container"):
                yield Button("Generate", id="generate-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")
```

## Configuration

### User Configuration

The system supports comprehensive configuration through `user_config.yaml`:

```yaml
api_key_management:
  storage_provider: "1password_cli"  # Future: "vault_cli", "aws_secrets_cli"
  onepassword_cli:
    vault: "DShield-MCP"  # 1Password vault name
    cache_ttl: 60  # Cache refresh interval in seconds
    sync_interval: 60  # Sync interval in seconds
  defaults:
    expiration_days: 90  # Default expiration in days
    rate_limit_per_minute: 60  # Default rate limit
    permissions:
      read_tools: true
      write_back: false
      admin_access: false
  cache_ttl: 300  # Cache time-to-live in seconds
  auto_cleanup_expired: true  # Auto cleanup expired keys
```

### Environment Variables

The system respects existing environment variables and adds new ones:

```bash
# 1Password CLI configuration
OP_VAULT="DShield-MCP"  # Default vault name

# API key management
API_KEY_CACHE_TTL=300  # Cache TTL in seconds
API_KEY_SYNC_INTERVAL=60  # Sync interval in seconds
```

## Security Considerations

### 1. Key Generation
- Uses `secrets.token_urlsafe(32)` for cryptographically secure key generation
- Keys are prefixed with `dshield_` for identification
- UUID4 used for unique key IDs

### 2. Storage Security
- All keys stored in 1Password with structured metadata
- No keys stored in plain text or configuration files
- 1Password CLI authentication required for access

### 3. Access Control
- Permission-based access control with granular permissions
- Rate limiting per key to prevent abuse
- Expiration enforcement with automatic validation

### 4. Session Management
- Active sessions terminated when keys are revoked
- Key validation on each request with caching for performance
- Graceful handling of expired or invalid keys

## Usage Examples

### Generating an API Key

```python
from src.op_secrets import OnePasswordAPIKeyManager

# Initialize the API key manager
api_key_manager = OnePasswordAPIKeyManager("DShield-MCP")

# Generate a new API key
key_value = await api_key_manager.generate_api_key(
    name="Development Key",
    permissions={
        "read_tools": True,
        "write_back": False,
        "admin_access": False,
        "rate_limit": 60
    },
    expiration_days=90,
    rate_limit=60
)

print(f"Generated API key: {key_value}")
```

### Validating an API Key

```python
# Validate an API key
key_info = await api_key_manager.validate_api_key(key_value)

if key_info:
    print(f"Valid key: {key_info['name']}")
    print(f"Permissions: {key_info['permissions']}")
    print(f"Expires: {key_info['expires_at']}")
else:
    print("Invalid or expired key")
```

### Listing API Keys

```python
# List all API keys
keys = await api_key_manager.list_api_keys()

for key in keys:
    print(f"Key: {key['name']} ({key['key_id']})")
    print(f"Created: {key['created_at']}")
    print(f"Expires: {key['expires_at'] or 'Never'}")
    print(f"Status: {'Active' if not key['is_expired'] else 'Expired'}")
    print("---")
```

### Deleting an API Key

```python
# Delete an API key
success = await api_key_manager.delete_api_key("key_id_here")

if success:
    print("API key deleted successfully")
else:
    print("Failed to delete API key")
```

## Testing

The implementation includes comprehensive tests:

### Unit Tests
- `tests/secrets/test_base_secrets_manager.py`: Tests for the abstraction layer
- `tests/secrets/test_onepassword_cli_manager.py`: Tests for 1Password CLI integration

### Integration Tests
- `tests/test_api_key_persistence.py`: End-to-end tests for API key persistence

### Test Coverage
- All public methods tested with success and failure scenarios
- Mock implementations for external dependencies
- Error handling and edge case testing

## Future Enhancements

### 1. Additional Secrets Managers
- HashiCorp Vault integration
- AWS Secrets Manager support
- Azure Key Vault integration

### 2. Advanced Features
- Key rotation and renewal
- Audit logging and compliance
- Multi-vault support
- Key sharing and delegation

### 3. Performance Optimizations
- Redis caching for high-traffic scenarios
- Batch operations for bulk key management
- Connection pooling for external services

## Troubleshooting

### Common Issues

1. **1Password CLI Not Found**
   ```
   Error: op CLI not found. Install from https://1password.com/downloads/command-line
   ```
   Solution: Install the 1Password CLI and ensure it's in your PATH

2. **Authentication Required**
   ```
   Error: op CLI not authenticated. Run 'op signin' to authenticate
   ```
   Solution: Run `op signin` to authenticate with your 1Password account

3. **Vault Not Found**
   ```
   Error: op command failed: vault not found
   ```
   Solution: Verify the vault name in your configuration and ensure you have access

4. **Key Generation Failed**
   ```
   Error: Failed to generate API key
   ```
   Solution: Check 1Password CLI connectivity and vault permissions

### Debug Mode

Enable debug logging to troubleshoot issues:

```yaml
logging:
  log_level: "DEBUG"
  enable_query_logging: true
```

### Health Checks

Use the health check functionality to verify system status:

```python
# Check if the API key manager is healthy
is_healthy = await api_key_manager.health_check()
print(f"API key manager healthy: {is_healthy}")
```

## Conclusion

The API key management implementation provides a robust, secure, and user-friendly system for managing API keys in the DShield MCP server. The abstraction layer ensures future extensibility, while the 1Password integration provides enterprise-grade security. The TUI integration makes key management accessible to all users, and comprehensive testing ensures reliability.

The system is production-ready and provides all the features needed for secure API key lifecycle management in a DShield SIEM environment.
