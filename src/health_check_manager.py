"""Health check manager for DShield MCP server dependencies."""
import asyncio
import subprocess
import sys
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class HealthCheckManager:
    """Manages health checks for all dependencies."""
    
    def __init__(self) -> None:
        """Initialize the health check manager."""
        self.health_status: Dict[str, bool] = {}
        self.health_details: Dict[str, Dict[str, Any]] = {}
        self.health_checks = {}

    async def check_elasticsearch(self) -> bool:
        """Check Elasticsearch connectivity and health.
        
        Returns:
            bool: True if Elasticsearch is healthy, False otherwise
        """
        try:
            # This will be implemented when we have access to the elastic client
            # For now, we'll check if the environment variables are set
            from src.elasticsearch_client import ElasticsearchClient
            
            # Try to create a client and check connection
            client = ElasticsearchClient()
            # Check if we can connect to Elasticsearch
            is_healthy = await client.check_health()
            
            self.health_details["elasticsearch"] = {
                "status": is_healthy,
                "timestamp": asyncio.get_event_loop().time(),
                "details": "Connection test completed"
            }
            
            return is_healthy
            
        except Exception as e:
            logger.error("Elasticsearch health check failed", error=str(e))
            self.health_details["elasticsearch"] = {
                "status": False,
                "timestamp": asyncio.get_event_loop().time(),
                "error": str(e),
                "details": "Health check failed"
            }
            return False

    async def check_dshield_api(self) -> bool:
        """Check DShield API connectivity and authentication.
        
        Returns:
            bool: True if DShield API is healthy, False otherwise
        """
        try:
            # This will be implemented when we have access to the dshield client
            # For now, we'll check if the environment variables are set
            from src.dshield_client import DShieldClient
            
            # Try to create a client and check connection
            client = DShieldClient()
            # Check if we can connect to DShield API
            is_healthy = await client.check_health()
            
            self.health_details["dshield_api"] = {
                "status": is_healthy,
                "timestamp": asyncio.get_event_loop().time(),
                "details": "Authentication test completed"
            }
            
            return is_healthy
            
        except Exception as e:
            logger.error("DShield API health check failed", error=str(e))
            self.health_details["dshield_api"] = {
                "status": False,
                "timestamp": asyncio.get_event_loop().time(),
                "error": str(e),
                "details": "Health check failed"
            }
            return False

    async def check_latex_availability(self) -> bool:
        """Check if LaTeX compilation is available.
        
        Returns:
            bool: True if LaTeX is available, False otherwise
        """
        try:
            # Check if pdflatex binary is available
            result = subprocess.run(
                ["which", "pdflatex"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                # Test basic compilation capability
                test_tex = r"""
                \documentclass{article}
                \begin{document}
                Test document
                \end{document}
                """
                
                # Create a temporary test file
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False) as f:
                    f.write(test_tex)
                    temp_file = f.name
                
                try:
                    # Try to compile
                    compile_result = subprocess.run(
                        ["pdflatex", "-interaction=nonstopmode", temp_file],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=os.path.dirname(temp_file)
                    )
                    
                    # Check if PDF was created
                    pdf_file = temp_file.replace('.tex', '.pdf')
                    pdf_exists = os.path.exists(pdf_file)
                    
                    # Cleanup
                    for ext in ['.tex', '.pdf', '.log', '.aux']:
                        try:
                            os.remove(temp_file.replace('.tex', ext))
                        except OSError:
                            pass
                    
                    is_healthy = pdf_exists and compile_result.returncode == 0
                    
                    self.health_details["latex"] = {
                        "status": is_healthy,
                        "timestamp": asyncio.get_event_loop().time(),
                        "details": f"Compilation test {'succeeded' if is_healthy else 'failed'}",
                        "pdflatex_path": result.stdout.strip(),
                        "test_compilation": is_healthy
                    }
                    
                    return is_healthy
                    
                except Exception as compile_error:
                    logger.error("LaTeX compilation test failed", error=str(compile_error))
                    self.health_details["latex"] = {
                        "status": False,
                        "timestamp": asyncio.get_event_loop().time(),
                        "error": str(compile_error),
                        "details": "Compilation test failed",
                        "pdflatex_path": result.stdout.strip()
                    }
                    return False
            else:
                self.health_details["latex"] = {
                    "status": False,
                    "timestamp": asyncio.get_event_loop().time(),
                    "error": "pdflatex not found in PATH",
                    "details": "Binary not available"
                }
                return False
                
        except Exception as e:
            logger.error("LaTeX availability check failed", error=str(e))
            self.health_details["latex"] = {
                "status": False,
                "timestamp": asyncio.get_event_loop().time(),
                "error": str(e),
                "details": "Health check failed"
            }
            return False

    async def check_threat_intel_sources(self) -> Dict[str, bool]:
        """Check availability of threat intelligence sources.
        
        Returns:
            Dict[str, bool]: Dictionary mapping source names to availability status
        """
        sources_status = {}
        
        try:
            # Check DShield API as primary source
            dshield_healthy = await self.check_dshield_api()
            sources_status["dshield"] = dshield_healthy
            
            # Check if we have any cached threat intelligence data
            try:
                from src.threat_intelligence_manager import ThreatIntelligenceManager
                tim = ThreatIntelligenceManager()
                has_cached_data = await tim.has_cached_data()
                sources_status["cached_data"] = has_cached_data
            except Exception:
                sources_status["cached_data"] = False
            
            # Check if we have offline threat intelligence sources
            try:
                from src.data_dictionary import DataDictionary
                dd = DataDictionary()
                has_offline_sources = dd.has_offline_threat_intel()
                sources_status["offline_sources"] = has_offline_sources
            except Exception:
                sources_status["offline_sources"] = False
            
            self.health_details["threat_intel_sources"] = {
                "status": any(sources_status.values()),
                "timestamp": asyncio.get_event_loop().time(),
                "details": "Individual source checks completed",
                "sources": sources_status
            }
            
            return sources_status
            
        except Exception as e:
            logger.error("Threat intelligence sources health check failed", error=str(e))
            self.health_details["threat_intel_sources"] = {
                "status": False,
                "timestamp": asyncio.get_event_loop().time(),
                "error": str(e),
                "details": "Health check failed"
            }
            return {"dshield": False, "cached_data": False, "offline_sources": False}

    async def check_database_health(self) -> bool:
        """Check database connectivity and health.
        
        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            # Check if we can access any database files or connections
            # For now, we'll assume it's healthy if no specific database is configured
            # This can be enhanced when we add specific database support
            
            self.health_details["database"] = {
                "status": True,
                "timestamp": asyncio.get_event_loop().time(),
                "details": "No specific database configured - assuming healthy"
            }
            
            return True
            
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            self.health_details["database"] = {
                "status": False,
                "timestamp": asyncio.get_event_loop().time(),
                "error": str(e),
                "details": "Health check failed"
            }
            return False

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status.
        
        Returns:
            Dict[str, Any]: Dictionary containing health status and details for all dependencies
        """
        logger.info("Starting comprehensive health checks")
        
        # Run all health checks concurrently with timeout protection
        async def run_with_timeout(coro, timeout_seconds: int = 30):
            """Run a coroutine with timeout protection."""
            try:
                return await asyncio.wait_for(coro, timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.warning(f"Health check timed out after {timeout_seconds} seconds")
                return False
            except Exception as e:
                logger.error(f"Health check failed with exception", error=str(e))
                return False
        
        tasks = [
            run_with_timeout(self.check_elasticsearch(), 30),
            run_with_timeout(self.check_dshield_api(), 30),
            run_with_timeout(self.check_latex_availability(), 10),
            run_with_timeout(self.check_threat_intel_sources(), 15),
            run_with_timeout(self.check_database_health(), 5)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        self.health_status["elasticsearch"] = results[0] if not isinstance(results[0], Exception) else False
        self.health_status["dshield_api"] = results[1] if not isinstance(results[1], Exception) else False
        self.health_status["latex"] = results[2] if not isinstance(results[2], Exception) else False
        
        threat_intel_result = results[3] if not isinstance(results[3], Exception) else {}
        self.health_status["threat_intel_sources"] = all(threat_intel_result.values()) if threat_intel_result else False
        
        self.health_status["database"] = results[4] if not isinstance(results[4], Exception) else False
        
        # Log health check results
        logger.info("Health checks completed", 
                   health_status=self.health_status,
                   healthy_count=sum(self.health_status.values()),
                   total_count=len(self.health_status))
        
        return {
            "status": self.health_status,
            "details": self.health_details,
            "summary": {
                "healthy_services": [k for k, v in self.health_status.items() if v],
                "unhealthy_services": [k for k, v in self.health_status.items() if not v],
                "overall_health": sum(self.health_status.values()) / len(self.health_status)
            }
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of current health status.
        
        Returns:
            Dict[str, Any]: Health status summary
        """
        return {
            "overall_health": sum(self.health_status.values()) / len(self.health_status),
            "healthy_services": [k for k, v in self.health_status.items() if v],
            "unhealthy_services": [k for k, v in self.health_status.items() if not v],
            "last_check": max([details.get("timestamp", 0) for details in self.health_details.values()], default=0)
        }

    def is_service_healthy(self, service_name: str) -> bool:
        """Check if a specific service is healthy.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            bool: True if service is healthy, False otherwise
        """
        return self.health_status.get(service_name, False)

    def get_service_details(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed health information for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Optional[Dict[str, Any]]: Service health details or None if not found
        """
        return self.health_details.get(service_name) 