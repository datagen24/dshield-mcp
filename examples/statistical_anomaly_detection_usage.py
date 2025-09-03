#!/usr/bin/env python3
"""Example usage of the Statistical Anomaly Detection Tool.

This example demonstrates how to use the detect_statistical_anomalies tool
to identify anomalies in DShield SIEM data.
"""

import asyncio
import json
from typing import Dict, Any

from src.statistical_analysis_tools import StatisticalAnalysisTools
from src.elasticsearch_client import ElasticsearchClient


async def example_basic_anomaly_detection() -> None:
    """Example of basic anomaly detection with default parameters."""
    print("=== Basic Statistical Anomaly Detection ===")

    try:
        # Initialize the tools
        es_client = ElasticsearchClient()
        stats_tools = StatisticalAnalysisTools(es_client)

        # Detect anomalies with default settings
        result = await stats_tools.detect_statistical_anomalies(time_range_hours=24)

        if result["success"]:
            print("✅ Anomaly detection completed successfully!")
            print(
                f"📊 Total anomalies detected: {result['anomaly_analysis']['summary']['total_anomalies_detected']}"
            )
            print(
                f"🔍 Methods used: {', '.join(result['anomaly_analysis']['summary']['methods_applied'])}"
            )
            print(
                f"⚙️ Sensitivity threshold: {result['anomaly_analysis']['summary']['sensitivity_threshold']}"
            )

            # Show risk assessment
            risk = result['anomaly_analysis']['risk_assessment']
            print(f"⚠️ Overall risk level: {risk['overall_risk_level']}")
            print(f"📈 Risk score: {risk['risk_score']}")

            # Show recommendations
            if result['anomaly_analysis']['recommended_actions']:
                print("\n💡 Recommendations:")
                for rec in result['anomaly_analysis']['recommended_actions']:
                    print(f"   • {rec}")
        else:
            print(f"❌ Anomaly detection failed: {result['error']}")

    except Exception as e:
        print(f"❌ Error during anomaly detection: {e}")


async def example_custom_anomaly_detection() -> None:
    """Example of custom anomaly detection with specific parameters."""
    print("\n=== Custom Statistical Anomaly Detection ===")

    try:
        # Initialize the tools
        es_client = ElasticsearchClient()
        stats_tools = StatisticalAnalysisTools(es_client)

        # Custom anomaly detection parameters
        custom_params = {
            "time_range_hours": 48,  # 2 days
            "anomaly_methods": ["zscore", "iqr", "isolation_forest", "time_series"],
            "sensitivity": 3.0,  # Higher sensitivity
            "dimensions": ["source_ip", "destination_port", "bytes_transferred"],
            "return_summary_only": True,
            "max_anomalies": 100,
        }

        print(f"🔧 Using custom parameters:")
        for key, value in custom_params.items():
            print(f"   • {key}: {value}")

        # Detect anomalies with custom settings
        result = await stats_tools.detect_statistical_anomalies(**custom_params)

        if result["success"]:
            print("\n✅ Custom anomaly detection completed successfully!")
            print(
                f"📊 Total anomalies detected: {result['anomaly_analysis']['summary']['total_anomalies_detected']}"
            )

            # Show detailed results by method
            for method_name, method_data in result['anomaly_analysis'][
                'anomalies_by_method'
            ].items():
                print(f"\n🔍 {method_name.upper()} Analysis:")
                print(f"   • Anomalies found: {method_data.get('count', 0)}")
                if method_data.get('anomalies'):
                    print(f"   • Sample anomalies: {len(method_data['anomalies'])}")

            # Show patterns
            patterns = result['anomaly_analysis']['patterns']
            if patterns.get('method_agreement'):
                agreement = patterns['method_agreement']
                print(
                    f"\n🤝 Method Agreement: {agreement['agreement_level']} ({agreement['total_methods']} methods)"
                )

            if patterns.get('field_concentration'):
                concentration = patterns['field_concentration']
                print(
                    f"\n🎯 Field Concentration: {concentration['total_fields_with_anomalies']} fields have anomalies"
                )
                if concentration.get('most_anomalous_fields'):
                    print("   • Most anomalous fields:")
                    for field, count in concentration['most_anomalous_fields'][:3]:
                        print(f"     - {field}: {count} anomalies")
        else:
            print(f"❌ Custom anomaly detection failed: {result['error']}")

    except Exception as e:
        print(f"❌ Error during custom anomaly detection: {e}")


async def example_anomaly_method_comparison() -> None:
    """Example comparing different anomaly detection methods."""
    print("\n=== Anomaly Detection Method Comparison ===")

    try:
        # Initialize the tools
        es_client = ElasticsearchClient()
        stats_tools = StatisticalAnalysisTools(es_client)

        # Test each method individually
        methods = ["zscore", "iqr", "isolation_forest", "time_series"]

        for method in methods:
            print(f"\n🔍 Testing {method.upper()} method:")

            result = await stats_tools.detect_statistical_anomalies(
                time_range_hours=24, anomaly_methods=[method], sensitivity=2.5
            )

            if result["success"]:
                anomaly_count = result['anomaly_analysis']['summary']['total_anomalies_detected']
                print(f"   ✅ {method.upper()}: {anomaly_count} anomalies detected")

                # Show method-specific details
                method_data = result['anomaly_analysis']['anomalies_by_method'].get(method, {})
                if method_data.get('anomalies'):
                    print(f"   📊 Sample anomalies: {len(method_data['anomalies'])}")
            else:
                print(f"   ❌ {method.upper()}: Failed - {result['error']}")

    except Exception as e:
        print(f"❌ Error during method comparison: {e}")


async def main() -> None:
    """Run all examples."""
    print("🚀 DShield Statistical Anomaly Detection Examples")
    print("=" * 60)

    # Run examples
    await example_basic_anomaly_detection()
    await example_custom_anomaly_detection()
    await example_anomaly_method_comparison()

    print("\n" + "=" * 60)
    print("✅ All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
