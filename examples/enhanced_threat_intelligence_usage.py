#!/usr/bin/env python3
"""
Enhanced Threat Intelligence Usage Example.

This example demonstrates the enhanced threat intelligence functionality
including comprehensive IP enrichment, domain enrichment, and threat
indicator correlation.

Features demonstrated:
- Comprehensive IP enrichment from multiple sources
- Domain threat intelligence
- Threat indicator correlation
- Caching and rate limiting
- Error handling

Example:
    python examples/enhanced_threat_intelligence_usage.py
"""

import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.threat_intelligence_manager import ThreatIntelligenceManager


async def demonstrate_ip_enrichment() -> None:
    """Demonstrate comprehensive IP enrichment."""
    print("=" * 60)
    print("ENHANCED THREAT INTELLIGENCE - IP ENRICHMENT")
    print("=" * 60)

    async with ThreatIntelligenceManager() as manager:
        # Test IPs with different characteristics
        test_ips = [
            "8.8.8.8",  # Google DNS (likely clean)
            "1.1.1.1",  # Cloudflare DNS (likely clean)
            "192.168.1.1",  # Private IP (should be filtered)
            "127.0.0.1",  # Localhost (should be filtered)
        ]

        for ip in test_ips:
            print(f"\n🔍 Enriching IP: {ip}")
            try:
                result = await manager.enrich_ip_comprehensive(ip)

                print(f"  📊 Overall Threat Score: {result.overall_threat_score}")
                print(f"  🎯 Confidence Score: {result.confidence_score}")
                print(f"  🌍 Sources Queried: {[s.value for s in result.sources_queried]}")
                print(f"  💾 Cache Hit: {result.cache_hit}")

                if result.geographic_data:
                    print(f"  🌐 Geographic Data: {result.geographic_data}")

                if result.network_data:
                    print(f"  🌐 Network Data: {result.network_data}")

                if result.threat_indicators:
                    print(f"  ⚠️  Threat Indicators: {len(result.threat_indicators)} found")
                    for indicator in result.threat_indicators[:3]:  # Show first 3
                        print(f"    - {indicator['indicator']} ({indicator['type']})")

            except Exception as e:
                print(f"  ❌ Error: {e}")


async def demonstrate_domain_enrichment() -> None:
    """Demonstrate domain enrichment."""
    print("\n" + "=" * 60)
    print("ENHANCED THREAT INTELLIGENCE - DOMAIN ENRICHMENT")
    print("=" * 60)

    async with ThreatIntelligenceManager() as manager:
        test_domains = [
            "google.com",
            "example.com",
            "malware-test.com",  # Hypothetical malicious domain
        ]

        for domain in test_domains:
            print(f"\n🔍 Enriching Domain: {domain}")
            try:
                result = await manager.enrich_domain_comprehensive(domain)

                print(f"  📊 Threat Score: {result.threat_score}")
                print(f"  🎯 Reputation Score: {result.reputation_score}")
                print(f"  🌍 Sources Queried: {[s.value for s in result.sources_queried]}")
                print(f"  💾 Cache Hit: {result.cache_hit}")

                if result.ip_addresses:
                    print(f"  🌐 Associated IPs: {result.ip_addresses[:3]}...")  # Show first 3

                if result.categories:
                    print(f"  🏷️  Categories: {result.categories}")

                if result.tags:
                    print(f"  🏷️  Tags: {result.tags}")

            except Exception as e:
                print(f"  ❌ Error: {e}")


