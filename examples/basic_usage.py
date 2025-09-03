#!/usr/bin/env python3
"""
Basic usage example for DShield MCP - Elastic SIEM Integration
Demonstrates how to use the MCP utility for DShield-specific security analysis.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from elasticsearch_client import ElasticsearchClient
from dshield_client import DShieldClient
from data_processor import DataProcessor
from context_injector import ContextInjector


async def dshield_security_analysis():
    """Perform DShield-specific security analysis using the MCP utility."""

    print("=== DShield MCP Security Analysis ===\n")

    try:
        # Initialize clients
        print("Initializing DShield clients...")
        es_client = ElasticsearchClient()
        dshield_client = DShieldClient()
        data_processor = DataProcessor()
        context_injector = ContextInjector()

        # Connect to Elasticsearch
        print("Connecting to Elasticsearch...")
        await es_client.connect()

        # Get available DShield indices
        print("Discovering DShield indices...")
        available_indices = await es_client.get_available_indices()
        print(f"Found {len(available_indices)} DShield indices: {available_indices[:5]}...")

        # Query DShield events
        print("Querying DShield events...")
        events = await es_client.query_dshield_events(time_range_hours=24, size=50)
        print(f"Found {len(events)} DShield events\n")

        if not events:
            print("No DShield events found in the last 24 hours.")
            return

        # Query DShield attacks specifically
        print("Querying DShield attack data...")
        attacks = await es_client.query_dshield_attacks(time_range_hours=24, size=20)
        print(f"Found {len(attacks)} DShield attacks")

        # Query DShield top attackers
        print("Querying DShield top attackers...")
        top_attackers = await es_client.query_dshield_top_attackers(hours=24, limit=10)
        print(f"Found {len(top_attackers)} top attackers")

        # Query DShield geographic data
        print("Querying DShield geographic data...")
        geo_data = await es_client.query_dshield_geographic_data(size=20)
        print(f"Found {len(geo_data)} geographic records")

        # Query DShield port data
        print("Querying DShield port data...")
        port_data = await es_client.query_dshield_port_data(size=20)
        print(f"Found {len(port_data)} port records")

        # Get DShield statistics
        print("Getting DShield statistics...")
        stats = await es_client.get_dshield_statistics(time_range_hours=24)
        print(f"Retrieved comprehensive DShield statistics")

        # Process events
        print("Processing DShield events...")
        processed_events = data_processor.process_security_events(events)

        # Generate DShield-specific summary
        print("Generating DShield security summary...")
        summary = data_processor.generate_security_summary(processed_events)

        # Generate DShield statistics
        print("Generating DShield statistics...")
        dshield_stats = data_processor.generate_dshield_summary(processed_events)

        # Extract unique IPs for threat intelligence
        print("Extracting unique IP addresses...")
        unique_ips = data_processor.extract_unique_ips(processed_events)
        print(f"Found {len(unique_ips)} unique IP addresses")

        # Enrich IPs with DShield threat intelligence
        print("Enriching IPs with DShield threat intelligence...")
        threat_intelligence = {}

        # Process first 10 IPs to avoid rate limiting
        for ip in unique_ips[:10]:
            try:
                ti_data = await dshield_client.get_ip_reputation(ip)
                threat_intelligence[ip] = ti_data
                print(f"  {ip}: {ti_data.get('threat_level', 'unknown')} threat level")
            except Exception as e:
                print(f"  {ip}: Error - {str(e)}")

        # Generate attack report with DShield data
        print("\nGenerating DShield attack report...")
        attack_report = data_processor.generate_attack_report(processed_events, threat_intelligence)

        # Prepare context for ChatGPT
        print("Preparing DShield context for ChatGPT...")
        context = context_injector.prepare_security_context(
            processed_events, threat_intelligence, summary
        )

        # Display results
        print("\n=== DSHIELD ANALYSIS RESULTS ===\n")

        print("DShield Security Summary:")
        print(f"  Total Events: {summary['total_events']}")
        print(f"  DShield Attacks: {summary['dshield_attacks']}")
        print(f"  DShield Blocks: {summary['dshield_blocks']}")
        print(f"  DShield Reputation Hits: {summary['dshield_reputation_hits']}")
        print(f"  High Risk Events: {summary['high_risk_events']}")
        print(f"  Unique Source IPs: {summary['unique_source_ips']}")
        print(f"  Unique Destination IPs: {summary['unique_destination_ips']}")

        print("\nSeverity Distribution:")
        for severity, count in summary['events_by_severity'].items():
            print(f"  {severity}: {count}")

        print("\nDShield Attack Patterns Detected:")
        for pattern, count in summary['attack_patterns'].items():
            print(f"  {pattern}: {count}")

        print("\nTop Source IPs:")
        for ip_info in summary['top_source_ips'][:5]:
            print(f"  {ip_info['ip']}: {ip_info['count']} events")

        print("\nGeographic Distribution:")
        for country, count in list(summary['geographic_distribution'].items())[:5]:
            print(f"  {country}: {count} attacks")

        print("\nPort Distribution:")
        for port, count in list(summary['port_distribution'].items())[:5]:
            print(f"  Port {port}: {count} attacks")

        print("\nASN Distribution:")
        for asn, count in list(summary['asn_distribution'].items())[:5]:
            print(f"  {asn}: {count} attacks")

        print("\nReputation Distribution:")
        for level, count in summary['reputation_distribution'].items():
            print(f"  {level}: {count} IPs")

        print("\nDShield Statistics:")
        print(f"  Total Attacks: {dshield_stats.total_attacks}")
        print(f"  Unique Attackers: {dshield_stats.unique_attackers}")
        print(f"  Countries Attacking: {dshield_stats.countries_attacking}")
        print(f"  Ports Targeted: {dshield_stats.ports_targeted}")
        print(f"  Protocols Used: {dshield_stats.protocols_used}")
        print(f"  ASNs Attacking: {dshield_stats.asns_attacking}")
        print(f"  Organizations Attacking: {dshield_stats.organizations_attacking}")
        print(f"  High Reputation IPs: {dshield_stats.high_reputation_ips}")
        print(f"  Average Reputation Score: {dshield_stats.average_reputation_score}")

        print("\nTop Countries by Attack Count:")
        for country_info in dshield_stats.top_countries[:5]:
            print(f"  {country_info['country']}: {country_info['count']} attacks")

        print("\nTop Ports by Attack Count:")
        for port_info in dshield_stats.top_ports[:5]:
            print(f"  Port {port_info['port']}: {port_info['count']} attacks")

        print("\nTop ASNs by Attack Count:")
        for asn_info in dshield_stats.top_asns[:5]:
            print(f"  {asn_info['asn']}: {asn_info['count']} attacks")

        print("\nThreat Intelligence Summary:")
        high_threat_ips = [
            ip for ip, ti in threat_intelligence.items() if ti.get('threat_level') == 'high'
        ]
        print(f"  High Threat IPs: {len(high_threat_ips)}")
        for ip in high_threat_ips[:5]:
            ti_data = threat_intelligence[ip]
            print(
                f"    {ip}: {ti_data.get('country', 'Unknown')} - Score: {ti_data.get('reputation_score', 'N/A')}"
            )

        print("\nAttack Report Summary:")
        print(f"  Report ID: {attack_report['report_id']}")
        print(f"  Impact Assessment: {attack_report['impact_assessment']}")
        print(f"  Confidence Level: {attack_report['confidence_level']}")
        print(f"  High Risk IPs: {len(attack_report['high_risk_ips'])}")
        print(f"  Attack Vectors: {len(attack_report['attack_vectors'])}")
        print(f"  Affected Systems: {len(attack_report['affected_systems'])}")

        print("\nRecommendations:")
        for i, rec in enumerate(attack_report['recommendations'][:5], 1):
            print(f"  {i}. {rec}")

        print("\nMitigation Actions:")
        for i, action in enumerate(attack_report['mitigation_actions'][:3], 1):
            print(f"  {i}. {action}")

        # Save results to files
        print("\nSaving results to files...")

        with open('dshield_analysis_results.json', 'w') as f:
            json.dump(
                {
                    'summary': summary,
                    'dshield_stats': dshield_stats.dict(),
                    'attack_report': attack_report,
                    'threat_intelligence': threat_intelligence,
                    'context': context,
                },
                f,
                indent=2,
                default=str,
            )

        print("Results saved to 'dshield_analysis_results.json'")

        print("\n=== DShield Analysis Complete ===")

        return summary, attack_report, threat_intelligence, dshield_stats

    except Exception as e:
        print(f"Error during DShield analysis: {str(e)}")
        raise


async def dshield_specific_analysis():
    """Perform specific DShield analysis tasks."""

    print("\n=== DShield Specific Analysis ===\n")

    try:
        es_client = ElasticsearchClient()
        dshield_client = DShieldClient()
        data_processor = DataProcessor()

        await es_client.connect()

        # Analyze specific IP addresses
        print("Analyzing specific IP addresses...")
        test_ips = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]

        for ip in test_ips:
            print(f"\nAnalyzing IP: {ip}")

            # Get DShield reputation
            try:
                reputation = await dshield_client.get_ip_reputation(ip)
                print(f"  Reputation Score: {reputation.get('reputation_score', 'N/A')}")
                print(f"  Threat Level: {reputation.get('threat_level', 'N/A')}")
                print(f"  Country: {reputation.get('country', 'N/A')}")
                print(f"  ASN: {reputation.get('asn', 'N/A')}")
                print(f"  Organization: {reputation.get('organization', 'N/A')}")
            except Exception as e:
                print(f"  Error getting reputation: {str(e)}")

            # Query events for this IP
            try:
                events = await es_client.query_events_by_ip([ip], time_range_hours=24)
                print(f"  Events found: {len(events)}")
            except Exception as e:
                print(f"  Error querying events: {str(e)}")

        # Get DShield attack summary
        print("\nGetting DShield attack summary...")
        try:
            attack_summary = await dshield_client.get_attack_summary(hours=24)
            print(f"  Total Attacks: {attack_summary.get('total_attacks', 'N/A')}")
            print(f"  Unique Attackers: {attack_summary.get('unique_attackers', 'N/A')}")
            print(f"  Top Countries: {len(attack_summary.get('top_countries', []))}")
            print(f"  Top Ports: {len(attack_summary.get('top_ports', []))}")
        except Exception as e:
            print(f"  Error getting attack summary: {str(e)}")

        # Get top attackers from DShield
        print("\nGetting DShield top attackers...")
        try:
            top_attackers = await dshield_client.get_top_attackers(hours=24)
            print(f"  Top Attackers: {len(top_attackers)}")
            for i, attacker in enumerate(top_attackers[:5], 1):
                print(
                    f"    {i}. {attacker.get('ip_address', 'N/A')}: {attacker.get('attack_count', 0)} attacks"
                )
        except Exception as e:
            print(f"  Error getting top attackers: {str(e)}")

        await es_client.close()

    except Exception as e:
        print(f"Error during specific analysis: {str(e)}")
        raise


async def main():
    """Main function to run DShield analysis examples."""

    print("DShield MCP - Elastic SIEM Integration Examples")
    print("=" * 50)

    # Run basic DShield analysis
    await dshield_security_analysis()

    # Run specific DShield analysis
    await dshield_specific_analysis()

    print("\nAll DShield analysis examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
