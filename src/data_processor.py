"""
Data processor for formatting and structuring DShield SIEM data for AI consumption.
Optimized for DShield SIEM data structures and patterns.
"""

import json
import os
import traceback
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import structlog
from .models import (
    SecurityEvent, ThreatIntelligence, AttackReport, SecuritySummary, 
    EventSeverity, EventCategory, DShieldAttack, DShieldReputation, 
    DShieldTopAttacker, DShieldGeographicData, DShieldPortData, DShieldStatistics
)

logger = structlog.get_logger(__name__)


def _is_debug_mode() -> bool:
    """Check if we're running in debug mode or test mode."""
    # Check for debug log level
    if os.getenv('LOG_LEVEL', '').upper() in ['DEBUG', 'TRACE']:
        return True
    
    # Check if we're running tests (common test indicators)
    test_indicators = [
        'pytest' in os.getenv('PYTEST_CURRENT_TEST', ''),
        'test' in os.getenv('PYTHONPATH', ''),
        'PYTEST' in os.environ,
        'TESTING' in os.environ,
        'UNITTEST' in os.environ,
    ]
    
    return any(test_indicators)


class DataProcessor:
    """Process and structure DShield SIEM data for AI analysis."""
    
    def __init__(self):
        # DShield-specific attack patterns and signatures
        self.dshield_attack_patterns = {
            'brute_force': ['failed login', 'authentication failure', 'invalid credentials', 'ssh brute force'],
            'port_scan': ['port scan', 'nmap', 'masscan', 'port scanning', 'syn scan'],
            'sql_injection': ['sql injection', 'sql error', 'database error', 'mysql error'],
            'xss': ['cross-site scripting', 'xss', 'script injection', 'javascript injection'],
            'ddos': ['denial of service', 'ddos', 'flood attack', 'syn flood', 'udp flood'],
            'malware': ['malware', 'virus', 'trojan', 'ransomware', 'botnet'],
            'phishing': ['phishing', 'suspicious email', 'credential harvesting', 'social engineering'],
            'reconnaissance': ['reconnaissance', 'information gathering', 'enumeration', 'network scan'],
            'exploit': ['exploit', 'vulnerability', 'cve', 'buffer overflow', 'code injection'],
            'backdoor': ['backdoor', 'reverse shell', 'command injection', 'remote access'],
            'data_exfiltration': ['data theft', 'exfiltration', 'sensitive data', 'confidential'],
            'privilege_escalation': ['privilege escalation', 'sudo', 'root access', 'admin access'],
            'persistence': ['persistence', 'startup', 'registry', 'cron job', 'scheduled task']
        }
        
        # DShield-specific severity mapping
        self.dshield_severity_mapping = {
            'critical': EventSeverity.CRITICAL,
            'high': EventSeverity.HIGH,
            'medium': EventSeverity.MEDIUM,
            'low': EventSeverity.LOW,
            'info': EventSeverity.LOW,
            'warning': EventSeverity.MEDIUM,
            'error': EventSeverity.HIGH,
            'attack': EventSeverity.HIGH,
            'block': EventSeverity.MEDIUM,
            'reputation': EventSeverity.MEDIUM
        }
        
        # DShield-specific category mapping
        self.dshield_category_mapping = {
            'attack': EventCategory.ATTACK,
            'block': EventCategory.BLOCK,
            'reputation': EventCategory.REPUTATION,
            'geographic': EventCategory.GEOGRAPHIC,
            'asn': EventCategory.ASN,
            'organization': EventCategory.ORGANIZATION,
            'port': EventCategory.PORT,
            'protocol': EventCategory.PROTOCOL,
            'network': EventCategory.NETWORK,
            'authentication': EventCategory.AUTHENTICATION,
            'malware': EventCategory.MALWARE,
            'intrusion': EventCategory.INTRUSION,
            'data_exfiltration': EventCategory.DATA_EXFILTRATION,
            'reconnaissance': EventCategory.RECONNAISSANCE,
            'denial_of_service': EventCategory.DENIAL_OF_SERVICE,
            'other': EventCategory.OTHER
        }
    
    def process_security_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and normalize security events from DShield SIEM."""
        
        processed_events = []
        
        for event in events:
            try:
                # Skip None events
                if event is None:
                    continue
                    
                # Normalize event data
                normalized_event = self._normalize_event(event)
                
                # Detect attack patterns
                normalized_event['attack_patterns'] = self._detect_attack_patterns([normalized_event])
                
                # Add DShield-specific enrichments
                normalized_event = self._enrich_dshield_data(normalized_event)
                
                processed_events.append(normalized_event)
                
            except Exception as e:
                if _is_debug_mode():
                    logger.warning("Failed to process event", 
                                  event_id=event.get('id') if event else None, 
                                  error=str(e),
                                  stack_trace=traceback.format_exc())
                else:
                    logger.warning("Failed to process event", 
                                  event_id=event.get('id') if event else None, 
                                  error=str(e))
                continue
        
        logger.info("Processed security events", 
                   total_events=len(events),
                   processed_events=len(processed_events))
        
        return processed_events
    
    def process_dshield_attacks(self, attacks: List[Dict[str, Any]]) -> List[DShieldAttack]:
        """Process DShield attack events into structured format."""
        
        processed_attacks = []
        
        for attack in attacks:
            try:
                # Create DShieldAttack object
                dshield_attack = DShieldAttack(
                    id=attack.get('id', str(uuid.uuid4())),
                    timestamp=attack.get('timestamp', datetime.utcnow()),
                    source_ip=attack.get('source_ip', ''),
                    destination_ip=attack.get('destination_ip'),
                    source_port=attack.get('source_port'),
                    destination_port=attack.get('destination_port'),
                    protocol=attack.get('protocol'),
                    attack_type=attack.get('event_type', 'unknown'),
                    severity=self.dshield_severity_mapping.get(
                        attack.get('severity', 'medium'), 
                        EventSeverity.HIGH
                    ),
                    description=attack.get('description', ''),
                    country=attack.get('country'),
                    asn=attack.get('asn'),
                    organization=attack.get('organization'),
                    reputation_score=attack.get('reputation_score'),
                    attack_count=attack.get('attack_count', 1),
                    first_seen=attack.get('first_seen'),
                    last_seen=attack.get('last_seen'),
                    tags=attack.get('tags', []),
                    attack_methods=attack.get('attack_types', []),
                    raw_data=attack.get('raw_data', {}),
                    indices=attack.get('indices', [])
                )
                
                processed_attacks.append(dshield_attack)
                
            except Exception as e:
                if _is_debug_mode():
                    logger.warning("Failed to process DShield attack", 
                                  attack_id=attack.get('id'), 
                                  error=str(e),
                                  stack_trace=traceback.format_exc())
                else:
                    logger.warning("Failed to process DShield attack", 
                                  attack_id=attack.get('id'), 
                                  error=str(e))
                continue
        
        return processed_attacks
    
    def process_dshield_reputation(self, reputation_data: List[Dict[str, Any]]) -> Dict[str, DShieldReputation]:
        """Process DShield reputation data into structured format."""
        
        processed_reputation = {}
        
        for rep_data in reputation_data:
            try:
                ip_address = rep_data.get('source_ip') or rep_data.get('ip_address')
                if not ip_address:
                    continue
                
                # Create DShieldReputation object
                dshield_rep = DShieldReputation(
                    ip_address=ip_address,
                    reputation_score=rep_data.get('reputation_score'),
                    threat_level=rep_data.get('threat_level'),
                    country=rep_data.get('country'),
                    asn=rep_data.get('asn'),
                    organization=rep_data.get('organization'),
                    first_seen=rep_data.get('first_seen'),
                    last_seen=rep_data.get('last_seen'),
                    attack_types=rep_data.get('attack_types', []),
                    tags=rep_data.get('tags', []),
                    attack_count=rep_data.get('attack_count'),
                    port_count=rep_data.get('port_count'),
                    service_count=rep_data.get('service_count'),
                    raw_data=rep_data.get('raw_data', {})
                )
                
                processed_reputation[ip_address] = dshield_rep
                
            except Exception as e:
                if _is_debug_mode():
                    logger.warning("Failed to process DShield reputation", 
                                  ip=rep_data.get('source_ip'), 
                                  error=str(e),
                                  stack_trace=traceback.format_exc())
                else:
                    logger.warning("Failed to process DShield reputation", 
                                  ip=rep_data.get('source_ip'), 
                                  error=str(e))
                continue
        
        return processed_reputation
    
    def process_dshield_top_attackers(self, attackers: List[Dict[str, Any]]) -> List[DShieldTopAttacker]:
        """Process DShield top attackers data into structured format."""
        
        processed_attackers = []
        
        for attacker in attackers:
            try:
                # Create DShieldTopAttacker object
                dshield_attacker = DShieldTopAttacker(
                    ip_address=attacker.get('source_ip', ''),
                    attack_count=attacker.get('attack_count', 0),
                    country=attacker.get('country'),
                    asn=attacker.get('asn'),
                    organization=attacker.get('organization'),
                    reputation_score=attacker.get('reputation_score'),
                    first_seen=attacker.get('first_seen'),
                    last_seen=attacker.get('last_seen'),
                    attack_types=attacker.get('attack_types', []),
                    tags=attacker.get('tags', []),
                    target_ports=attacker.get('target_ports', []),
                    target_services=attacker.get('target_services', []),
                    raw_data=attacker.get('raw_data', {})
                )
                
                processed_attackers.append(dshield_attacker)
                
            except Exception as e:
                if _is_debug_mode():
                    logger.warning("Failed to process DShield top attacker", 
                                  ip=attacker.get('source_ip'), 
                                  error=str(e),
                                  stack_trace=traceback.format_exc())
                else:
                    logger.warning("Failed to process DShield top attacker", 
                                  ip=attacker.get('source_ip'), 
                                  error=str(e))
                continue
        
        return processed_attackers
    
    def generate_dshield_summary(self, events: List[Dict[str, Any]]) -> DShieldStatistics:
        """Generate DShield-specific security summary."""
        
        if not events:
            return self._create_empty_dshield_statistics()
        
        # Extract DShield-specific data
        dshield_attacks = [e for e in events if e.get('event_type') == 'attack']
        dshield_blocks = [e for e in events if e.get('event_type') == 'block']
        dshield_reputation = [e for e in events if e.get('event_type') == 'reputation']
        
        # Compile statistics
        stats = DShieldStatistics(
            time_range_hours=24,  # Default, should be configurable
            total_attacks=len(dshield_attacks),
            unique_attackers=len(set(str(e.get('source_ip')) if isinstance(e.get('source_ip'), (list, dict)) else e.get('source_ip') for e in dshield_attacks if e.get('source_ip'))),
            total_targets=len(set(str(e.get('destination_ip')) if isinstance(e.get('destination_ip'), (list, dict)) else e.get('destination_ip') for e in dshield_attacks if e.get('destination_ip'))),
            countries_attacking=len(set(str(e.get('country')) if isinstance(e.get('country'), (list, dict)) else e.get('country') for e in events if e.get('country'))),
            ports_targeted=len(set(str(e.get('destination_port')) if isinstance(e.get('destination_port'), (list, dict)) else e.get('destination_port') for e in events if e.get('destination_port'))),
            protocols_used=len(set(str(e.get('protocol')) if isinstance(e.get('protocol'), (list, dict)) else e.get('protocol') for e in events if e.get('protocol'))),
            asns_attacking=len(set(str(e.get('asn')) if isinstance(e.get('asn'), (list, dict)) else e.get('asn') for e in events if e.get('asn'))),
            organizations_attacking=len(set(str(e.get('organization')) if isinstance(e.get('organization'), (list, dict)) else e.get('organization') for e in events if e.get('organization'))),
            high_reputation_ips=len([e for e in events if e.get('reputation_score', 0) > 80]),
            top_countries=self._get_top_countries(events),
            top_ports=self._get_top_ports(events),
            top_protocols=self._get_top_protocols(events),
            top_asns=self._get_top_asns(events),
            top_organizations=self._get_top_organizations(events),
            average_reputation_score=self._calculate_average_reputation(events),
            indices_queried=list(set(
                str(index) for e in events for index in e.get('indices', [])
            ))
        )
        
        return stats
    
    def generate_security_summary(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate security summary statistics with DShield enrichment."""
        
        if not events:
            return self._create_empty_summary()
        
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'time_range_hours': 24,  # Default, should be configurable
            'total_events': len(events),
            'events_by_severity': {},
            'events_by_category': {},
            'unique_source_ips': 0,
            'unique_destination_ips': 0,
            'top_source_ips': [],
            'top_destination_ips': [],
            'high_risk_events': 0,
            'threat_intelligence_hits': 0,
            'attack_patterns': {},
            'timeline': {},
            'indices_queried': [],
            
            # DShield-specific statistics
            'dshield_attacks': 0,
            'dshield_blocks': 0,
            'dshield_reputation_hits': 0,
            'top_attackers': [],
            'geographic_distribution': {},
            'port_distribution': {},
            'asn_distribution': {},
            'organization_distribution': {},
            'reputation_distribution': {}
        }
        
        # Extract unique IPs
        source_ips = set()
        destination_ips = set()
        ip_event_counts = Counter()
        
        # Process events
        for event in events:
            # Count by severity
            severity = event.get('severity', 'medium')
            # Ensure severity is hashable
            if isinstance(severity, (list, dict)):
                severity = str(severity)
            summary['events_by_severity'][severity] = summary['events_by_severity'].get(severity, 0) + 1
            
            # Count by category
            category = event.get('category', 'other')
            # Ensure category is hashable
            if isinstance(category, (list, dict)):
                category = str(category)
            summary['events_by_category'][category] = summary['events_by_category'].get(category, 0) + 1
            
            # Track IPs - ensure they are hashable
            source_ip = event.get('source_ip')
            if source_ip:
                if isinstance(source_ip, (list, dict)):
                    source_ip_str = str(source_ip)
                else:
                    source_ip_str = str(source_ip)
                source_ips.add(source_ip_str)
                ip_event_counts[source_ip_str] += 1
            
            destination_ip = event.get('destination_ip')
            if destination_ip:
                if isinstance(destination_ip, (list, dict)):
                    destination_ip_str = str(destination_ip)
                else:
                    destination_ip_str = str(destination_ip)
                destination_ips.add(destination_ip_str)
            
            # Count high-risk events
            if severity in ['high', 'critical']:
                summary['high_risk_events'] += 1
            
            # DShield-specific counting
            if event.get('event_type') == 'attack':
                summary['dshield_attacks'] += 1
            elif event.get('event_type') == 'block':
                summary['dshield_blocks'] += 1
            elif event.get('event_type') == 'reputation':
                summary['dshield_reputation_hits'] += 1
            
            # Track indices
            if 'indices' in event:
                indices = event['indices']
                if isinstance(indices, list):
                    for index in indices:
                        if isinstance(index, (list, dict)):
                            summary['indices_queried'].append(str(index))
                        else:
                            summary['indices_queried'].append(str(index))
                else:
                    summary['indices_queried'].append(str(indices))
        
        # Update summary with IP statistics
        summary['unique_source_ips'] = len(source_ips)
        summary['unique_destination_ips'] = len(destination_ips)
        
        # Get top source IPs
        summary['top_source_ips'] = [
            {'ip': ip, 'count': count} 
            for ip, count in ip_event_counts.most_common(10)
        ]
        
        # Generate DShield-specific distributions
        summary['geographic_distribution'] = self._get_geographic_distribution(events)
        summary['port_distribution'] = self._get_port_distribution(events)
        summary['asn_distribution'] = self._get_asn_distribution(events)
        summary['organization_distribution'] = self._get_organization_distribution(events)
        summary['reputation_distribution'] = self._get_reputation_distribution(events)
        
        # Generate timeline
        summary['timeline'] = self._generate_timeline(events)
        
        # Detect attack patterns
        summary['attack_patterns'] = self._detect_attack_patterns(events)
        
        # Remove duplicates from indices
        summary['indices_queried'] = list(set(summary['indices_queried']))
        
        return summary
    
    def generate_attack_report(
        self, 
        events: List[Dict[str, Any]], 
        threat_intelligence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate structured attack report with DShield data."""
        
        if not events:
            return self._create_empty_attack_report()
        
        threat_intelligence = threat_intelligence or {}
        
        # Generate report ID
        report_id = str(uuid.uuid4())
        
        # Analyze events
        analysis = self._analyze_events(events)
        
        # Extract threat indicators
        threat_indicators = self._extract_threat_indicators(events, threat_intelligence)
        
        # Identify attack vectors
        attack_vectors = self._identify_attack_vectors(events)
        
        # Determine affected systems
        affected_systems = self._identify_affected_systems(events)
        
        # Assess impact
        impact_assessment = self._assess_impact(events, threat_indicators)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(events, threat_indicators, impact_assessment)
        
        # Process DShield-specific data
        dshield_attacks = self.process_dshield_attacks([e for e in events if e.get('event_type') == 'attack'])
        dshield_reputation = self.process_dshield_reputation([e for e in events if e.get('event_type') == 'reputation'])
        top_attackers = self.process_dshield_top_attackers([e for e in events if e.get('attack_count', 0) > 1])
        
        # Create attack report
        report = {
            'report_id': report_id,
            'timestamp': datetime.utcnow().isoformat(),
            'title': f"Security Incident Report - {report_id[:8]}",
            'summary': self._generate_executive_summary(events, threat_indicators),
            'total_events': len(events),
            'unique_ips': len(set(str(e.get('source_ip')) if isinstance(e.get('source_ip'), (list, dict)) else e.get('source_ip') for e in events if e.get('source_ip'))),
            'time_range': self._calculate_time_range(events),
            'threat_indicators': threat_indicators,
            'high_risk_ips': self._identify_high_risk_ips(events, threat_intelligence),
            'attack_vectors': attack_vectors,
            'affected_systems': affected_systems,
            'impact_assessment': impact_assessment,
            'dshield_attacks': [attack.dict() for attack in dshield_attacks],
            'dshield_reputation': {ip: rep.dict() for ip, rep in dshield_reputation.items()},
            'top_attackers': [attacker.dict() for attacker in top_attackers],
            'recommendations': recommendations,
            'mitigation_actions': self._generate_mitigation_actions(events, threat_indicators),
            'confidence_level': self._assess_confidence_level(events, threat_intelligence),
            'tags': self._extract_tags(events),
            'events': events,
            'threat_intelligence': threat_intelligence
        }
        
        return report
    
    def extract_unique_ips(self, events: List[Dict[str, Any]]) -> List[str]:
        """Extract unique IP addresses from events."""
        unique_ips = set()
        
        for event in events:
            if event.get('source_ip'):
                unique_ips.add(str(event['source_ip']) if isinstance(event['source_ip'], (list, dict)) else event['source_ip'])
            if event.get('destination_ip'):
                unique_ips.add(str(event['destination_ip']) if isinstance(event['destination_ip'], (list, dict)) else event['destination_ip'])
        
        return list(unique_ips)
    
    def _normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event data structure."""
        
        # Ensure severity and category are strings before using as dictionary keys
        severity_raw = event.get('severity', 'medium')
        if isinstance(severity_raw, (list, dict)):
            severity = str(severity_raw)
        else:
            severity = str(severity_raw)
            
        category_raw = event.get('category', 'other')
        if isinstance(category_raw, (list, dict)):
            category = str(category_raw)
        else:
            category = str(category_raw)
        
        normalized = {
            'id': event.get('id', str(uuid.uuid4())),
            'timestamp': event.get('timestamp', datetime.utcnow()),
            'source_ip': event.get('source_ip'),
            'destination_ip': event.get('destination_ip'),
            'source_port': event.get('source_port'),
            'destination_port': event.get('destination_port'),
            'protocol': event.get('protocol'),
            'event_type': event.get('event_type', 'unknown'),
            'severity': self.dshield_severity_mapping.get(
                severity, 
                EventSeverity.MEDIUM
            ).value,
            'category': self.dshield_category_mapping.get(
                category, 
                EventCategory.OTHER
            ).value,
            'description': event.get('description', ''),
            'country': event.get('country'),
            'asn': event.get('asn'),
            'organization': event.get('organization'),
            'reputation_score': event.get('reputation_score'),
            'attack_count': event.get('attack_count'),
            'first_seen': event.get('first_seen'),
            'last_seen': event.get('last_seen'),
            'tags': event.get('tags', []),
            'attack_types': event.get('attack_types', []),
            'raw_data': event.get('raw_data', {}),
            'indices': event.get('indices', [])
        }
        
        return normalized
    
    def _enrich_dshield_data(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich event with DShield-specific data."""
        
        # Add threat level based on reputation score
        reputation_score = event.get('reputation_score')
        if reputation_score is not None:
            if reputation_score >= 80:
                event['threat_level'] = 'high'
            elif reputation_score >= 50:
                event['threat_level'] = 'medium'
            else:
                event['threat_level'] = 'low'
        else:
            event['threat_level'] = 'unknown'
        
        # Add geographic context
        if event.get('country'):
            event['geographic_context'] = f"Attacker from {event['country']}"
        
        # Add ASN context
        if event.get('asn'):
            event['asn_context'] = f"ASN: {event['asn']}"
        
        # Add organization context
        if event.get('organization'):
            event['organization_context'] = f"Organization: {event['organization']}"
        
        return event
    
    def _detect_attack_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Detect attack patterns in events."""
        
        pattern_counts = Counter()
        
        for event in events:
            # Robustly handle both strings and lists for description and event_type
            description_raw = event.get('description', '')
            if isinstance(description_raw, list):
                description = ' '.join(map(str, description_raw)).lower()
            else:
                description = str(description_raw).lower()
            
            event_type_raw = event.get('event_type', '')
            if isinstance(event_type_raw, list):
                event_type = ' '.join(map(str, event_type_raw)).lower()
            else:
                event_type = str(event_type_raw).lower()
            
            for pattern, keywords in self.dshield_attack_patterns.items():
                if any(keyword in description or keyword in event_type for keyword in keywords):
                    pattern_counts[pattern] += 1
        
        return dict(pattern_counts)
    
    def _get_top_countries(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get top countries by attack count."""
        country_counts = Counter()
        for event in events:
            if event.get('country'):
                country_counts[str(event['country']) if isinstance(event['country'], (list, dict)) else event['country']] += 1
        
        return [{'country': country, 'count': count} 
                for country, count in country_counts.most_common(10)]
    
    def _get_top_ports(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get top ports by attack count."""
        port_counts = Counter()
        for event in events:
            if event.get('destination_port'):
                port_counts[str(event['destination_port']) if isinstance(event['destination_port'], (list, dict)) else event['destination_port']] += 1
        
        return [{'port': port, 'count': count} 
                for port, count in port_counts.most_common(10)]
    
    def _get_top_protocols(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get top protocols by attack count."""
        protocol_counts = Counter()
        for event in events:
            if event.get('protocol'):
                protocol_counts[str(event['protocol']) if isinstance(event['protocol'], (list, dict)) else event['protocol']] += 1
        
        return [{'protocol': protocol, 'count': count} 
                for protocol, count in protocol_counts.most_common(10)]
    
    def _get_top_asns(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get top ASNs by attack count."""
        asn_counts = Counter()
        for event in events:
            if event.get('asn'):
                asn_counts[str(event['asn']) if isinstance(event['asn'], (list, dict)) else event['asn']] += 1
        
        return [{'asn': asn, 'count': count} 
                for asn, count in asn_counts.most_common(10)]
    
    def _get_top_organizations(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get top organizations by attack count."""
        org_counts = Counter()
        for event in events:
            if event.get('organization'):
                org_counts[str(event['organization']) if isinstance(event['organization'], (list, dict)) else event['organization']] += 1
        
        return [{'organization': org, 'count': count} 
                for org, count in org_counts.most_common(10)]
    
    def _calculate_average_reputation(self, events: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate average reputation score."""
        scores = [e.get('reputation_score') for e in events if e.get('reputation_score') is not None]
        return sum(scores) / len(scores) if scores else None
    
    def _get_geographic_distribution(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get geographic distribution of attacks."""
        distribution = Counter()
        for event in events:
            if event.get('country'):
                distribution[str(event['country']) if isinstance(event['country'], (list, dict)) else event['country']] += 1
        return dict(distribution)
    
    def _get_port_distribution(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get port distribution of attacks."""
        distribution = Counter()
        for event in events:
            if event.get('destination_port'):
                distribution[str(event['destination_port']) if isinstance(event['destination_port'], (list, dict)) else event['destination_port']] += 1
        return dict(distribution)
    
    def _get_asn_distribution(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get ASN distribution of attacks."""
        distribution = Counter()
        for event in events:
            if event.get('asn'):
                distribution[str(event['asn']) if isinstance(event['asn'], (list, dict)) else event['asn']] += 1
        return dict(distribution)
    
    def _get_organization_distribution(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get organization distribution of attacks."""
        distribution = Counter()
        for event in events:
            if event.get('organization'):
                distribution[str(event['organization']) if isinstance(event['organization'], (list, dict)) else event['organization']] += 1
        return dict(distribution)
    
    def _get_reputation_distribution(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get reputation score distribution."""
        distribution = Counter()
        for event in events:
            score = event.get('reputation_score')
            if score is not None:
                if score >= 80:
                    distribution['high'] += 1
                elif score >= 50:
                    distribution['medium'] += 1
                else:
                    distribution['low'] += 1
        return dict(distribution)
    
    def _generate_timeline(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Generate timeline of events."""
        timeline = Counter()
        for event in events:
            timestamp = event.get('timestamp')
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    hour = dt.strftime('%Y-%m-%d %H:00')
                    timeline[hour] += 1
                except:
                    continue
        return dict(timeline)
    
    def _analyze_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze events for patterns and insights."""
        # Filter out unhashable values for Counter
        severity_values = []
        category_values = []
        
        for event in events:
            severity = event.get('severity')
            category = event.get('category')
            
            # Convert to string if it's not hashable
            if severity is not None:
                if isinstance(severity, (list, dict)):
                    severity_values.append(str(severity))
                else:
                    severity_values.append(severity)
            
            if category is not None:
                if isinstance(category, (list, dict)):
                    category_values.append(str(category))
                else:
                    category_values.append(category)
        
        # Extract unique IPs safely
        unique_ips = set()
        for event in events:
            source_ip = event.get('source_ip')
            if source_ip:
                if isinstance(source_ip, (list, dict)):
                    unique_ips.add(str(source_ip))
                else:
                    unique_ips.add(str(source_ip))
        
        return {
            'total_events': len(events),
            'unique_ips': len(unique_ips),
            'attack_patterns': self._detect_attack_patterns(events),
            'severity_distribution': Counter(severity_values),
            'category_distribution': Counter(category_values)
        }
    
    def _extract_threat_indicators(self, events: List[Dict[str, Any]], threat_intelligence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract threat indicators from events and threat intelligence."""
        indicators = []
        
        for event in events:
            if event.get('reputation_score', 0) > 80:
                indicators.append({
                    'type': 'high_reputation_score',
                    'value': str(event.get('source_ip')) if isinstance(event.get('source_ip'), (list, dict)) else event.get('source_ip'),
                    'score': event.get('reputation_score'),
                    'description': f"IP {str(event.get('source_ip')) if isinstance(event.get('source_ip'), (list, dict)) else event.get('source_ip')} has high reputation score"
                })
            
            if event.get('attack_count', 0) > 10:
                indicators.append({
                    'type': 'high_attack_count',
                    'value': str(event.get('source_ip')) if isinstance(event.get('source_ip'), (list, dict)) else event.get('source_ip'),
                    'count': event.get('attack_count'),
                    'description': f"IP {str(event.get('source_ip')) if isinstance(event.get('source_ip'), (list, dict)) else event.get('source_ip')} has high attack count"
                })
        
        return indicators
    
    def _identify_attack_vectors(self, events: List[Dict[str, Any]]) -> List[str]:
        """Identify attack vectors from events."""
        vectors = set()
        
        for event in events:
            if event.get('destination_port'):
                vectors.add(f"Port {str(event['destination_port']) if isinstance(event['destination_port'], (list, dict)) else event['destination_port']}")
            
            if event.get('protocol'):
                vectors.add(f"Protocol {str(event['protocol']) if isinstance(event['protocol'], (list, dict)) else event['protocol']}")
            
            if event.get('attack_types'):
                # Handle attack_types that might contain unhashable types
                attack_types = event['attack_types']
                if isinstance(attack_types, list):
                    for attack_type in attack_types:
                        if isinstance(attack_type, (list, dict)):
                            vectors.add(str(attack_type))
                        else:
                            vectors.add(attack_type)
                else:
                    vectors.add(str(attack_types))
        
        return list(vectors)
    
    def _identify_affected_systems(self, events: List[Dict[str, Any]]) -> List[str]:
        """Identify affected systems from events."""
        systems = set()
        
        for event in events:
            if event.get('destination_ip'):
                systems.add(str(event['destination_ip']) if isinstance(event['destination_ip'], (list, dict)) else event['destination_ip'])
        
        return list(systems)
    
    def _assess_impact(self, events: List[Dict[str, Any]], threat_indicators: List[Dict[str, Any]]) -> str:
        """Assess the impact of the security incident."""
        high_severity_count = len([e for e in events if e.get('severity') in ['high', 'critical']])
        high_reputation_count = len([i for i in threat_indicators if i.get('type') == 'high_reputation_score'])
        
        if high_severity_count > 10 or high_reputation_count > 5:
            return "High - Multiple high-severity events and high-reputation attackers detected"
        elif high_severity_count > 5 or high_reputation_count > 2:
            return "Medium - Several high-severity events or high-reputation attackers detected"
        else:
            return "Low - Limited high-severity events detected"
    
    def _generate_recommendations(self, events: List[Dict[str, Any]], threat_indicators: List[Dict[str, Any]], impact: str) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        # Basic recommendations
        recommendations.append("Review and update firewall rules to block suspicious IP addresses")
        recommendations.append("Implement rate limiting for authentication attempts")
        recommendations.append("Enable logging and monitoring for all critical systems")
        
        # DShield-specific recommendations
        if any(e.get('reputation_score', 0) > 80 for e in events):
            recommendations.append("Block IP addresses with high DShield reputation scores")
        
        if any(e.get('attack_count', 0) > 10 for e in events):
            recommendations.append("Implement additional monitoring for IPs with high attack counts")
        
        if impact == "High":
            recommendations.append("Consider implementing additional security controls")
            recommendations.append("Review incident response procedures")
        
        return recommendations
    
    def _generate_mitigation_actions(self, events: List[Dict[str, Any]], threat_indicators: List[Dict[str, Any]]) -> List[str]:
        """Generate specific mitigation actions."""
        actions = []
        
        # Immediate actions
        high_reputation_ips = [i.get('value') for i in threat_indicators if i.get('type') == 'high_reputation_score']
        if high_reputation_ips:
            actions.append(f"Block IP addresses: {', '.join(high_reputation_ips[:5])}")
        
        # Monitoring actions
        actions.append("Increase monitoring frequency for affected systems")
        actions.append("Review and update security policies")
        
        return actions
    
    def _assess_confidence_level(self, events: List[Dict[str, Any]], threat_intelligence: Dict[str, Any]) -> str:
        """Assess confidence level of the analysis."""
        if len(events) > 50 and threat_intelligence:
            return "High"
        elif len(events) > 20:
            return "Medium"
        else:
            return "Low"
    
    def _extract_tags(self, events: List[Dict[str, Any]]) -> List[str]:
        """Extract tags from events."""
        tags = set()
        for event in events:
            event_tags = event.get('tags', [])
            if isinstance(event_tags, list):
                for tag in event_tags:
                    if isinstance(tag, (list, dict)):
                        tags.add(str(tag))
                    else:
                        tags.add(tag)
            else:
                tags.add(str(event_tags))
        return list(tags)
    
    def _generate_executive_summary(self, events: List[Dict[str, Any]], threat_indicators: List[Dict[str, Any]]) -> str:
        """Generate executive summary of the security incident."""
        total_events = len(events)
        
        # Extract unique IPs safely
        unique_ips = set()
        for event in events:
            source_ip = event.get('source_ip')
            if source_ip:
                if isinstance(source_ip, (list, dict)):
                    unique_ips.add(str(source_ip))
                else:
                    unique_ips.add(str(source_ip))
        
        high_severity = len([e for e in events if e.get('severity') in ['high', 'critical']])
        
        summary = f"Security incident involving {total_events} events from {len(unique_ips)} unique IP addresses. "
        summary += f"{high_severity} high-severity events detected. "
        
        if threat_indicators:
            summary += f"{len(threat_indicators)} threat indicators identified requiring immediate attention."
        
        return summary
    
    def _identify_high_risk_ips(self, events: List[Dict[str, Any]], threat_intelligence: Dict[str, Any]) -> List[str]:
        """Identify high-risk IP addresses."""
        high_risk_ips = set()
        
        for event in events:
            source_ip = event.get('source_ip')
            if source_ip:
                if isinstance(source_ip, (list, dict)):
                    source_ip_str = str(source_ip)
                else:
                    source_ip_str = str(source_ip)
                
                if event.get('reputation_score', 0) > 80:
                    high_risk_ips.add(source_ip_str)
                elif event.get('attack_count', 0) > 10:
                    high_risk_ips.add(source_ip_str)
        
        return list(high_risk_ips)
    
    def _create_empty_summary(self) -> Dict[str, Any]:
        """Create empty security summary."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'time_range_hours': 24,
            'total_events': 0,
            'events_by_severity': {},
            'events_by_category': {},
            'unique_source_ips': 0,
            'unique_destination_ips': 0,
            'top_source_ips': [],
            'top_destination_ips': [],
            'high_risk_events': 0,
            'threat_intelligence_hits': 0,
            'attack_patterns': {},
            'timeline': {},
            'indices_queried': [],
            'dshield_attacks': 0,
            'dshield_blocks': 0,
            'dshield_reputation_hits': 0,
            'top_attackers': [],
            'geographic_distribution': {},
            'port_distribution': {},
            'asn_distribution': {},
            'organization_distribution': {},
            'reputation_distribution': {}
        }
    
    def _create_empty_attack_report(self) -> Dict[str, Any]:
        """Create empty attack report."""
        return {
            'report_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'title': 'No Security Events Detected',
            'summary': 'No security events were found in the specified time range.',
            'total_events': 0,
            'unique_ips': 0,
            'time_range': {},
            'threat_indicators': [],
            'high_risk_ips': [],
            'attack_vectors': [],
            'affected_systems': [],
            'impact_assessment': 'None',
            'dshield_attacks': [],
            'dshield_reputation': {},
            'top_attackers': [],
            'recommendations': ['Continue monitoring for security events'],
            'mitigation_actions': [],
            'confidence_level': 'Low',
            'tags': [],
            'events': [],
            'threat_intelligence': {}
        }
    
    def _calculate_time_range(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate time range from events, handling empty sequences."""
        # Extract valid timestamps
        timestamps = []
        for event in events:
            timestamp = event.get('timestamp')
            if timestamp:
                # Handle both string and datetime timestamps
                if isinstance(timestamp, str):
                    try:
                        # Try to parse ISO format timestamps
                        if timestamp.endswith('Z'):
                            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            timestamp = datetime.fromisoformat(timestamp)
                    except ValueError:
                        # Skip malformed timestamps
                        continue
                elif isinstance(timestamp, datetime):
                    timestamps.append(timestamp)
                else:
                    # Skip non-datetime objects
                    continue
        
        if timestamps:
            return {
                'start': min(timestamps),
                'end': max(timestamps)
            }
        else:
            # Return current time as fallback
            current_time = datetime.utcnow()
            return {
                'start': current_time,
                'end': current_time
            }
    
    def _create_empty_dshield_statistics(self) -> DShieldStatistics:
        """Create empty DShield statistics."""
        return DShieldStatistics(
            time_range_hours=24,
            total_attacks=0,
            unique_attackers=0,
            total_targets=0,
            countries_attacking=0,
            ports_targeted=0,
            protocols_used=0,
            asns_attacking=0,
            organizations_attacking=0,
            high_reputation_ips=0,
            top_countries=[],
            top_ports=[],
            top_protocols=[],
            top_asns=[],
            top_organizations=[],
            average_reputation_score=None,
            indices_queried=[]
        ) 