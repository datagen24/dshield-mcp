#!/usr/bin/env python3
"""
MCP-Shield Security Scanner Integration for DShield MCP

This script provides integration with MCP-Shield for security scanning of MCP servers.
It wraps the MCP-Shield Node.js tool and provides Python-based reporting and analysis.
"""

import subprocess
import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPShieldScanner:
    """Integration wrapper for MCP-Shield security scanning."""
    
    def __init__(self, config_path: Optional[str] = None, safe_list: Optional[List[str]] = None):
        """
        Initialize MCP-Shield scanner.
        
        Args:
            config_path: Path to MCP configuration files
            safe_list: List of trusted server names to exclude from scanning
        """
        self.config_path = config_path or self._find_mcp_config()
        self.safe_list = safe_list or ["dshield-elastic-mcp"]
        self.scan_results = {}
        
    def _find_mcp_config(self) -> Optional[str]:
        """Find MCP configuration files in standard locations."""
        standard_paths = [
            Path.home() / ".config" / ".mcp",
            Path.home() / "Library" / "Application Support" / "Claude",
            Path.home() / ".continue",
            Path.cwd() / ".mcp"
        ]
        
        for path in standard_paths:
            if path.exists():
                logger.info(f"Found MCP config at: {path}")
                return str(path)
        
        logger.warning("No MCP configuration found in standard locations")
        return None
    
    def check_mcp_shield_installed(self) -> bool:
        """Check if MCP-Shield is installed and available."""
        try:
            result = subprocess.run(
                ["npx", "mcp-shield", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def install_mcp_shield(self) -> bool:
        """Install MCP-Shield globally."""
        try:
            logger.info("Installing MCP-Shield...")
            result = subprocess.run(
                ["npm", "install", "-g", "mcp-shield"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("MCP-Shield installed successfully")
                return True
            else:
                logger.error(f"Failed to install MCP-Shield: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("Installation timed out")
            return False
    
    def scan(self, claude_api_key: Optional[str] = None, identify_as: Optional[str] = None) -> Dict[str, Any]:
        """
        Run MCP-Shield security scan.
        
        Args:
            claude_api_key: Optional Claude API key for enhanced analysis
            identify_as: Optional client name for testing
            
        Returns:
            Dictionary containing scan results and analysis
        """
        if not self.check_mcp_shield_installed():
            logger.info("MCP-Shield not found, attempting to install...")
            if not self.install_mcp_shield():
                return {
                    "error": "Failed to install MCP-Shield",
                    "exit_code": 1,
                    "vulnerabilities": []
                }
        
        cmd = ["npx", "mcp-shield"]
        
        if self.config_path:
            cmd.extend(["--path", self.config_path])
            
        if claude_api_key:
            cmd.extend(["--claude-api-key", claude_api_key])
            
        if identify_as:
            cmd.extend(["--identify-as", identify_as])
            
        # Add safe list for trusted servers
        safe_list_str = ",".join(self.safe_list)
        cmd.extend(["--safe-list", safe_list_str])
        
        logger.info(f"Running MCP-Shield scan: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            self.scan_results = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": datetime.now().isoformat(),
                "vulnerabilities": self._parse_vulnerabilities(result.stdout),
                "summary": self._generate_summary(result.stdout)
            }
            
            return self.scan_results
            
        except subprocess.TimeoutExpired:
            logger.error("Scan timed out")
            return {
                "error": "Scan timed out",
                "exit_code": 1,
                "vulnerabilities": []
            }
    
    def _parse_vulnerabilities(self, output: str) -> List[Dict[str, Any]]:
        """Parse MCP-Shield output for vulnerabilities."""
        vulnerabilities = []
        
        # Parse vulnerability sections
        vulnerability_pattern = r'(\d+)\.\s+Server:\s+([^\n]+)\s+Tool:\s+([^\n]+)\s+Risk Level:\s+([^\n]+)'
        matches = re.finditer(vulnerability_pattern, output, re.MULTILINE)
        
        for match in matches:
            vulnerability = {
                "id": match.group(1),
                "server": match.group(2).strip(),
                "tool": match.group(3).strip(),
                "risk_level": match.group(4).strip(),
                "issues": self._extract_issues(output, match.start()),
                "ai_analysis": self._extract_ai_analysis(output, match.start())
            }
            vulnerabilities.append(vulnerability)
        
        return vulnerabilities
    
    def _extract_issues(self, output: str, start_pos: int) -> List[str]:
        """Extract issues from vulnerability section."""
        issues = []
        
        # Look for issues section after the vulnerability header
        section_start = output.find("Issues:", start_pos)
        if section_start == -1:
            return issues
        
        # Find the end of the issues section
        section_end = output.find("\n\n", section_start)
        if section_end == -1:
            section_end = len(output)
        
        issues_section = output[section_start:section_end]
        
        # Extract individual issues
        issue_pattern = r'–\s+([^\n]+)'
        for match in re.finditer(issue_pattern, issues_section):
            issues.append(match.group(1).strip())
        
        return issues
    
    def _extract_ai_analysis(self, output: str, start_pos: int) -> Optional[str]:
        """Extract AI analysis from vulnerability section."""
        section_start = output.find("AI Analysis:", start_pos)
        if section_start == -1:
            return None
        
        # Find the end of the AI analysis section
        section_end = output.find("\n\n", section_start)
        if section_end == -1:
            section_end = len(output)
        
        return output[section_start:section_end].strip()
    
    def _generate_summary(self, output: str) -> Dict[str, Any]:
        """Generate summary statistics from scan output."""
        summary = {
            "total_servers": 0,
            "total_tools": 0,
            "vulnerable_servers": 0,
            "vulnerable_tools": 0,
            "high_risk_vulnerabilities": 0,
            "medium_risk_vulnerabilities": 0,
            "low_risk_vulnerabilities": 0
        }
        
        # Count servers and tools
        server_pattern = r'●\s+([^\s]+)\s+\((\d+)\s+tools?\)'
        for match in re.finditer(server_pattern, output):
            summary["total_servers"] += 1
            summary["total_tools"] += int(match.group(2))
        
        # Count vulnerabilities by risk level
        for vuln in self.scan_results.get("vulnerabilities", []):
            risk_level = vuln.get("risk_level", "").upper()
            if "HIGH" in risk_level:
                summary["high_risk_vulnerabilities"] += 1
            elif "MEDIUM" in risk_level:
                summary["medium_risk_vulnerabilities"] += 1
            elif "LOW" in risk_level:
                summary["low_risk_vulnerabilities"] += 1
        
        summary["vulnerable_servers"] = len(set(v["server"] for v in self.scan_results.get("vulnerabilities", [])))
        summary["vulnerable_tools"] = len(self.scan_results.get("vulnerabilities", []))
        
        return summary
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate a formatted security report."""
        if not self.scan_results:
            return "No scan results available. Run scan() first."
        
        report = []
        report.append("# MCP Security Scan Report")
        report.append(f"Generated: {self.scan_results.get('timestamp', 'Unknown')}")
        report.append("")
        
        # Summary
        summary = self.scan_results.get("summary", {})
        report.append("## Summary")
        report.append(f"- Total Servers: {summary.get('total_servers', 0)}")
        report.append(f"- Total Tools: {summary.get('total_tools', 0)}")
        report.append(f"- Vulnerable Servers: {summary.get('vulnerable_servers', 0)}")
        report.append(f"- Vulnerable Tools: {summary.get('vulnerable_tools', 0)}")
        report.append(f"- High Risk Vulnerabilities: {summary.get('high_risk_vulnerabilities', 0)}")
        report.append(f"- Medium Risk Vulnerabilities: {summary.get('medium_risk_vulnerabilities', 0)}")
        report.append(f"- Low Risk Vulnerabilities: {summary.get('low_risk_vulnerabilities', 0)}")
        report.append("")
        
        # Vulnerabilities
        vulnerabilities = self.scan_results.get("vulnerabilities", [])
        if vulnerabilities:
            report.append("## Vulnerabilities")
            report.append("")
            
            for vuln in vulnerabilities:
                report.append(f"### {vuln['id']}. {vuln['server']} - {vuln['tool']}")
                report.append(f"**Risk Level:** {vuln['risk_level']}")
                report.append("")
                
                if vuln.get('issues'):
                    report.append("**Issues:**")
                    for issue in vuln['issues']:
                        report.append(f"- {issue}")
                    report.append("")
                
                if vuln.get('ai_analysis'):
                    report.append("**AI Analysis:**")
                    report.append(vuln['ai_analysis'])
                    report.append("")
        else:
            report.append("## Vulnerabilities")
            report.append("No vulnerabilities detected.")
            report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        if vulnerabilities:
            report.append("1. Review all identified vulnerabilities")
            report.append("2. Remove or fix high-risk issues immediately")
            report.append("3. Audit tool descriptions for hidden instructions")
            report.append("4. Review parameter schemas for suspicious fields")
            report.append("5. Implement security validation in tool registration")
        else:
            report.append("1. Continue regular security scanning")
            report.append("2. Monitor for new vulnerabilities")
            report.append("3. Keep MCP-Shield updated")
            report.append("4. Consider implementing additional security measures")
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            logger.info(f"Report saved to: {output_file}")
        
        return report_text
    
    def save_results(self, output_file: str) -> None:
        """Save scan results to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.scan_results, f, indent=2)
        logger.info(f"Results saved to: {output_file}")


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="MCP-Shield Security Scanner Integration")
    parser.add_argument("--config-path", help="Path to MCP configuration files")
    parser.add_argument("--claude-api-key", help="Claude API key for enhanced analysis")
    parser.add_argument("--identify-as", help="Identify as specific client for testing")
    parser.add_argument("--safe-list", help="Comma-separated list of trusted servers")
    parser.add_argument("--output", help="Output file for scan results (JSON)")
    parser.add_argument("--report", help="Output file for formatted report (Markdown)")
    parser.add_argument("--install", action="store_true", help="Install MCP-Shield if not found")
    
    args = parser.parse_args()
    
    # Initialize scanner
    safe_list = args.safe_list.split(",") if args.safe_list else None
    scanner = MCPShieldScanner(
        config_path=args.config_path,
        safe_list=safe_list
    )
    
    # Check if MCP-Shield is installed
    if not scanner.check_mcp_shield_installed():
        if args.install:
            if not scanner.install_mcp_shield():
                logger.error("Failed to install MCP-Shield")
                sys.exit(1)
        else:
            logger.error("MCP-Shield not found. Use --install to install it.")
            sys.exit(1)
    
    # Run scan
    results = scanner.scan(
        claude_api_key=args.claude_api_key,
        identify_as=args.identify_as
    )
    
    if "error" in results:
        logger.error(f"Scan failed: {results['error']}")
        sys.exit(1)
    
    # Save results
    if args.output:
        scanner.save_results(args.output)
    
    # Generate report
    report = scanner.generate_report(args.report)
    print(report)
    
    # Exit with appropriate code
    if results.get("vulnerabilities"):
        logger.warning("Vulnerabilities detected!")
        sys.exit(1)
    else:
        logger.info("No vulnerabilities detected.")
        sys.exit(0)


if __name__ == "__main__":
    main() 