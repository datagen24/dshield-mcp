"""Context injector for preparing data for ChatGPT context injection.

This module provides utilities for preparing and formatting security data
for injection into ChatGPT conversations. It handles various data types
including security events, threat intelligence, attack reports, and query
results, formatting them appropriately for AI consumption.

Features:
- Security context preparation and formatting
- Attack report context injection
- Query result formatting
- MCP-compatible context injection
- Multiple output formats (structured, summary, raw)
- ChatGPT-optimized formatting

Example:
    >>> from src.context_injector import ContextInjector
    >>> injector = ContextInjector()
    >>> context = injector.prepare_security_context(events, threat_intel)
    >>> formatted = injector.inject_context_for_chatgpt(context)

"""

import json
import os
from datetime import UTC, datetime
from typing import Any

import structlog
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = structlog.get_logger(__name__)


class ContextInjector:
    """Prepare and inject security context for ChatGPT analysis.

    This class provides methods to prepare and format various types of
    security data for injection into ChatGPT conversations. It supports
    multiple output formats and optimizes data for AI consumption.

    Attributes:
        max_context_size: Maximum context size in characters
        include_raw_data: Whether to include raw data in context
        context_format: Output format (structured, summary, or raw)

    Example:
        >>> injector = ContextInjector()
        >>> context = injector.prepare_security_context(events)
        >>> formatted = injector.inject_context_for_chatgpt(context)

    """

    def __init__(self) -> None:
        """Initialize the ContextInjector.

        Loads configuration from environment variables for context
        formatting preferences and size limits.
        """
        self.max_context_size = int(os.getenv("MAX_CONTEXT_SIZE", "10000"))  # characters
        self.include_raw_data = os.getenv("INCLUDE_RAW_DATA", "false").lower() == "true"
        self.context_format = os.getenv(
            "CONTEXT_FORMAT", "structured"
        )  # structured, summary, or raw

    def prepare_security_context(
        self,
        events: list[dict[str, Any]],
        threat_intelligence: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Prepare security context for injection.

        Creates a comprehensive security context from events, threat
        intelligence, and summary data, formatted according to the
        configured context format preference.

        Args:
            events: List of security event dictionaries
            threat_intelligence: Optional threat intelligence data
            summary: Optional summary data

        Returns:
            Dictionary containing formatted security context

        """
        context: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "context_type": "security_analysis",
            "data": {},
        }

        # Add events based on format preference
        if self.context_format == "structured":
            context["data"]["events"] = self._structure_events(events)
        elif self.context_format == "summary":
            context["data"]["events"] = self._summarize_events(events)
        else:  # raw
            context["data"]["events"] = (
                events if self.include_raw_data else self._clean_events(events)
            )

        # Add threat intelligence
        if threat_intelligence:
            context["data"]["threat_intelligence"] = self._process_threat_intelligence(
                threat_intelligence
            )

        # Add summary if provided
        if summary:
            context["data"]["summary"] = summary

        # Add metadata
        context["data"]["metadata"] = self._generate_metadata(events, threat_intelligence)

        # Add analysis hints
        context["data"]["analysis_hints"] = self._generate_analysis_hints(
            events, threat_intelligence
        )

        return context

    def prepare_attack_report_context(self, report: dict[str, Any]) -> dict[str, Any]:
        """Prepare attack report context for injection.

        Formats an attack report for injection into ChatGPT conversations,
        including metadata and confidence information.

        Args:
            report: Attack report dictionary

        Returns:
            Dictionary containing formatted attack report context

        """
        context = {
            "timestamp": datetime.now(UTC).isoformat(),
            "context_type": "attack_report",
            "data": {
                "report": self._format_attack_report(report),
                "metadata": {
                    "report_id": report.get("report_id"),
                    "confidence_level": report.get("confidence_level"),
                    "tags": report.get("tags", []),
                },
            },
        }

        return context

    def prepare_query_context(
        self,
        query_type: str,
        parameters: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Prepare query context for injection.

        Formats query results and parameters for injection into ChatGPT
        conversations, including metadata about the query execution.

        Args:
            query_type: Type of query that was executed
            parameters: Query parameters that were used
            results: Query results to format

        Returns:
            Dictionary containing formatted query context

        """
        context = {
            "timestamp": datetime.now(UTC).isoformat(),
            "context_type": "query_results",
            "data": {
                "query_type": query_type,
                "parameters": parameters,
                "results": self._format_query_results(results),
                "result_count": len(results),
                "metadata": {
                    "query_timestamp": datetime.now(UTC).isoformat(),
                    "result_format": self.context_format,
                },
            },
        }

        return context

    def inject_context_for_chatgpt(self, context: dict[str, Any]) -> str:
        """Format context for ChatGPT consumption.

        Converts a context dictionary into a string format optimized
        for ChatGPT consumption, handling different context types
        appropriately.

        Args:
            context: Context dictionary to format

        Returns:
            String formatted for ChatGPT consumption

        """
        # Convert context to a readable format for ChatGPT
        if context["context_type"] == "security_analysis":
            return self._format_security_context_for_chatgpt(context["data"])
        if context["context_type"] == "attack_report":
            return self._format_attack_report_for_chatgpt(context["data"])
        if context["context_type"] == "query_results":
            return self._format_query_results_for_chatgpt(context["data"])
        return json.dumps(context, indent=2)

    def create_mcp_context_injection(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create MCP-compatible context injection.

        Formats context data for use with the Model Context Protocol (MCP),
        including proper metadata and version information.

        Args:
            context: Context dictionary to format

        Returns:
            Dictionary formatted for MCP protocol

        """
        # Format for MCP protocol
        mcp_context = {
            "type": "context_injection",
            "timestamp": context["timestamp"],
            "context_type": context["context_type"],
            "content": self.inject_context_for_chatgpt(context),
            "metadata": {
                "source": "dshield-elastic-mcp",
                "version": "1.0.0",
                "format": "structured_text",
            },
        }

        return mcp_context

    def _structure_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Structure events for better analysis.

        Converts raw event data into a structured format optimized
        for analysis, organizing network information and metadata.

        Args:
            events: List of raw event dictionaries

        Returns:
            List of structured event dictionaries

        """
        structured_events = []

        for event in events:
            structured_event = {
                "id": event.get("id"),
                "timestamp": event.get("timestamp"),
                "severity": event.get("severity"),
                "category": event.get("category"),
                "event_type": event.get("event_type"),
                "description": event.get("description"),
                "network_info": {
                    "source_ip": event.get("source_ip"),
                    "destination_ip": event.get("destination_ip"),
                    "source_port": event.get("source_port"),
                    "destination_port": event.get("destination_port"),
                    "protocol": event.get("protocol"),
                },
            }

            # Add raw data if enabled
            if self.include_raw_data and "raw_data" in event:
                structured_event["raw_data"] = event["raw_data"]

            structured_events.append(structured_event)

        return structured_events

    def _summarize_events(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Create a summary of events instead of full details.

        Generates a summary of events including counts by severity,
        category, and unique IP addresses for efficient context injection.

        Args:
            events: List of event dictionaries to summarize

        Returns:
            Dictionary containing event summary

        """
        if not events:
            return {"message": "No events found"}

        # Count by severity
        severity_counts: dict[str, int] = {}
        for event in events:
            severity = event.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Count by category
        category_counts: dict[str, int] = {}
        for event in events:
            category = event.get("category", "unknown")
            category_counts[category] = category_counts.get(category, 0) + 1

        # Extract unique IPs
        source_ips = set()
        destination_ips = set()
        for event in events:
            if event.get("source_ip"):
                source_ip = event["source_ip"]
                if isinstance(source_ip, list | dict):
                    source_ips.add(str(source_ip))
                else:
                    source_ips.add(str(source_ip))
            if event.get("destination_ip"):
                destination_ip = event["destination_ip"]
                if isinstance(destination_ip, list | dict):
                    destination_ips.add(str(destination_ip))
                else:
                    destination_ips.add(str(destination_ip))

        # Get sample events (first 5)
        sample_events = events[:5]

        return {
            "total_events": len(events),
            "severity_distribution": severity_counts,
            "category_distribution": category_counts,
            "unique_source_ips": len(source_ips),
            "unique_destination_ips": len(destination_ips),
            "sample_events": self._structure_events(sample_events),
        }

    def _clean_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean events by removing sensitive or unnecessary data.

        Removes sensitive fields and unnecessary metadata from events
        while preserving essential information for analysis.

        Args:
            events: List of event dictionaries to clean

        Returns:
            List of cleaned event dictionaries

        """
        cleaned_events = []

        for event in events:
            cleaned_event = {
                "id": event.get("id"),
                "timestamp": event.get("timestamp"),
                "severity": event.get("severity"),
                "category": event.get("category"),
                "event_type": event.get("event_type"),
                "description": event.get("description"),
                "source_ip": event.get("source_ip"),
                "destination_ip": event.get("destination_ip"),
                "source_port": event.get("source_port"),
                "destination_port": event.get("destination_port"),
                "protocol": event.get("protocol"),
            }

            # Remove None values
            cleaned_event = {k: v for k, v in cleaned_event.items() if v is not None}
            cleaned_events.append(cleaned_event)

        return cleaned_events

    def _process_threat_intelligence(self, threat_intelligence: dict[str, Any]) -> dict[str, Any]:
        """Process threat intelligence data for context injection.

        Formats threat intelligence data for inclusion in context,
        organizing it by IP address and threat level.

        Args:
            threat_intelligence: Raw threat intelligence data

        Returns:
            Processed threat intelligence dictionary

        """
        processed_ti: dict[str, Any] = {
            "total_ips": len(threat_intelligence),
            "high_risk_ips": [],
            "medium_risk_ips": [],
            "low_risk_ips": [],
            "unknown_risk_ips": [],
        }

        for ip, ti_data in threat_intelligence.items():
            if isinstance(ti_data, dict):
                threat_level = ti_data.get("threat_level", "unknown")
                ip_info = {
                    "ip": ip,
                    "reputation_score": ti_data.get("reputation_score"),
                    "country": ti_data.get("country"),
                    "asn": ti_data.get("asn"),
                    "organization": ti_data.get("organization"),
                    "attack_types": ti_data.get("attack_types", []),
                }

                if threat_level == "high":
                    processed_ti["high_risk_ips"].append(ip_info)
                elif threat_level == "medium":
                    processed_ti["medium_risk_ips"].append(ip_info)
                elif threat_level == "low":
                    processed_ti["low_risk_ips"].append(ip_info)
                else:
                    processed_ti["unknown_risk_ips"].append(ip_info)

        return processed_ti

    def _generate_metadata(
        self, events: list[dict[str, Any]], threat_intelligence: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Generate metadata for the context.

        Creates metadata including time ranges, data sources, and
        processing information for the context.

        Args:
            events: List of events to analyze
            threat_intelligence: Optional threat intelligence data

        Returns:
            Dictionary containing context metadata

        """
        metadata = {
            "event_count": len(events),
            "time_range": self._extract_time_range(events),
            "data_sources": self._extract_data_sources(events),
            "threat_intelligence_available": threat_intelligence is not None
            and len(threat_intelligence) > 0,
        }

        if threat_intelligence:
            metadata["threat_intelligence_ips"] = len(threat_intelligence)

        return metadata

    def _generate_analysis_hints(
        self, events: list[dict[str, Any]], threat_intelligence: dict[str, Any] | None
    ) -> list[str]:
        """Generate analysis hints for ChatGPT.

        Creates a list of analysis hints and suggestions based on
        the events and threat intelligence data.

        Args:
            events: List of events to analyze
            threat_intelligence: Optional threat intelligence data

        Returns:
            List of analysis hints and suggestions

        """
        hints = []

        # Analyze event patterns
        high_severity_count = sum(
            1 for event in events if event.get("severity") in ["high", "critical"]
        )
        if high_severity_count > 0:
            hints.append(
                f"Found {high_severity_count} high/critical severity events "
                f"requiring immediate attention"
            )

        # Check for threat intelligence hits
        if threat_intelligence:
            high_risk_ti = sum(
                1
                for ti in threat_intelligence.values()
                if isinstance(ti, dict) and ti.get("threat_level") == "high"
            )
            if high_risk_ti > 0:
                hints.append(
                    f"Identified {high_risk_ti} IP addresses with high threat intelligence scores"
                )

        # Check for attack patterns
        attack_patterns = self._detect_attack_patterns(events)
        for pattern, count in attack_patterns.items():
            if count > 0:
                hints.append(f"Detected {count} events matching {pattern} pattern")

        # Add general analysis guidance
        hints.append(
            "Consider correlating events with threat intelligence for comprehensive analysis"
        )
        hints.append("Look for patterns in source IPs, ports, and protocols")
        hints.append("Assess the potential impact and recommend mitigation strategies")

        return hints

    def _format_attack_report(self, report: dict[str, Any]) -> dict[str, Any]:
        """Format attack report for context injection.

        Formats an attack report for inclusion in context, organizing
        it into sections for executive summary, details, and recommendations.

        Args:
            report: Raw attack report dictionary

        Returns:
            Formatted attack report dictionary

        """
        formatted_report = {
            "title": report.get("title"),
            "summary": report.get("summary"),
            "key_findings": {
                "total_events": report.get("total_events"),
                "unique_ips": report.get("unique_ips"),
                "high_risk_ips": report.get("high_risk_ips", []),
                "attack_vectors": report.get("attack_vectors", []),
                "impact_assessment": report.get("impact_assessment"),
            },
            "recommendations": report.get("recommendations", []),
            "mitigation_actions": report.get("mitigation_actions", []),
        }

        return formatted_report

    def _format_query_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format query results for context injection.

        Formats query results for inclusion in context, ensuring
        they are properly structured and readable.

        Args:
            results: Raw query results list

        Returns:
            Formatted query results list

        """
        if self.context_format == "structured":
            return self._structure_events(results)
        if self.context_format == "summary":
            return [self._summarize_events(results)]
        return self._clean_events(results)

    def _format_security_context_for_chatgpt(self, data: dict[str, Any]) -> str:
        """Format security context specifically for ChatGPT.

        Converts security context data into a text format optimized
        for ChatGPT consumption, including structured sections and
        analysis guidance.

        Args:
            data: Security context data dictionary

        Returns:
            String formatted for ChatGPT consumption

        """
        output = []

        # Add summary if available
        if "summary" in data:
            summary = data["summary"]
            output.append("=== SECURITY SUMMARY ===")
            output.append(f"Total Events: {summary.get('total_events', 0)}")
            output.append(f"Time Range: {summary.get('time_range_hours', 24)} hours")
            output.append(f"High Risk Events: {summary.get('high_risk_events', 0)}")
            output.append("")

        # Add events
        if "events" in data:
            events = data["events"]
            if isinstance(events, dict) and "total_events" in events:
                # Summary format
                output.append("=== EVENT SUMMARY ===")
                output.append(f"Total Events: {events['total_events']}")
                output.append(
                    f"Severity Distribution: "
                    f"{json.dumps(events.get('severity_distribution', {}), indent=2)}"
                )
                output.append(
                    f"Category Distribution: "
                    f"{json.dumps(events.get('category_distribution', {}), indent=2)}"
                )
                output.append("")

                if "sample_events" in events:
                    output.append("=== SAMPLE EVENTS ===")
                    for event in events["sample_events"]:
                        output.append(
                            f"- {event.get('event_type', 'Unknown')}: "
                            f"{event.get('description', 'No description')}"
                        )
                    output.append("")
            else:
                # Full events format
                output.append("=== SECURITY EVENTS ===")
                for event in events:
                    output.append(f"Event: {event.get('event_type', 'Unknown')}")
                    output.append(f"  Severity: {event.get('severity', 'Unknown')}")
                    output.append(f"  Description: {event.get('description', 'No description')}")
                    if event.get("source_ip"):
                        output.append(f"  Source IP: {event['source_ip']}")
                    if event.get("destination_ip"):
                        output.append(f"  Destination IP: {event['destination_ip']}")
                    output.append("")

        # Add threat intelligence
        if "threat_intelligence" in data:
            ti = data["threat_intelligence"]
            output.append("=== THREAT INTELLIGENCE ===")
            output.append(f"Total IPs: {ti.get('total_ips', 0)}")
            output.append(f"High Risk IPs: {len(ti.get('high_risk_ips', []))}")
            output.append(f"Medium Risk IPs: {len(ti.get('medium_risk_ips', []))}")

            if ti.get("high_risk_ips"):
                output.append("High Risk IPs:")
                for ip_info in ti["high_risk_ips"]:
                    output.append(
                        f"  - {ip_info['ip']} (Score: {ip_info.get('reputation_score', 'Unknown')})"
                    )
            output.append("")

        # Add analysis hints
        if "analysis_hints" in data:
            output.append("=== ANALYSIS HINTS ===")
            for hint in data["analysis_hints"]:
                output.append(f"- {hint}")
            output.append("")

        return "\n".join(output)

    def _format_attack_report_for_chatgpt(self, data: dict[str, Any]) -> str:
        """Format attack report specifically for ChatGPT.

        Converts attack report data into a text format optimized
        for ChatGPT consumption, including executive summary and
        detailed analysis sections.

        Args:
            data: Attack report data dictionary

        Returns:
            String formatted for ChatGPT consumption

        """
        report = data["report"]

        output = []
        output.append("=== ATTACK REPORT ===")
        output.append(f"Title: {report.get('title', 'Unknown')}")
        output.append("")
        output.append("Executive Summary:")
        output.append(report.get("summary", "No summary available"))
        output.append("")

        # Key findings
        findings = report.get("key_findings", {})
        output.append("Key Findings:")
        output.append(f"- Total Events: {findings.get('total_events', 0)}")
        output.append(f"- Unique IPs: {findings.get('unique_ips', 0)}")
        output.append(f"- High Risk IPs: {len(findings.get('high_risk_ips', []))}")
        output.append(f"- Attack Vectors: {', '.join(findings.get('attack_vectors', []))}")
        output.append(f"- Impact: {findings.get('impact_assessment', 'Unknown')}")
        output.append("")

        # Recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            output.append("Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                output.append(f"{i}. {rec}")
            output.append("")

        # Mitigation actions
        actions = report.get("mitigation_actions", [])
        if actions:
            output.append("Immediate Actions:")
            for i, action in enumerate(actions, 1):
                output.append(f"{i}. {action}")
            output.append("")

        return "\n".join(output)

    def _format_query_results_for_chatgpt(self, data: dict[str, Any]) -> str:
        """Format query results specifically for ChatGPT.

        Converts query results data into a text format optimized
        for ChatGPT consumption, including query parameters and
        result summaries.

        Args:
            data: Query results data dictionary

        Returns:
            String formatted for ChatGPT consumption

        """
        output = []
        output.append(f"=== QUERY RESULTS ({data.get('query_type', 'Unknown')}) ===")
        output.append(f"Result Count: {data.get('result_count', 0)}")
        output.append("")

        results = data.get("results", [])
        if isinstance(results, dict) and "total_events" in results:
            # Summary format
            output.append("Event Summary:")
            output.append(f"- Total Events: {results['total_events']}")
            output.append(
                f"- Severity Distribution: "
                f"{json.dumps(results.get('severity_distribution', {}), indent=2)}"
            )
            output.append(
                f"- Category Distribution: "
                f"{json.dumps(results.get('category_distribution', {}), indent=2)}"
            )
        else:
            # Full results format
            for i, result in enumerate(results[:10], 1):  # Limit to first 10
                output.append(f"Result {i}:")
                output.append(f"  Type: {result.get('event_type', 'Unknown')}")
                output.append(f"  Severity: {result.get('severity', 'Unknown')}")
                output.append(f"  Description: {result.get('description', 'No description')}")
                output.append("")

        return "\n".join(output)

    def _extract_time_range(self, events: list[dict[str, Any]]) -> dict[str, str]:
        """Extract time range from events.

        Determines the earliest and latest timestamps from a list
        of events to establish the time range.

        Args:
            events: List of event dictionaries

        Returns:
            Dictionary with 'start' and 'end' timestamps

        """
        if not events:
            return {"start": "", "end": ""}

        timestamps = []
        for event in events:
            timestamp = event.get("timestamp")
            if timestamp:
                if isinstance(timestamp, str):
                    timestamps.append(timestamp)
                elif hasattr(timestamp, "isoformat"):
                    timestamps.append(timestamp.isoformat())

        if timestamps:
            return {
                "start": min(timestamps),
                "end": max(timestamps),
            }

        return {"start": "", "end": ""}

    def _extract_data_sources(self, events: list[dict[str, Any]]) -> list[str]:
        """Extract data sources from events.

        Identifies the unique data sources (indices) from which
        the events were retrieved.

        Args:
            events: List of event dictionaries

        Returns:
            List of unique data source names

        """
        sources = set()
        for event in events:
            if "indices" in event:
                indices = event["indices"]
                if isinstance(indices, list):
                    for index in indices:
                        if isinstance(index, list | dict):
                            sources.add(str(index))
                        else:
                            sources.add(str(index))
                else:
                    sources.add(str(indices))

        return list(sources)

    def _detect_attack_patterns(self, events: list[dict[str, Any]]) -> dict[str, int]:
        """Detect attack patterns in events.

        Analyzes events to identify common attack patterns and
        their frequencies.

        Args:
            events: List of event dictionaries

        Returns:
            Dictionary mapping attack patterns to their counts

        """
        patterns = {
            "brute_force": 0,
            "port_scan": 0,
            "sql_injection": 0,
            "xss": 0,
            "ddos": 0,
            "malware": 0,
            "phishing": 0,
            "reconnaissance": 0,
        }

        for event in events:
            # Robustly handle both strings and lists for description and event_type
            description_raw = event.get("description", "")
            if isinstance(description_raw, list):
                description = " ".join(map(str, description_raw)).lower()
            else:
                description = str(description_raw).lower()

            event_type_raw = event.get("event_type", "")
            if isinstance(event_type_raw, list):
                event_type = " ".join(map(str, event_type_raw)).lower()
            else:
                event_type = str(event_type_raw).lower()

            if any(
                keyword in description or keyword in event_type
                for keyword in ["brute", "auth", "login", "failed"]
            ):
                patterns["brute_force"] += 1
            elif any(
                keyword in description or keyword in event_type
                for keyword in ["scan", "port", "nmap"]
            ):
                patterns["port_scan"] += 1
            elif any(
                keyword in description or keyword in event_type for keyword in ["sql", "injection"]
            ):
                patterns["sql_injection"] += 1
            elif any(
                keyword in description or keyword in event_type for keyword in ["xss", "script"]
            ):
                patterns["xss"] += 1
            elif any(
                keyword in description or keyword in event_type for keyword in ["ddos", "flood"]
            ):
                patterns["ddos"] += 1
            elif any(
                keyword in description or keyword in event_type for keyword in ["malware", "virus"]
            ):
                patterns["malware"] += 1
            elif any(
                keyword in description or keyword in event_type for keyword in ["phishing", "email"]
            ):
                patterns["phishing"] += 1
            elif any(
                keyword in description or keyword in event_type
                for keyword in ["recon", "enumeration"]
            ):
                patterns["reconnaissance"] += 1

        return {k: v for k, v in patterns.items() if v > 0}
