"""LLM analyzer for PitchPerfect AI using Ollama."""

import json
import requests
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..config import get_settings
from ..utils import get_logger, LoggerMixin, get_rate_limiter


@dataclass 
class LLMAnalysisResult:
    """Container for LLM analysis results."""
    url: str
    suggestions: str
    issues_summary: str
    business_impact: str
    priority_actions: List[str]
    estimated_effort: str
    success: bool
    duration: float
    error_message: Optional[str] = None


class LLMAnalyzer(LoggerMixin):
    """LLM-powered website analyzer using Ollama."""
    
    def __init__(self):
        """Initialize LLM analyzer."""
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url
        self.model = self.settings.ollama_model
        self.timeout = self.settings.ollama_timeout
        self.rate_limiter = get_rate_limiter("llm")
        
        self.logger.info(f"LLM analyzer initialized with model: {self.model}")
    
    def is_available(self) -> bool:
        """Check if Ollama service is available.
        
        Returns:
            True if Ollama is reachable
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def test_connection(self) -> bool:
        """Test connection to Ollama and model availability.
        
        Returns:
            True if connection and model work
        """
        try:
            # Test basic connection
            if not self.is_available():
                self.logger.error("Ollama service not available")
                return False
            
            # Test model availability
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                
                if self.model in models or any(self.model in model for model in models):
                    self.logger.info("LLM connection test successful")
                    return True
                else:
                    self.logger.error(f"Model {self.model} not found. Available: {models}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"LLM connection test failed: {e}")
            return False
    
    def analyze_website_content(
        self,
        url: str,
        lighthouse_scores: Dict[str, float],
        lighthouse_issues: Dict[str, List[str]],
        business_category: Optional[str] = None
    ) -> LLMAnalysisResult:
        """Analyze website using LLM based on Lighthouse results.
        
        Args:
            url: Website URL
            lighthouse_scores: Lighthouse performance scores
            lighthouse_issues: Categorized issues from Lighthouse
            business_category: Business category for context
            
        Returns:
            LLM analysis result
        """
        self.logger.info(f"Starting LLM analysis for: {url}")
        start_time = time.time()
        
        if not self.is_available():
            return LLMAnalysisResult(
                url=url,
                suggestions="",
                issues_summary="",
                business_impact="",
                priority_actions=[],
                estimated_effort="",
                success=False,
                duration=0,
                error_message="Ollama service not available"
            )
        
        try:
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            # Create analysis prompt
            prompt = self._build_analysis_prompt(
                url, lighthouse_scores, lighthouse_issues, business_category
            )
            
            # Call Ollama API
            response = self._call_ollama_api(prompt)
            
            if not response:
                self.rate_limiter.record_request(success=False)
                return LLMAnalysisResult(
                    url=url,
                    suggestions="",
                    issues_summary="",
                    business_impact="",
                    priority_actions=[],
                    estimated_effort="",
                    success=False,
                    duration=time.time() - start_time,
                    error_message="Failed to get response from LLM"
                )
            
            # Parse response
            analysis = self._parse_llm_response(response)
            duration = time.time() - start_time
            
            self.rate_limiter.record_request(success=True)
            self.logger.info(f"LLM analysis completed in {duration:.1f}s")
            
            return LLMAnalysisResult(
                url=url,
                suggestions=analysis.get('suggestions', ''),
                issues_summary=analysis.get('issues_summary', ''),
                business_impact=analysis.get('business_impact', ''),
                priority_actions=analysis.get('priority_actions', []),
                estimated_effort=analysis.get('estimated_effort', ''),
                success=True,
                duration=duration
            )
            
        except Exception as e:
            self.rate_limiter.record_request(success=False)
            duration = time.time() - start_time
            error_msg = f"LLM analysis failed: {str(e)}"
            self.logger.error(error_msg)
            
            return LLMAnalysisResult(
                url=url,
                suggestions="",
                issues_summary="",
                business_impact="",
                priority_actions=[],
                estimated_effort="",
                success=False,
                duration=duration,
                error_message=error_msg
            )
    
    def _build_analysis_prompt(
        self,
        url: str,
        scores: Dict[str, float],
        issues: Dict[str, List[str]],
        business_category: Optional[str]
    ) -> str:
        """Build analysis prompt for the LLM.
        
        Args:
            url: Website URL
            scores: Lighthouse scores
            issues: Lighthouse issues
            business_category: Business category
            
        Returns:
            Formatted prompt
        """
        category_context = f" (a {business_category} business)" if business_category else ""
        
        prompt = f"""You are a website optimization expert analyzing {url}{category_context}.

LIGHTHOUSE PERFORMANCE SCORES:
{self._format_scores(scores)}

IDENTIFIED ISSUES:
{self._format_issues(issues)}

Please provide a comprehensive analysis in JSON format with these exact keys:

{{
  "issues_summary": "Brief overview of main problems found",
  "business_impact": "How these issues affect the business (customer experience, conversions, credibility)",
  "suggestions": "Detailed, actionable recommendations to fix the issues",
  "priority_actions": ["List", "of", "top", "3-5", "priority", "actions"],
  "estimated_effort": "Overall effort estimate (Low/Medium/High) with brief justification"
}}

Focus on:
1. Business impact - how issues affect customers and revenue
2. Actionable solutions - specific steps to implement
3. Priority order - what to fix first for maximum impact
4. Realistic effort estimates