async def demonstrate_threat_correlation() -> None:
    """Demonstrate threat indicator correlation."""
    print("\n" + "=" * 60)
    print("ENHANCED THREAT INTELLIGENCE - THREAT CORRELATION")
    print("=" * 60)

    async with ThreatIntelligenceManager() as manager:
        # Sample threat indicators
        indicators = [
            "8.8.8.8",
            "malware.example.com",
            "a1b2c3d4e5f6789012345678901234567890abcd",  # Sample hash
            "CVE-2021-1234",
            "192.168.1.100",
        ]

        print(f"\n🔍 Correlating {len(indicators)} threat indicators:")
        for indicator in indicators:
            print(f"  - {indicator}")

        try:
            result = await manager.correlate_threat_indicators(indicators)

            print("\n📊 Correlation Results:")
            print(f"  🆔 Correlation ID: {result['correlation_id']}")
            print(f"  🎯 Confidence Score: {result['confidence_score']}")
            print(f"  🌍 Sources Queried: {result['sources_queried']}")
            print(f"  📅 Timestamp: {result['timestamp']}")

            if result['correlations']:
                print(f"  🔗 Correlations Found: {len(result['correlations'])}")
            else:
                print("  🔗 No correlations found (placeholder implementation)")

            if result['relationships']:
                print(f"  🔗 Relationships Found: {len(result['relationships'])}")
            else:
                print("  🔗 No relationships found (placeholder implementation)")

        except Exception as e:
            print(f"  ❌ Error: {e}")


async def demonstrate_manager_capabilities() -> None:
    """Demonstrate Threat Intelligence Manager capabilities."""
    print("\n" + "=" * 60)
    print("ENHANCED THREAT INTELLIGENCE - MANAGER CAPABILITIES")
    print("=" * 60)

    async with ThreatIntelligenceManager() as manager:
        print("\n📋 Available Sources:")
        sources = manager.get_available_sources()
        for source in sources:
            print(f"  - {source.value}")

        print("\n📊 Source Status:")
        status = manager.get_source_status()
        for source_name, source_status in status.items():
            print(f"  - {source_name}:")
            print(f"    Enabled: {source_status['enabled']}")
            print(f"    Client Type: {source_status['client_type']}")
            print(f"    Has IP Reputation: {source_status['has_get_ip_reputation']}")

        print("\n⚙️  Configuration:")
        print(f"  Confidence Threshold: {manager.confidence_threshold}")
        print(f"  Max Sources Per Query: {manager.max_sources}")
        print(f"  Cache TTL: {manager.cache_ttl}")
        print(f"  Cache Size: {len(manager.cache)}")


async def demonstrate_error_handling() -> None:
    """Demonstrate error handling capabilities."""
    print("\n" + "=" * 60)
    print("ENHANCED THREAT INTELLIGENCE - ERROR HANDLING")
    print("=" * 60)

    async with ThreatIntelligenceManager() as manager:
        # Test invalid inputs
        invalid_inputs = [
            ("Invalid IP", "invalid_ip"),
            ("Empty Domain", ""),
            ("No Dots Domain", "nodots"),
            ("Empty Indicators", []),
        ]

        for test_name, test_input in invalid_inputs:
            print(f"\n🔍 Testing {test_name}: {test_input}")
            try:
                if isinstance(test_input, str):
                    if "." in test_input and any(c.isdigit() for c in test_input):
                        # Looks like an IP
                        await manager.enrich_ip_comprehensive(test_input)
                        print("  ✅ IP enrichment completed")
                    elif "." in test_input:
                        # Looks like a domain
                        await manager.enrich_domain_comprehensive(test_input)
                        print("  ✅ Domain enrichment completed")
                    else:
                        print("  ❌ Invalid input format")
                else:
                    # Empty list for indicators
                    await manager.correlate_threat_indicators(test_input)
                    print("  ✅ Correlation completed")

            except ValueError as e:
                print(f"  ⚠️  Validation Error: {e}")
            except RuntimeError as e:
                print(f"  ⚠️  Runtime Error: {e}")
            except Exception as e:
                print(f"  ❌ Unexpected Error: {e}")


async def main() -> None:
    """Main demonstration function."""
    print("🚀 Enhanced Threat Intelligence Demonstration")
    print("This example shows the enhanced threat intelligence capabilities")
    print("including multi-source enrichment, correlation, and error handling.")

    try:
        # Demonstrate various capabilities
        await demonstrate_ip_enrichment()
        await demonstrate_domain_enrichment()
        await demonstrate_threat_correlation()
        await demonstrate_manager_capabilities()
        await demonstrate_error_handling()

        print("\n" + "=" * 60)
        print("✅ Enhanced Threat Intelligence Demonstration Complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
