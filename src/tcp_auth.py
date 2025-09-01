#!/usr/bin/env python3
"""TCP authentication system for DShield MCP Server.

This module provides authentication functionality for TCP connections,
including API key validation, permission checking, and session management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import structlog

from .connection_manager import ConnectionManager, APIKey
from .mcp_error_handler import MCPErrorHandler

logger = structlog.get_logger(__name__)


class AuthenticationError(Exception):
    """Exception raised for authentication-related errors.
    
    Attributes:
        error_code: JSON-RPC error code
        message: Error message
        details: Additional error details
    """
    
    def __init__(self, error_code: int, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize authentication error.
        
        Args:
            error_code: JSON-RPC error code
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class TCPAuthenticator:
    """Handles authentication for TCP connections.
    
    This class manages API key validation, permission checking, and
    session management for TCP-based MCP connections.
    
    Attributes:
        connection_manager: Connection manager instance
        error_handler: MCP error handler instance
        sessions: Active authentication sessions
        config: Authentication configuration
    """
    
    def __init__(self, connection_manager: ConnectionManager, 
                 error_handler: MCPErrorHandler,
                 config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the TCP authenticator.
        
        Args:
            connection_manager: Connection manager instance
            error_handler: MCP error handler instance
            config: Authentication configuration
        """
        self.connection_manager = connection_manager
        self.error_handler = error_handler
        self.config = config or {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Session configuration
        self.session_timeout = self.config.get("session_timeout_seconds", 3600)  # 1 hour
        self.max_sessions_per_key = self.config.get("max_sessions_per_key", 5)
    
    async def authenticate_connection(self, connection: Any, 
                                   auth_message: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate a TCP connection.
        
        Args:
            connection: The TCP connection object
            auth_message: Authentication message from client
            
        Returns:
            Authentication result with session information
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Extract API key from authentication message
            api_key = auth_message.get("api_key")
            if not api_key:
                raise AuthenticationError(
                    -32602,  # INVALID_PARAMS
                    "API key is required for authentication",
                    {"missing_field": "api_key"}
                )
            
            # Validate API key
            api_key_obj = await self.connection_manager.validate_api_key(api_key)
            if not api_key_obj:
                raise AuthenticationError(
                    -32001,  # RESOURCE_NOT_FOUND
                    "Invalid or expired API key",
                    {"api_key": api_key[:8] + "..."}
                )
            
            # Check session limits
            if not self._check_session_limits(api_key):
                raise AuthenticationError(
                    -32008,  # RATE_LIMIT_ERROR
                    "Maximum sessions per API key exceeded",
                    {"max_sessions": self.max_sessions_per_key}
                )
            
            # Create session
            session_id = self._create_session(connection, api_key_obj)
            
            # Update connection with authentication info
            connection.api_key = api_key
            connection.is_authenticated = True
            connection.session_id = session_id
            
            self.logger.info("Connection authenticated successfully",
                           client_address=connection.client_address,
                           api_key_id=api_key_obj.key_id,
                           session_id=session_id)
            
            return {
                "authenticated": True,
                "session_id": session_id,
                "permissions": api_key_obj.permissions,
                "expires_at": api_key_obj.expires_at.isoformat()
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error("Authentication error", 
                            client_address=connection.client_address, error=str(e))
            raise AuthenticationError(
                -32603,  # INTERNAL_ERROR
                "Authentication failed due to internal error",
                {"error": str(e)}
            )
    
    def _check_session_limits(self, api_key: str) -> bool:
        """Check if session limits are exceeded for an API key.
        
        Args:
            api_key: The API key to check
            
        Returns:
            True if session limits are not exceeded, False otherwise
        """
        # Count active sessions for this API key
        active_sessions = sum(
            1 for session in self.sessions.values()
            if session.get("api_key") == api_key and not self._is_session_expired(session)
        )
        
        return active_sessions < self.max_sessions_per_key
    
    def _create_session(self, connection: Any, api_key_obj: APIKey) -> str:
        """Create a new authentication session.
        
        Args:
            connection: The TCP connection
            api_key_obj: The validated API key object
            
        Returns:
            Session ID for the new session
        """
        import secrets
        
        session_id = f"session_{secrets.token_hex(16)}"
        
        self.sessions[session_id] = {
            "session_id": session_id,
            "api_key": api_key_obj.key_value,
            "api_key_id": api_key_obj.key_id,
            "permissions": api_key_obj.permissions,
            "client_address": connection.client_address,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "connection": connection
        }
        
        return session_id
    
    def _is_session_expired(self, session: Dict[str, Any]) -> bool:
        """Check if a session has expired.
        
        Args:
            session: Session dictionary
            
        Returns:
            True if session has expired, False otherwise
        """
        last_activity = session.get("last_activity")
        if not last_activity:
            return True
        
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity)
        
        return (datetime.utcnow() - last_activity).total_seconds() > self.session_timeout
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate an authentication session.
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            Session information if valid, None if invalid
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        if self._is_session_expired(session):
            # Remove expired session
            del self.sessions[session_id]
            return None
        
        # Update last activity
        session["last_activity"] = datetime.utcnow()
        return session
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke an authentication session.
        
        Args:
            session_id: Session ID to revoke
            
        Returns:
            True if session was revoked, False if not found
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            self.logger.info("Session revoked",
                           session_id=session_id,
                           client_address=session.get("client_address"))
            del self.sessions[session_id]
            return True
        return False
    
    def revoke_all_sessions_for_key(self, api_key: str) -> int:
        """Revoke all sessions for a specific API key.
        
        Args:
            api_key: API key to revoke sessions for
            
        Returns:
            Number of sessions revoked
        """
        sessions_to_revoke = [
            session_id for session_id, session in self.sessions.items()
            if session.get("api_key") == api_key
        ]
        
        for session_id in sessions_to_revoke:
            self.revoke_session(session_id)
        
        if sessions_to_revoke:
            self.logger.info("Revoked all sessions for API key",
                           api_key=api_key[:8] + "...",
                           session_count=len(sessions_to_revoke))
        
        return len(sessions_to_revoke)
    
    def check_permission(self, session_id: str, permission: str) -> bool:
        """Check if a session has a specific permission.
        
        Args:
            session_id: Session ID to check
            permission: Permission to check
            
        Returns:
            True if permission is granted, False otherwise
        """
        session = self.validate_session(session_id)
        if not session:
            return False
        
        permissions = session.get("permissions", {})
        return permissions.get(permission, False)
    
    def check_tool_permission(self, session_id: str, tool_name: str) -> bool:
        """Check if a session has permission to use a specific tool.
        
        Args:
            session_id: Session ID to check
            tool_name: Tool name to check
            
        Returns:
            True if tool permission is granted, False otherwise
        """
        session = self.validate_session(session_id)
        if not session:
            return False
        
        permissions = session.get("permissions", {})
        allowed_tools = permissions.get("allowed_tools", [])
        blocked_tools = permissions.get("blocked_tools", [])
        
        # If blocked_tools contains the tool, deny access
        if tool_name in blocked_tools:
            return False
        
        # If allowed_tools is empty, allow all tools (except blocked ones)
        if not allowed_tools:
            return True
        
        # Check if tool is in allowed_tools
        return tool_name in allowed_tools
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session information if valid, None if invalid
        """
        session = self.validate_session(session_id)
        if not session:
            return None
        
        # Return sanitized session info
        return {
            "session_id": session["session_id"],
            "api_key_id": session["api_key_id"],
            "permissions": session["permissions"],
            "client_address": session["client_address"],
            "created_at": session["created_at"].isoformat(),
            "last_activity": session["last_activity"].isoformat()
        }
    
    def get_all_sessions_info(self) -> List[Dict[str, Any]]:
        """Get information about all active sessions.
        
        Returns:
            List of session information dictionaries
        """
        active_sessions = []
        
        for session_id, session in list(self.sessions.items()):
            if not self._is_session_expired(session):
                active_sessions.append(self.get_session_info(session_id))
            else:
                # Clean up expired session
                del self.sessions[session_id]
        
        return [s for s in active_sessions if s is not None]
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if self._is_session_expired(session)
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            self.logger.info("Cleaned up expired sessions", count=len(expired_sessions))
        
        return len(expired_sessions)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get authentication statistics.
        
        Returns:
            Dictionary of authentication statistics
        """
        total_sessions = len(self.sessions)
        active_sessions = len([s for s in self.sessions.values() if not self._is_session_expired(s)])
        expired_sessions = total_sessions - active_sessions
        
        return {
            "sessions": {
                "total": total_sessions,
                "active": active_sessions,
                "expired": expired_sessions
            },
            "session_timeout": self.session_timeout,
            "max_sessions_per_key": self.max_sessions_per_key,
            "last_cleanup": datetime.utcnow().isoformat()
        }