Keep suggestions practical and business-focused. Avoid overly technical jargon."""
        
        return prompt
    
    def _format_scores(self, scores: Dict[str, float]) -> str:
        """Format scores for the prompt.
        
        Args:
            scores: Score dictionary
            
        Returns:
            Formatted score string
        """
        if not scores:
            return "No scores available"
        
        formatted = []
        for key, value in scores.items():
            display_name = key.replace('_', ' ').title()
            formatted.append(f"- {display_name}: {value}/100")
        
        return "\n".join(formatted)
    
    def _format_issues(self, issues: Dict[str, List[str]]) -> str:
        """Format issues for the prompt.
        
        Args:
            issues: Issues dictionary
            
        Returns:
            Formatted issues string
        """
        if not any(issues.values()):
            return "No specific issues identified"
        
        formatted = []
        for category, issue_list in issues.items():
            if issue_list:
                display_category = category.replace('_', ' ').title()
                formatted.append(f"\n{display_category}:")
                for issue in issue_list:
                    formatted.append(f"  - {issue}")
        
        return "\n".join(formatted)
    
    def _call_ollama_api(self, prompt: str) -> Optional[str]:
        """Call Ollama API with the analysis prompt.
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            LLM response or None if failed
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more consistent analysis
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                self.logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
        except requests.Timeout:
            self.logger.error(f"Ollama API timeout after {self.timeout}s")
            return None
        except Exception as e:
            self.logger.error(f"Ollama API call failed: {e}")
            return None
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed analysis data
        """
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Find JSON block in response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
                
                # Validate required keys
                required_keys = ['issues_summary', 'business_impact', 'suggestions', 'priority_actions', 'estimated_effort']
                for key in required_keys:
                    if key not in parsed:
                        parsed[key] = ""
                
                # Ensure priority_actions is a list
                if not isinstance(parsed.get('priority_actions'), list):
                    parsed['priority_actions'] = []
                
                return parsed
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON from LLM response: {e}")
        except Exception as e:
            self.logger.warning(f"Error parsing LLM response: {e}")
        
        # Fallback: try to extract information manually
        return self._fallback_parse(response)
    
    def _fallback_parse(self, response: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Basic parsed data
        """
        # Basic fallback - just use the response as suggestions
        return {
            'issues_summary': 'Analysis completed (parsing error)',
            'business_impact': 'See detailed suggestions for impact assessment',
            'suggestions': response[:1000] + '...' if len(response) > 1000 else response,
            'priority_actions': ['Review detailed suggestions', 'Prioritize based on business needs'],
            'estimated_effort': 'Medium (requires detailed review)'
        }
    
    def generate_email_pitch(
        self,
        business_name: str,
        analysis_result: LLMAnalysisResult,
        business_category: Optional[str] = None
    ) -> str:
        """Generate email pitch based on analysis results.
        
        Args:
            business_name: Name of the business
            analysis_result: LLM analysis results
            business_category: Business category
            
        Returns:
            Generated email content
        """
        if not self.is_available() or not analysis_result.success:
            return self._fallback_email_template(business_name, business_category)
        
        try:
            self.rate_limiter.wait_if_needed()
            
            category_context = f" ({business_category})" if business_category else ""
            
            prompt = f"""Write a professional cold email to {business_name}{category_context} about their website improvements.

ANALYSIS RESULTS:
- Issues Summary: {analysis_result.issues_summary}
- Business Impact: {analysis_result.business_impact}
- Priority Actions: {', '.join(analysis_result.priority_actions)}

EMAIL REQUIREMENTS:
- Professional and friendly tone
- Max 150 words
- Focus on business benefits, not technical details
- Clear value proposition
- Call to action
- No pushy sales language
- Include unsubscribe option

Write ONLY the email body (no subject line)."""
            
            response = self._call_ollama_api(prompt)
            
            if response:
                self.rate_limiter.record_request(success=True)
                # Clean up the response
                email_content = response.strip()
                
                # Add unsubscribe if not present
                if 'unsubscribe' not in email_content.lower():
                    email_content += "\n\nReply STOP to unsubscribe from future emails."
                
                return email_content
            
        except Exception as e:
            self.logger.warning(f"Failed to generate email pitch: {e}")
        
        self.rate_limiter.record_request(success=False)
        return self._fallback_email_template(business_name, business_category)
    
    def _fallback_email_template(self, business_name: str, business_category: Optional[str] = None) -> str:
        """Fallback email template when LLM is unavailable.
        
        Args:
            business_name: Business name
            business_category: Business category
            
        Returns:
            Template email content
        """
        category_text = f" {business_category}" if business_category else ""
        
        return f"""Hi {business_name},

I recently analyzed your website and noticed some opportunities to improve your online presence that could help attract more customers.

Our analysis found areas where your site could perform better in search engines and provide a smoother experience for visitors. These improvements typically lead to increased traffic and better customer engagement.

Would you be interested in a brief conversation about how these enhancements could benefit your{category_text} business?

Best regards,
PitchPerfect AI

Reply STOP to unsubscribe from future emails."""
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama.
        
        Returns:
            List of model names
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            
        except Exception as e:
            self.logger.warning(f"Failed to get available models: {e}")
        
        return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry.
        
        Args:
            model_name: Name of model to pull
            
        Returns:
            True if successful
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=300  # Model pulling can take a while
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
            return False 