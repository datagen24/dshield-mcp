"""
Security validation module for DShield MCP server.

This module provides security validation for MCP tools, including:
- Tool description validation
- Parameter schema validation
- Input sanitization checks
- Security monitoring and logging
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SecurityRiskLevel(Enum):
    """Security risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityIssue:
    """Represents a security issue found during validation."""
    issue_type: str
    severity: SecurityRiskLevel
    description: str
    location: str
    details: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['severity'] = self.severity.value
        return data


class SecurityValidator:
    """Security validation for MCP tools and parameters."""
    
    def __init__(self, enable_logging: bool = True):
        """
        Initialize security validator.
        
        Args:
            enable_logging: Whether to enable security logging
        """
        self.enable_logging = enable_logging
        self.issues: List[SecurityIssue] = []
        
        # Patterns for detecting security issues
        self.sensitive_patterns = [
            r'~/.ssh',
            r'~?\.env',  # Match both ~/.env and .env
            r'config\.json',
            r'id_rsa',
            r'password',
            r'secret',
            r'key',
            r'\.pem',
            r'\.key',
            r'\.crt',
            r'\.p12',
            r'\.pfx'
        ]
        
        # Separate patterns for exact matching (including ~)
        self.sensitive_exact_patterns = [
            r'~/.ssh',
            r'~/.env',
            r'\.env',
            r'config\.json',
            r'id_rsa',
            r'password',
            r'secret',
            r'key',
            r'\.pem',
            r'\.key',
            r'\.crt',
            r'\.p12',
            r'\.pfx'
        ]
        
        self.hidden_instruction_patterns = [
            r'<instructions>',
            r'<secret>',
            r'<system>',
            r'<hidden>',
            r'hidden',
            r'secret',
            r'do not mention',
            r'do not tell',
            r'never inform',
            r'keep secret',
            r'confidential'
        ]
        
        self.suspicious_parameters = [
            'feedback',
            'debug',
            'extra',
            'metadata',
            'notes',
            'comments',
            'description',
            'details',
            'context',
            'payload',
            'data',
            'content'
        ]
        
        self.tool_shadowing_patterns = [
            r'when.*tool.*is.*available',
            r'modify.*behavior.*of',
            r'change.*recipient.*to',
            r'proxy.*number',
            r'relay.*messages',
            r'intercept.*messages',
            r'override.*behavior'
        ]
        
        # Compile patterns for better performance
        self.sensitive_regex = re.compile('|'.join(self.sensitive_patterns), re.IGNORECASE)
        self.sensitive_exact_regex = re.compile('|'.join(self.sensitive_exact_patterns), re.IGNORECASE)
        self.hidden_instruction_regex = re.compile('|'.join(self.hidden_instruction_patterns), re.IGNORECASE)
        self.tool_shadowing_regex = re.compile('|'.join(self.tool_shadowing_patterns), re.IGNORECASE)
    
    def validate_tool_description(self, tool_name: str, description: str) -> List[SecurityIssue]:
        """
        Validate tool description for security issues.
        
        Args:
            tool_name: Name of the tool being validated
            description: Tool description to validate
            
        Returns:
            List of security issues found
        """
        issues = []
        
        # Check for hidden instructions
        hidden_matches = self.hidden_instruction_regex.findall(description)
        if hidden_matches:
            issues.append(SecurityIssue(
                issue_type="hidden_instructions",
                severity=SecurityRiskLevel.HIGH,
                description=f"Hidden instructions detected in tool description",
                location=f"tool:{tool_name}",
                details={
                    "matches": hidden_matches,
                    "description_preview": description[:200] + "..." if len(description) > 200 else description
                }
            ))
        
        # Check for sensitive file access
        sensitive_matches = self.sensitive_exact_regex.findall(description)
        if sensitive_matches:
            issues.append(SecurityIssue(
                issue_type="sensitive_file_access",
                severity=SecurityRiskLevel.HIGH,
                description=f"Potential sensitive file access detected",
                location=f"tool:{tool_name}",
                details={
                    "matches": sensitive_matches,
                    "description_preview": description[:200] + "..." if len(description) > 200 else description
                }
            ))
        
        # Check for tool shadowing
        shadowing_matches = self.tool_shadowing_regex.findall(description)
        if shadowing_matches:
            issues.append(SecurityIssue(
                issue_type="tool_shadowing",
                severity=SecurityRiskLevel.CRITICAL,
                description=f"Tool shadowing behavior detected",
                location=f"tool:{tool_name}",
                details={
                    "matches": shadowing_matches,
                    "description_preview": description[:200] + "..." if len(description) > 200 else description
                }
            ))
        
        # Check for excessive length (potential hidden content)
        if len(description) > 2000:
            issues.append(SecurityIssue(
                issue_type="excessive_description_length",
                severity=SecurityRiskLevel.MEDIUM,
                description=f"Tool description is excessively long",
                location=f"tool:{tool_name}",
                details={
                    "length": len(description),
                    "recommended_max": 2000
                }
            ))
        
        self._log_issues(issues)
        return issues
    
    def validate_tool_schema(self, tool_name: str, schema: Dict[str, Any]) -> List[SecurityIssue]:
        """
        Validate tool schema for security issues.
        
        Args:
            tool_name: Name of the tool being validated
            schema: Tool parameter schema to validate
            
        Returns:
            List of security issues found
        """
        issues = []
        
        if not isinstance(schema, dict):
            return issues
        
        # Check for suspicious parameters
        properties = schema.get('properties', {})
        for param_name, param_schema in properties.items():
            if param_name.lower() in self.suspicious_parameters:
                issues.append(SecurityIssue(
                    issue_type="suspicious_parameter",
                    severity=SecurityRiskLevel.MEDIUM,
                    description=f"Suspicious parameter name detected",
                    location=f"tool:{tool_name}:parameter:{param_name}",
                    details={
                        "parameter_name": param_name,
                        "parameter_schema": param_schema,
                        "suspicious_reason": "Parameter name matches suspicious patterns"
                    }
                ))
            
            # Check for overly permissive parameter types
            param_type = param_schema.get('type', '')
            if param_type == 'object' and param_schema.get('additionalProperties', False):
                issues.append(SecurityIssue(
                    issue_type="permissive_parameter",
                    severity=SecurityRiskLevel.MEDIUM,
                    description=f"Overly permissive parameter type",
                    location=f"tool:{tool_name}:parameter:{param_name}",
                    details={
                        "parameter_name": param_name,
                        "parameter_type": param_type,
                        "additional_properties": True
                    }
                ))
        
        # Check for missing required field validation
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in properties:
                issues.append(SecurityIssue(
                    issue_type="missing_required_field",
                    severity=SecurityRiskLevel.LOW,
                    description=f"Required field not defined in properties",
                    location=f"tool:{tool_name}:parameter:{field}",
                    details={
                        "field_name": field,
                        "required_fields": required_fields
                    }
                ))
        
        self._log_issues(issues)
        return issues
    
    def validate_tool_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> List[SecurityIssue]:
        """
        Validate tool arguments for security issues.
        
        Args:
            tool_name: Name of the tool being validated
            arguments: Tool arguments to validate
            
        Returns:
            List of security issues found
        """
        issues = []
        
        if not isinstance(arguments, dict):
            return issues
        
        # Check for sensitive data in arguments
        for arg_name, arg_value in arguments.items():
            if isinstance(arg_value, str):
                # Check for sensitive patterns in string values
                sensitive_matches = self.sensitive_regex.findall(arg_value)
                if sensitive_matches:
                    issues.append(SecurityIssue(
                        issue_type="sensitive_data_in_arguments",
                        severity=SecurityRiskLevel.HIGH,
                        description=f"Sensitive data detected in tool arguments",
                        location=f"tool:{tool_name}:argument:{arg_name}",
                        details={
                            "argument_name": arg_name,
                            "matches": sensitive_matches,
                            "value_preview": arg_value[:100] + "..." if len(arg_value) > 100 else arg_value
                        }
                    ))
                
                # Check for potential path traversal
                if '..' in arg_value or arg_value.startswith('/'):
                    issues.append(SecurityIssue(
                        issue_type="potential_path_traversal",
                        severity=SecurityRiskLevel.HIGH,
                        description=f"Potential path traversal detected",
                        location=f"tool:{tool_name}:argument:{arg_name}",
                        details={
                            "argument_name": arg_name,
                            "value": arg_value
                        }
                    ))
            
            # Check for suspicious parameter names
            if arg_name.lower() in self.suspicious_parameters:
                issues.append(SecurityIssue(
                    issue_type="suspicious_argument_name",
                    severity=SecurityRiskLevel.MEDIUM,
                    description=f"Suspicious argument name detected",
                    location=f"tool:{tool_name}:argument:{arg_name}",
                    details={
                        "argument_name": arg_name,
                        "argument_value": str(arg_value)[:100]
                    }
                ))
        
        self._log_issues(issues)
        return issues
    
    def validate_server_configuration(self, config: Dict[str, Any]) -> List[SecurityIssue]:
        """
        Validate MCP server configuration for security issues.
        
        Args:
            config: Server configuration to validate
            
        Returns:
            List of security issues found
        """
        issues = []
        
        # Check for hardcoded credentials
        if 'env' in config:
            env_vars = config['env']
            sensitive_env_vars = ['password', 'secret', 'key', 'token', 'api_key']
            
            for env_var_name, env_var_value in env_vars.items():
                env_var_lower = env_var_name.lower()
                for sensitive_pattern in sensitive_env_vars:
                    if sensitive_pattern in env_var_lower:
                        issues.append(SecurityIssue(
                            issue_type="hardcoded_credentials",
                            severity=SecurityRiskLevel.HIGH,
                            description=f"Hardcoded credentials detected in configuration",
                            location=f"config:env:{env_var_name}",
                            details={
                                "environment_variable": env_var_name,
                                "sensitive_pattern": sensitive_pattern,
                                "recommendation": "Use environment variables or secure secret management"
                            }
                        ))
                        break  # Only report once per environment variable
        
        # Check for insecure command execution
        if 'command' in config:
            command = config['command']
            if command in ['bash', 'sh', 'cmd', 'powershell']:
                issues.append(SecurityIssue(
                    issue_type="insecure_command_execution",
                    severity=SecurityRiskLevel.HIGH,
                    description=f"Insecure command execution detected",
                    location="config:command",
                    details={
                        "command": command,
                        "recommendation": "Use specific executable paths instead of shell commands"
                    }
                ))
        
        self._log_issues(issues)
        return issues
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get a summary of all security issues found."""
        summary = {
            "total_issues": len(self.issues),
            "issues_by_severity": {},
            "issues_by_type": {},
            "recommendations": []
        }
        
        # Count by severity
        for issue in self.issues:
            severity = issue.severity.value
            summary["issues_by_severity"][severity] = summary["issues_by_severity"].get(severity, 0) + 1
        
        # Count by type
        for issue in self.issues:
            issue_type = issue.issue_type
            summary["issues_by_type"][issue_type] = summary["issues_by_type"].get(issue_type, 0) + 1
        
        # Generate recommendations
        if summary["issues_by_severity"].get("critical", 0) > 0:
            summary["recommendations"].append("Immediately address critical security issues")
        
        if summary["issues_by_severity"].get("high", 0) > 0:
            summary["recommendations"].append("Review and fix high-risk vulnerabilities")
        
        if summary["issues_by_severity"].get("medium", 0) > 0:
            summary["recommendations"].append("Consider addressing medium-risk issues")
        
        if summary["total_issues"] == 0:
            summary["recommendations"].append("Continue regular security monitoring")
        
        return summary
    
    def clear_issues(self) -> None:
        """Clear all recorded security issues."""
        self.issues.clear()
    
    def _log_issues(self, issues: List[SecurityIssue]) -> None:
        """Log security issues and add to tracking list."""
        for issue in issues:
            self.issues.append(issue)
            
            # Only log if logging is enabled
            if self.enable_logging:
                log_level = {
                    SecurityRiskLevel.LOW: logging.INFO,
                    SecurityRiskLevel.MEDIUM: logging.WARNING,
                    SecurityRiskLevel.HIGH: logging.ERROR,
                    SecurityRiskLevel.CRITICAL: logging.CRITICAL
                }.get(issue.severity, logging.WARNING)
                
                logger.log(log_level, 
                          f"Security issue detected: {issue.issue_type} - {issue.description} at {issue.location}")


class SecurityMonitor:
    """Real-time security monitoring for MCP server."""
    
    def __init__(self, validator: SecurityValidator):
        """
        Initialize security monitor.
        
        Args:
            validator: Security validator instance
        """
        self.validator = validator
        self.monitoring_enabled = True
        self.alert_threshold = SecurityRiskLevel.MEDIUM
    
    def monitor_tool_registration(self, tool_name: str, description: str, schema: Dict[str, Any]) -> List[SecurityIssue]:
        """Monitor tool registration for security issues."""
        if not self.monitoring_enabled:
            return []
        
        issues = []
        issues.extend(self.validator.validate_tool_description(tool_name, description))
        issues.extend(self.validator.validate_tool_schema(tool_name, schema))
        
        # Check if any issues meet alert threshold
        high_priority_issues = [i for i in issues if i.severity.value >= self.alert_threshold.value]
        if high_priority_issues:
            logger.warning(f"High-priority security issues detected during tool registration: {tool_name}")
        
        return issues
    
    def monitor_tool_execution(self, tool_name: str, arguments: Dict[str, Any]) -> List[SecurityIssue]:
        """Monitor tool execution for security issues."""
        if not self.monitoring_enabled:
            return []
        
        issues = self.validator.validate_tool_arguments(tool_name, arguments)
        
        # Check if any issues meet alert threshold
        high_priority_issues = [i for i in issues if i.severity.value >= self.alert_threshold.value]
        if high_priority_issues:
            logger.warning(f"High-priority security issues detected during tool execution: {tool_name}")
        
        return issues
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security monitoring metrics."""
        summary = self.validator.get_security_summary()
        
        return {
            "monitoring_enabled": self.monitoring_enabled,
            "alert_threshold": self.alert_threshold.value,
            "total_issues": summary["total_issues"],
            "issues_by_severity": summary["issues_by_severity"],
            "issues_by_type": summary["issues_by_type"],
            "recommendations": summary["recommendations"]
        }
    
    def set_alert_threshold(self, threshold: SecurityRiskLevel) -> None:
        """Set the alert threshold for security monitoring."""
        self.alert_threshold = threshold
    
    def enable_monitoring(self) -> None:
        """Enable security monitoring."""
        self.monitoring_enabled = True
    
    def disable_monitoring(self) -> None:
        """Disable security monitoring."""
        self.monitoring_enabled = False 