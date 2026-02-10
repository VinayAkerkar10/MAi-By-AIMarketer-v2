# MAi Strategy Provider Abstraction
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
import logging

logger = logging.getLogger(__name__)

# ===== PROVIDER INTERFACE =====

class StrategyProvider(ABC):
    """Abstract base class for strategy generation providers"""
    
    @abstractmethod
    async def generate_strategy(
        self,
        business_profile: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate marketing strategy based on business profile.
        
        Args:
            business_profile: Business profile data
            additional_context: Optional additional context
            
        Returns:
            Dictionary containing strategy recommendations
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available/configured"""
        pass

# ===== OLLAMA PROVIDER (Local) =====

class OllamaStrategyProvider(StrategyProvider):
    """Ollama-based strategy provider (local deployment)"""
    
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.model = os.getenv("OLLAMA_STRATEGY_MODEL", "llama2")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    async def generate_strategy(
        self,
        business_profile: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate strategy using Ollama"""
        import httpx
        import json
        
        # Build prompt for strategy generation
        prompt = self._build_strategy_prompt(business_profile, additional_context)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "format": "json",
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "max_tokens": 2000
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                # Parse Ollama response (tolerate different response shapes)
                strategy_text = result.get("response", "")
                if not strategy_text and isinstance(result.get("message"), dict):
                    strategy_text = result["message"].get("content", "")
                if isinstance(strategy_text, dict):
                    strategy_text = json.dumps(strategy_text)
                if isinstance(strategy_text, str) and strategy_text.startswith('"') and strategy_text.endswith('"'):
                    try:
                        strategy_text = json.loads(strategy_text)
                    except json.JSONDecodeError:
                        pass
                return self._parse_strategy_response(strategy_text, business_profile)
                
        except httpx.RequestError as e:
            logger.error(f"Ollama request error: {e}")
            return self._get_minimal_fallback_strategy(business_profile)
        except Exception as e:
            logger.error(f"Ollama strategy generation error: {e}")
            return self._get_minimal_fallback_strategy(business_profile)
    
    def _build_strategy_prompt(
        self,
        business_profile: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> str:
        """Build prompt for strategy generation"""
        budget_range = business_profile.get('budget_range', 'Not specified')
        marketing_goals = ', '.join(business_profile.get('marketing_goals', []))
        
        prompt = f"""You are an expert B2B digital marketing strategy consultant with deep industry knowledge. Generate a comprehensive, data-driven marketing strategy based on the business profile provided.

BUSINESS PROFILE:
- Company Name: {business_profile.get('business_name', 'N/A')}
- Industry: {business_profile.get('industry', 'N/A')}
- Company Size: {business_profile.get('company_size', 'N/A')}
- Annual Revenue: {business_profile.get('revenue', 'Not specified')}
- Geography: {business_profile.get('geography', 'N/A')}
- Marketing Goals: {marketing_goals}
- Budget Range: {budget_range}
- Target Audience: {business_profile.get('target_audience', 'Not specified')}

"""
        if additional_context:
            prompt += f"ADDITIONAL CONTEXT: {additional_context}\n\n"
        
        prompt += """INSTRUCTIONS:
1. Analyze the business profile and generate a tailored marketing strategy
2. Create a campaign timeline based on the marketing goals and industry best practices
3. Allocate budget based on customer preferences, industry standards, and what will achieve their goals
4. Research and provide competitor budget benchmarks for similar companies in this industry
5. If the budget seems low for the goals, provide specific recommendations and warnings
6. All recommendations must be data-driven and industry-specific

REQUIREMENTS (MUST FOLLOW):
- Every field in the JSON must be present
- No nulls or empty strings
- All arrays must have at least 1 item
- All objects must have realistic default values
- If uncertain, invent reasonable industry-standard defaults

Generate the strategy in the following JSON format:
{
  "recommended_channels": ["Channel1", "Channel2", ...],
  "budget_allocation": {
    "paid_advertising": 0,
    "content_marketing": 0,
    "email_marketing": 0,
    "social_media": 0,
    "events_webinars": 0,
    "other": 0
  },
  "budget_analysis": {
    "customer_budget": "<budget range provided>",
    "recommended_budget_range": "<optimal budget range for goals>",
    "competitor_benchmark": {
      "industry_average": "<average budget for similar companies>",
      "top_performers": "<budget range for top performers>",
      "minimum_viable": "<minimum budget to achieve basic goals>"
    },
    "budget_assessment": "low|adequate|optimal",
    "budget_warnings": ["Warning 1 if budget is low", "Warning 2", ...],
    "budget_recommendations": ["Recommendation 1", "Recommendation 2", ...]
  },
  "target_segments": ["Segment1", "Segment2", ...],
  "campaign_timeline": {
    "phase_1": {
      "name": "Phase name based on strategy",
      "duration": "timeframe",
      "description": "detailed description",
      "key_activities": ["Activity 1", "Activity 2", ...]
    },
    "phase_2": {
      "name": "Phase name",
      "duration": "timeframe",
      "description": "detailed description",
      "key_activities": ["Activity 1", "Activity 2", ...]
    },
    "phase_3": {
      "name": "Phase name",
      "duration": "timeframe",
      "description": "detailed description",
      "key_activities": ["Activity 1", "Activity 2", ...]
    },
    "phase_4": {
      "name": "Phase name",
      "duration": "timeframe",
      "description": "detailed description",
      "key_activities": ["Activity 1", "Activity 2", ...]
    }
  },
  "content_strategy": ["Content Type 1", "Content Type 2", ...],
  "kpis": ["KPI 1", "KPI 2", ...],
  "insights": "Concrete, actionable strategic insights and recommendations",
  "risk_assessment": "Potential risks and mitigation strategies"
}

IMPORTANT:
- Timeline phases should be tailored to the marketing goals and industry
- Budget allocation must reflect customer preferences while optimizing for results
- Provide real competitor benchmark data based on industry research
- If budget is insufficient, clearly state what can and cannot be achieved
- All percentages in budget_allocation must sum to 100
- Timeline should be realistic and achievable based on the budget and goals

Provide only valid JSON, no additional text and no Markdown code fences. If unsure, invent plausible defaults."""
        
        return prompt
    
    def _parse_strategy_response(
        self,
        response_text: str,
        business_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Ollama response into strategy format"""
        import json
        import re
        from json import JSONDecoder
        
        def _extract_json(text: str) -> Optional[Dict[str, Any]]:
            text = text.strip()
            if not text:
                return None

            # Strip Markdown code fences if present
            fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
            if fence_match:
                try:
                    return json.loads(fence_match.group(1))
                except json.JSONDecodeError:
                    pass

            # Try to decode from first JSON object in the text
            decoder = JSONDecoder()
            for idx, ch in enumerate(text):
                if ch == "{":
                    try:
                        obj, _ = decoder.raw_decode(text[idx:])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        continue
            return None

        strategy_data = _extract_json(response_text)
        if strategy_data:
            # Validate and structure the response
            parsed_strategy = {
                "recommended_channels": strategy_data.get("recommended_channels", []),
                "budget_allocation": strategy_data.get("budget_allocation", {}),
                "budget_analysis": strategy_data.get("budget_analysis", {}),
                "target_segments": strategy_data.get("target_segments", []),
                "campaign_timeline": strategy_data.get("campaign_timeline", {}),
                "content_strategy": strategy_data.get("content_strategy", []),
                "kpis": strategy_data.get("kpis", []),
                "insights": strategy_data.get("insights", ""),
                "risk_assessment": strategy_data.get("risk_assessment", ""),
                "provider": "ollama",
                "model": self.model
            }
            
            # Validate budget allocation sums to 100
            budget_allocation = parsed_strategy.get("budget_allocation", {})
            total = sum(v for v in budget_allocation.values() if isinstance(v, (int, float)))
            if total != 100 and total > 0:
                logger.warning(f"Budget allocation sums to {total}%, normalizing to 100%")
                # Normalize to 100%
                for key in budget_allocation:
                    if isinstance(budget_allocation[key], (int, float)):
                        budget_allocation[key] = round((budget_allocation[key] / total) * 100, 2)
            
            return parsed_strategy
        else:
            logger.error("Failed to extract JSON from Ollama response")
            logger.debug(f"Response text: {response_text[:500]}")
        
        # If parsing fails, try to get AI to fix it or use minimal fallback
        logger.warning("Failed to parse AI response, using minimal fallback")
        return self._get_minimal_fallback_strategy(business_profile)
    
    def _get_minimal_fallback_strategy(self, business_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Minimal fallback strategy if AI parsing completely fails"""
        return {
            "recommended_channels": ["Email", "LinkedIn", "Content Marketing"],
            "budget_allocation": {
                "paid_advertising": 40,
                "content_marketing": 25,
                "email_marketing": 15,
                "social_media": 10,
                "events_webinars": 10
            },
            "budget_analysis": {
                "customer_budget": business_profile.get('budget_range', 'Not specified'),
                "budget_assessment": "unknown",
                "budget_warnings": ["AI model response could not be parsed. Please try again."],
                "budget_recommendations": ["Retry strategy generation for AI-powered recommendations"]
            },
            "target_segments": ["Decision Makers", "Influencers"],
            "campaign_timeline": {
                "phase_1": {
                    "name": "Initial Setup",
                    "duration": "Months 1-2",
                    "description": "Foundation and planning phase",
                    "key_activities": ["Setup", "Planning"]
                }
            },
            "content_strategy": ["Content Marketing"],
            "kpis": ["Lead Generation", "Conversion Rate"],
            "insights": "AI model response parsing failed. This is a fallback response. Please retry for AI-generated strategy.",
            "risk_assessment": "Unable to assess risks due to parsing failure",
            "provider": "ollama_fallback",
            "model": self.model
        }

# ===== OPENAI PROVIDER (API) =====

class OpenAIStrategyProvider(StrategyProvider):
    """OpenAI-based strategy provider (API)"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    def is_available(self) -> bool:
        """Check if OpenAI is configured"""
        return self.api_key is not None and len(self.api_key) > 0
    
    async def generate_strategy(
        self,
        business_profile: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate strategy using OpenAI API"""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            
            # Build prompt
            prompt = self._build_strategy_prompt(business_profile, additional_context)
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a marketing strategy AI expert. Generate comprehensive B2B digital marketing strategies. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            strategy_text = response.choices[0].message.content
            return self._parse_strategy_response(strategy_text, business_profile)
            
        except ImportError:
            raise Exception("OpenAI library not installed. Install with: pip install openai")
        except Exception as e:
            logger.error(f"OpenAI strategy generation error: {e}")
            raise Exception(f"OpenAI strategy generation failed: {str(e)}")
    
    def _build_strategy_prompt(
        self,
        business_profile: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> str:
        """Build prompt for OpenAI"""
        budget_range = business_profile.get('budget_range', 'Not specified')
        marketing_goals = ', '.join(business_profile.get('marketing_goals', []))
        
        prompt = f"""You are an expert B2B digital marketing strategy consultant with deep industry knowledge. Generate a comprehensive, data-driven marketing strategy based on the business profile provided.

BUSINESS PROFILE:
- Company Name: {business_profile.get('business_name', 'N/A')}
- Industry: {business_profile.get('industry', 'N/A')}
- Company Size: {business_profile.get('company_size', 'N/A')}
- Annual Revenue: {business_profile.get('revenue', 'Not specified')}
- Geography: {business_profile.get('geography', 'N/A')}
- Marketing Goals: {marketing_goals}
- Budget Range: {budget_range}
- Target Audience: {business_profile.get('target_audience', 'Not specified')}

"""
        if additional_context:
            prompt += f"ADDITIONAL CONTEXT: {additional_context}\n\n"
        
        prompt += """INSTRUCTIONS:
1. Analyze the business profile and generate a tailored marketing strategy
2. Create a campaign timeline based on the marketing goals and industry best practices
3. Allocate budget based on customer preferences, industry standards, and what will achieve their goals
4. Research and provide competitor budget benchmarks for similar companies in this industry
5. If the budget seems low for the goals, provide specific recommendations and warnings
6. All recommendations must be data-driven and industry-specific

Return a JSON object with this exact structure:
{
  "recommended_channels": ["Channel1", "Channel2", ...],
  "budget_allocation": {
    "paid_advertising": <percentage based on customer preference and industry>,
    "content_marketing": <percentage>,
    "email_marketing": <percentage>,
    "social_media": <percentage>,
    "events_webinars": <percentage>,
    "other": <percentage>
  },
  "budget_analysis": {
    "customer_budget": "<budget range provided>",
    "recommended_budget_range": "<optimal budget range for goals>",
    "competitor_benchmark": {
      "industry_average": "<average budget for similar companies>",
      "top_performers": "<budget range for top performers>",
      "minimum_viable": "<minimum budget to achieve basic goals>"
    },
    "budget_assessment": "<low/adequate/optimal>",
    "budget_warnings": ["Warning 1 if budget is low", "Warning 2", ...],
    "budget_recommendations": ["Recommendation 1", "Recommendation 2", ...]
  },
  "target_segments": ["Segment1", "Segment2", ...],
  "campaign_timeline": {
    "phase_1": {
      "name": "<Phase name based on strategy>",
      "duration": "<timeframe>",
      "description": "<detailed description>",
      "key_activities": ["Activity 1", "Activity 2", ...]
    },
    "phase_2": {
      "name": "<Phase name>",
      "duration": "<timeframe>",
      "description": "<detailed description>",
      "key_activities": ["Activity 1", "Activity 2", ...]
    },
    "phase_3": {
      "name": "<Phase name>",
      "duration": "<timeframe>",
      "description": "<detailed description>",
      "key_activities": ["Activity 1", "Activity 2", ...]
    },
    "phase_4": {
      "name": "<Phase name>",
      "duration": "<timeframe>",
      "description": "<detailed description>",
      "key_activities": ["Activity 1", "Activity 2", ...]
    }
  },
  "content_strategy": ["Content Type 1", "Content Type 2", ...],
  "kpis": ["KPI 1", "KPI 2", ...],
  "insights": "Comprehensive strategic insights and recommendations",
  "risk_assessment": "Potential risks and mitigation strategies"
}

IMPORTANT:
- Timeline phases should be tailored to the marketing goals and industry
- Budget allocation must reflect customer preferences while optimizing for results
- Provide real competitor benchmark data based on industry research
- If budget is insufficient, clearly state what can and cannot be achieved
- All percentages in budget_allocation must sum to 100
- Timeline should be realistic and achievable based on the budget and goals"""
        
        return prompt
    
    def _parse_strategy_response(
        self,
        response_text: str,
        business_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse OpenAI response"""
        import json
        
        try:
            strategy_data = json.loads(response_text)
            
            # Validate and structure the response
            parsed_strategy = {
                "recommended_channels": strategy_data.get("recommended_channels", []),
                "budget_allocation": strategy_data.get("budget_allocation", {}),
                "budget_analysis": strategy_data.get("budget_analysis", {}),
                "target_segments": strategy_data.get("target_segments", []),
                "campaign_timeline": strategy_data.get("campaign_timeline", {}),
                "content_strategy": strategy_data.get("content_strategy", []),
                "kpis": strategy_data.get("kpis", []),
                "insights": strategy_data.get("insights", ""),
                "risk_assessment": strategy_data.get("risk_assessment", ""),
                "provider": "openai",
                "model": self.model
            }
            
            # Validate budget allocation sums to 100
            budget_allocation = parsed_strategy.get("budget_allocation", {})
            total = sum(v for v in budget_allocation.values() if isinstance(v, (int, float)))
            if total != 100 and total > 0:
                logger.warning(f"Budget allocation sums to {total}%, normalizing to 100%")
                # Normalize to 100%
                for key in budget_allocation:
                    if isinstance(budget_allocation[key], (int, float)):
                        budget_allocation[key] = round((budget_allocation[key] / total) * 100, 2)
            
            return parsed_strategy
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise Exception(f"Invalid JSON response from OpenAI: {str(e)}")

# ===== PROVIDER FACTORY =====

class StrategyProviderFactory:
    """Factory for creating strategy providers"""
    
    @staticmethod
    def create_provider(provider_type: Optional[str] = None) -> StrategyProvider:
        """
        Create strategy provider based on configuration.
        
        Priority:
        1. STRATEGY_PROVIDER env var
        2. Check Ollama availability
        3. Check OpenAI availability
        4. Fallback to config-based
        """
        if provider_type is None:
            provider_type = os.getenv("STRATEGY_PROVIDER", "auto")
        
        provider_type = provider_type.lower()
        
        if provider_type == "ollama" or provider_type == "auto":
            ollama_provider = OllamaStrategyProvider()
            if ollama_provider.is_available():
                logger.info("Using Ollama strategy provider")
                return ollama_provider
        
        if provider_type == "openai" or (provider_type == "auto" and os.getenv("OPENAI_API_KEY")):
            openai_provider = OpenAIStrategyProvider()
            if openai_provider.is_available():
                logger.info("Using OpenAI strategy provider")
                return openai_provider
        
        # Fallback: try Ollama first, then OpenAI
        ollama_provider = OllamaStrategyProvider()
        if ollama_provider.is_available():
            logger.info("Using Ollama strategy provider (fallback)")
            return ollama_provider
        
        openai_provider = OpenAIStrategyProvider()
        if openai_provider.is_available():
            logger.info("Using OpenAI strategy provider (fallback)")
            return openai_provider
        
        # Last resort: return Ollama (will use fallback strategy)
        logger.warning("No AI provider available, using Ollama with fallback")
        return OllamaStrategyProvider()
    
    @staticmethod
    def get_available_providers() -> List[str]:
        """Get list of available providers"""
        available = []
        
        ollama = OllamaStrategyProvider()
        if ollama.is_available():
            available.append("ollama")
        
        openai = OpenAIStrategyProvider()
        if openai.is_available():
            available.append("openai")
        
        return available
