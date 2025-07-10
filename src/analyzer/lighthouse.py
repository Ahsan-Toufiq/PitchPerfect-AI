"""Lighthouse CLI analyzer for PitchPerfect AI."""

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..config import get_settings
from ..utils import get_logger, LoggerMixin, validate_url, record_analysis_request


@dataclass
class LighthouseResult:
    """Container for Lighthouse analysis results."""
    url: str
    scores: Dict[str, float]
    issues: Dict[str, List[str]]
    raw_data: Dict[str, Any]
    duration: float
    success: bool
    error_message: Optional[str] = None


class LighthouseAnalyzer(LoggerMixin):
    """Lighthouse CLI analyzer for website performance and SEO analysis."""
    
    def __init__(self):
        """Initialize Lighthouse analyzer."""
        self.settings = get_settings()
        self.lighthouse_cmd = self._find_lighthouse_executable()
        
        if not self.lighthouse_cmd:
            self.logger.warning("Lighthouse CLI not found. Install with: npm install -g lighthouse")
        else:
            self.logger.info(f"Lighthouse CLI found: {self.lighthouse_cmd}")
    
    def _find_lighthouse_executable(self) -> Optional[str]:
        """Find Lighthouse executable in system PATH.
        
        Returns:
            Path to lighthouse executable or None if not found
        """
        possible_commands = ['lighthouse', 'lighthouse.cmd']
        
        for cmd in possible_commands:
            try:
                result = subprocess.run(
                    [cmd, '--version'], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return None
    
    def is_available(self) -> bool:
        """Check if Lighthouse is available.
        
        Returns:
            True if Lighthouse CLI is available
        """
        return self.lighthouse_cmd is not None
    
    def analyze_website(self, url: str) -> LighthouseResult:
        """Analyze website using Lighthouse.
        
        Args:
            url: URL to analyze
            
        Returns:
            LighthouseResult with analysis data
        """
        # Validate URL
        url_validation = validate_url(url)
        if not url_validation.is_valid:
            return LighthouseResult(
                url=url,
                scores={},
                issues={},
                raw_data={},
                duration=0,
                success=False,
                error_message=f"Invalid URL: {url_validation.error_message}"
            )
        
        clean_url = url_validation.cleaned_value
        
        if not self.lighthouse_cmd:
            return LighthouseResult(
                url=clean_url,
                scores={},
                issues={},
                raw_data={},
                duration=0,
                success=False,
                error_message="Lighthouse CLI not available"
            )
        
        self.logger.info(f"Starting Lighthouse analysis for: {clean_url}")
        start_time = time.time()
        
        try:
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Build Lighthouse command
                cmd = self._build_lighthouse_command(clean_url, temp_path)
                
                # Run Lighthouse
                self.logger.debug(f"Running command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.settings.lighthouse_timeout
                )
                
                duration = time.time() - start_time
                
                if result.returncode != 0:
                    record_analysis_request(success=False)
                    error_msg = f"Lighthouse failed (exit code {result.returncode}): {result.stderr}"
                    self.logger.error(error_msg)
                    
                    return LighthouseResult(
                        url=clean_url,
                        scores={},
                        issues={},
                        raw_data={},
                        duration=duration,
                        success=False,
                        error_message=error_msg
                    )
                
                # Parse results
                lighthouse_data = self._parse_lighthouse_output(temp_path)
                
                if not lighthouse_data:
                    record_analysis_request(success=False)
                    return LighthouseResult(
                        url=clean_url,
                        scores={},
                        issues={},
                        raw_data={},
                        duration=duration,
                        success=False,
                        error_message="Failed to parse Lighthouse output"
                    )
                
                # Extract scores and issues
                scores = self._extract_scores(lighthouse_data)
                issues = self._extract_issues(lighthouse_data)
                
                record_analysis_request(success=True)
                
                self.logger.info(f"Lighthouse analysis completed in {duration:.1f}s")
                self.logger.debug(f"Scores: {scores}")
                
                return LighthouseResult(
                    url=clean_url,
                    scores=scores,
                    issues=issues,
                    raw_data=lighthouse_data,
                    duration=duration,
                    success=True
                )
                
            finally:
                # Clean up temporary file
                try:
                    Path(temp_path).unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup temp file: {e}")
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            record_analysis_request(success=False)
            error_msg = f"Lighthouse analysis timed out after {self.settings.lighthouse_timeout}s"
            self.logger.error(error_msg)
            
            return LighthouseResult(
                url=clean_url,
                scores={},
                issues={},
                raw_data={},
                duration=duration,
                success=False,
                error_message=error_msg
            )
        
        except Exception as e:
            duration = time.time() - start_time
            record_analysis_request(success=False)
            error_msg = f"Lighthouse analysis failed: {str(e)}"
            self.logger.error(error_msg)
            
            return LighthouseResult(
                url=clean_url,
                scores={},
                issues={},
                raw_data={},
                duration=duration,
                success=False,
                error_message=error_msg
            )
    
    def _build_lighthouse_command(self, url: str, output_path: str) -> List[str]:
        """Build Lighthouse command with appropriate flags.
        
        Args:
            url: URL to analyze
            output_path: Path for JSON output
            
        Returns:
            List of command arguments
        """
        cmd = [
            self.lighthouse_cmd,
            url,
            '--output=json',
            f'--output-path={output_path}',
            '--quiet',
            '--no-enable-error-reporting'
        ]
        
        # Add Chrome flags from settings
        chrome_flags = self.settings.lighthouse_chrome_flags
        if chrome_flags:
            cmd.append(f'--chrome-flags={chrome_flags}')
        
        # Add timeout
        if self.settings.lighthouse_timeout:
            cmd.append(f'--max-wait-for-load={self.settings.lighthouse_timeout * 1000}')
        
        # Add additional flags for better performance in automation
        cmd.extend([
            '--disable-device-emulation',
            '--disable-storage-reset',
            '--throttling-method=simulate'
        ])
        
        return cmd
    
    def _parse_lighthouse_output(self, output_path: str) -> Optional[Dict[str, Any]]:
        """Parse Lighthouse JSON output.
        
        Args:
            output_path: Path to Lighthouse JSON output
            
        Returns:
            Parsed JSON data or None if failed
        """
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                self.logger.error("Lighthouse output is not a valid JSON object")
                return None
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Lighthouse JSON: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to read Lighthouse output: {e}")
            return None
    
    def _extract_scores(self, lighthouse_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract category scores from Lighthouse data.
        
        Args:
            lighthouse_data: Parsed Lighthouse JSON
            
        Returns:
            Dictionary with category scores (0-100)
        """
        scores = {}
        
        try:
            categories = lighthouse_data.get('categories', {})
            
            # Extract main category scores
            category_mapping = {
                'performance': 'performance_score',
                'accessibility': 'accessibility_score',
                'best-practices': 'best_practices_score',
                'seo': 'seo_score'
            }
            
            for lighthouse_key, our_key in category_mapping.items():
                category_data = categories.get(lighthouse_key, {})
                score = category_data.get('score')
                
                if score is not None:
                    # Convert from 0-1 to 0-100
                    scores[our_key] = round(score * 100, 1)
            
            # Calculate overall Lighthouse score (average of all categories)
            if scores:
                overall_score = sum(scores.values()) / len(scores)
                scores['lighthouse_score'] = round(overall_score, 1)
            
        except Exception as e:
            self.logger.warning(f"Failed to extract scores: {e}")
        
        return scores
    
    def _extract_issues(self, lighthouse_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract issues and recommendations from Lighthouse data.
        
        Args:
            lighthouse_data: Parsed Lighthouse JSON
            
        Returns:
            Dictionary with categorized issues
        """
        issues = {
            'performance_issues': [],
            'seo_issues': [],
            'accessibility_issues': [],
            'best_practices_issues': []
        }
        
        try:
            audits = lighthouse_data.get('audits', {})
            
            # Define audit categories
            audit_categories = {
                'performance_issues': [
                    'first-contentful-paint',
                    'largest-contentful-paint',
                    'cumulative-layout-shift',
                    'total-blocking-time',
                    'speed-index',
                    'render-blocking-resources',
                    'unused-css-rules',
                    'unused-javascript',
                    'uses-optimized-images',
                    'modern-image-formats',
                    'efficient-animated-content'
                ],
                'seo_issues': [
                    'meta-description',
                    'document-title',
                    'html-has-lang',
                    'canonical',
                    'robots-txt',
                    'image-alt',
                    'link-text',
                    'is-crawlable',
                    'structured-data'
                ],
                'accessibility_issues': [
                    'color-contrast',
                    'image-alt',
                    'button-name',
                    'link-name',
                    'html-has-lang',
                    'heading-order',
                    'label',
                    'landmark-one-main'
                ],
                'best_practices_issues': [
                    'uses-https',
                    'is-on-https',
                    'geolocation-on-start',
                    'notification-on-start',
                    'no-vulnerable-libraries',
                    'csp-xss',
                    'password-inputs-can-be-pasted-into'
                ]
            }
            
            # Extract issues for each category
            for category, audit_ids in audit_categories.items():
                for audit_id in audit_ids:
                    audit = audits.get(audit_id, {})
                    
                    # Check if audit failed or has warnings
                    score = audit.get('score')
                    if score is not None and score < 1.0:  # Score < 1.0 indicates issues
                        title = audit.get('title', audit_id)
                        description = audit.get('description', '')
                        
                        # Create issue description
                        issue_text = title
                        if description and description != title:
                            issue_text += f": {description}"
                        
                        issues[category].append(issue_text)
            
            # Limit issues per category to avoid overwhelming output
            for category in issues:
                if len(issues[category]) > 10:
                    issues[category] = issues[category][:10]
                    issues[category].append("... and more issues")
        
        except Exception as e:
            self.logger.warning(f"Failed to extract issues: {e}")
        
        return issues
    
    def get_lighthouse_version(self) -> Optional[str]:
        """Get Lighthouse version.
        
        Returns:
            Lighthouse version string or None
        """
        if not self.lighthouse_cmd:
            return None
        
        try:
            result = subprocess.run(
                [self.lighthouse_cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            
        except Exception as e:
            self.logger.warning(f"Failed to get Lighthouse version: {e}")
        
        return None
    
    def test_lighthouse(self) -> bool:
        """Test if Lighthouse is working properly.
        
        Returns:
            True if Lighthouse is working
        """
        if not self.lighthouse_cmd:
            return False
        
        try:
            # Test with a simple, fast website
            result = self.analyze_website("https://example.com")
            
            if result.success and result.scores:
                self.logger.info("Lighthouse test successful")
                return True
            else:
                self.logger.warning(f"Lighthouse test failed: {result.error_message}")
                return False
                
        except Exception as e:
            self.logger.error(f"Lighthouse test failed: {e}")
            return False
    
    def get_analysis_summary(self, result: LighthouseResult) -> str:
        """Get human-readable summary of analysis results.
        
        Args:
            result: Lighthouse analysis result
            
        Returns:
            Formatted summary string
        """
        if not result.success:
            return f"Analysis failed: {result.error_message}"
        
        summary_lines = []
        summary_lines.append(f"Website: {result.url}")
        summary_lines.append(f"Analysis Duration: {result.duration:.1f}s")
        summary_lines.append("")
        
        # Scores
        summary_lines.append("Scores:")
        for key, value in result.scores.items():
            display_name = key.replace('_', ' ').title()
            summary_lines.append(f"  {display_name}: {value}/100")
        
        # Issues summary
        summary_lines.append("")
        summary_lines.append("Issues Found:")
        
        for category, issues in result.issues.items():
            if issues:
                display_category = category.replace('_', ' ').title()
                summary_lines.append(f"  {display_category}: {len(issues)} issues")
        
        return "\n".join(summary_lines) 