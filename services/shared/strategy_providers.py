# MAi Strategy Provider Abstraction
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
import os
import random
import logging

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Raised when provider configuration or upstream call fails."""
    pass

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
        self.model = os.getenv("OLLAMA_STRATEGY_MODEL", os.getenv("MODEL_NAME", "llama2"))
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", os.getenv("REQUEST_TIMEOUT", "120")))
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    @staticmethod
    def _snippet(value: Any, limit: int = 200) -> str:
        text = str(value or "").replace("\n", " ").strip()
        return text[:limit]

    @staticmethod
    def _extract_strategy_text(result: Dict[str, Any]) -> Any:
        strategy_text = result.get("response", "")
        if not strategy_text and isinstance(result.get("message"), dict):
            strategy_text = result["message"].get("content", "")
        return strategy_text
    
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
        logger.debug(
            "[OLLAMA_DEBUG] Preparing request: base_url=%s model=%s timeout=%s prompt_len=%d",
            self.base_url,
            self.model,
            self.timeout,
            len(prompt)
        )
        
        try:
            timeout = httpx.Timeout(
                connect=30.0,
                read=300.0,
                write=300.0,
                pool=30.0
            )
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(
                    "[OLLAMA_DEBUG] Calling Ollama: url=%s timeout=%s",
                    f"{self.base_url}/api/generate",
                    timeout
                )
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "format": "json",
                        "stream": False,
                        "options": {
                            "num_predict": 1200,
                            "temperature": 0.7,
                            "top_p": 0.9
                        }
                    }
                )
                logger.debug(
                    "[OLLAMA_DEBUG] Response meta: status=%s headers=%s text_len=%d",
                    response.status_code,
                    dict(response.headers),
                    len(response.text or "")
                )
                if response.text:
                    logger.debug(
                        "[OLLAMA_DEBUG] Response text head(500)=%s",
                        response.text[:500]
                    )
                    logger.debug(
                        "[OLLAMA_DEBUG] Response text tail(500)=%s",
                        response.text[-500:]
                    )
                response.raise_for_status()
                result = response.json()
                logger.debug(
                    "[OLLAMA_DEBUG] Response JSON (truncated): %s",
                    str(result)[:500]
                )
                
                # Parse Ollama response (tolerate different response shapes)
                strategy_text = self._extract_strategy_text(result)
                if isinstance(strategy_text, dict):
                    strategy_text = json.dumps(strategy_text)
                if isinstance(strategy_text, str) and strategy_text.startswith('"') and strategy_text.endswith('"'):
                    try:
                        strategy_text = json.loads(strategy_text)
                    except json.JSONDecodeError:
                        pass
                logger.debug(
                    "[OLLAMA_DEBUG] Extracted response length: %d",
                    len(strategy_text or "")
                )
                logger.debug(
                    "[OLLAMA_DEBUG] Extracted strategy_text head(500)=%s",
                    (strategy_text or "")[:500]
                )
                logger.debug(
                    "JSON_PARSE_STAGE=initial snippet=%s",
                    self._snippet(strategy_text)
                )
                parsed_strategy = self._parse_strategy_response(
                    strategy_text,
                    business_profile,
                    allow_fallback=False
                )
                if parsed_strategy:
                    return parsed_strategy

                retry_prompt = (
                    f"{prompt}\n\n"
                    "The previous response was not valid JSON.\n"
                    "Return ONLY valid JSON. No text outside JSON."
                )
                logger.debug(
                    "[OLLAMA_DEBUG] Retrying Ollama parse recovery: url=%s",
                    f"{self.base_url}/api/generate"
                )
                retry_response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": retry_prompt,
                        "format": "json",
                        "stream": False,
                        "options": {
                            "num_predict": 1200,
                            "temperature": 0.7,
                            "top_p": 0.9
                        }
                    }
                )
                retry_response.raise_for_status()
                retry_result = retry_response.json()
                retry_text = self._extract_strategy_text(retry_result)
                if isinstance(retry_text, dict):
                    retry_text = json.dumps(retry_text)
                logger.debug(
                    "JSON_PARSE_STAGE=retry snippet=%s",
                    self._snippet(retry_text)
                )
                retry_parsed = self._parse_strategy_response(
                    retry_text,
                    business_profile,
                    allow_fallback=False
                )
                if retry_parsed:
                    return retry_parsed

                logger.warning(
                    "JSON_PARSE_STAGE=fallback snippet=%s",
                    self._snippet(retry_text or strategy_text)
                )
                return self._get_minimal_fallback_strategy(business_profile, reason="parse_failure")
                
        except httpx.RequestError as e:
            logger.error(f"Ollama request error: {e}")
            logger.warning("Fallback trigger condition: request_error")
            return self._get_minimal_fallback_strategy(business_profile, reason="request_error")
        except Exception as e:
            logger.error(f"Ollama strategy generation error: {e}")
            logger.warning("Fallback trigger condition: generation_exception")
            return self._get_minimal_fallback_strategy(business_profile, reason="generation_exception")


class OllamaCloudStrategyProvider(OllamaStrategyProvider):
    """Official Ollama cloud API provider."""

    TRANSIENT_STATUS_CODES = {429, 502, 503, 504}

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/api").rstrip("/")
        self.api_key = os.getenv("OLLAMA_API_KEY", "")
        self.model = os.getenv("MODEL_NAME", os.getenv("OLLAMA_STRATEGY_MODEL", "gpt-oss:120b"))
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", os.getenv("OLLAMA_TIMEOUT", "60")))
        self.max_retries = 3

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _generate_endpoint(self) -> str:
        return f"{self.base_url}/generate" if self.base_url.endswith("/api") else f"{self.base_url}/api/generate"

    async def _request_with_retry(self, prompt: str) -> Dict[str, Any]:
        import httpx

        if not self.api_key:
            raise LLMProviderError("OLLAMA_API_KEY is required for ollama_cloud provider")
        if self.timeout <= 0:
            raise LLMProviderError("REQUEST_TIMEOUT must be greater than 0")

        url = self._generate_endpoint()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "num_predict": 1200,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(float(self.timeout))) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    logger.warning(
                        "Ollama cloud request attempt failed",
                        extra={"provider": "ollama_cloud", "attempt": attempt, "error_type": type(exc).__name__}
                    )
                    if attempt < self.max_retries:
                        backoff = min(6.0, 0.5 * (2 ** (attempt - 1)) + random.uniform(0.0, 0.25))
                        await asyncio.sleep(backoff)
                        continue
                    raise LLMProviderError("Ollama cloud request failed") from exc

                if response.status_code in self.TRANSIENT_STATUS_CODES and attempt < self.max_retries:
                    backoff = min(6.0, 0.5 * (2 ** (attempt - 1)) + random.uniform(0.0, 0.25))
                    await asyncio.sleep(backoff)
                    continue

                if response.status_code >= 400:
                    error_message = None
                    try:
                        error_body = response.json()
                        error_message = error_body.get("error") if isinstance(error_body, dict) else None
                    except Exception:
                        error_message = response.text
                    raise LLMProviderError(
                        f"Ollama cloud error ({response.status_code}): {(error_message or 'unknown error')[:300]}"
                    )

                try:
                    return response.json()
                except Exception as exc:
                    raise LLMProviderError("Invalid JSON response from Ollama cloud") from exc

        raise LLMProviderError("Ollama cloud request failed after retries")

    async def generate_strategy(
        self,
        business_profile: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        import json

        prompt = self._build_strategy_prompt(business_profile, additional_context)
        logger.info(
            "Using Ollama cloud provider for strategy generation",
            extra={"provider": "ollama_cloud", "model": self.model, "base_url": self.base_url}
        )
        try:
            result = await self._request_with_retry(prompt)
            strategy_text = self._extract_strategy_text(result)
            if isinstance(strategy_text, dict):
                strategy_text = json.dumps(strategy_text)
            logger.debug(
                "JSON_PARSE_STAGE=initial snippet=%s",
                self._snippet(strategy_text)
            )
            parsed = self._parse_strategy_response(
                strategy_text,
                business_profile,
                allow_fallback=False
            )
            if parsed:
                parsed["provider"] = "ollama_cloud"
                parsed["model"] = self.model
                return parsed

            retry_prompt = (
                f"{prompt}\n\n"
                "The previous response was not valid JSON.\n"
                "Return ONLY valid JSON. No text outside JSON."
            )
            retry_result = await self._request_with_retry(retry_prompt)
            retry_text = self._extract_strategy_text(retry_result)
            if isinstance(retry_text, dict):
                retry_text = json.dumps(retry_text)
            logger.debug(
                "JSON_PARSE_STAGE=retry snippet=%s",
                self._snippet(retry_text)
            )
            retry_parsed = self._parse_strategy_response(
                retry_text,
                business_profile,
                allow_fallback=False
            )
            if retry_parsed:
                retry_parsed["provider"] = "ollama_cloud"
                retry_parsed["model"] = self.model
                return retry_parsed

            logger.warning(
                "JSON_PARSE_STAGE=fallback snippet=%s",
                self._snippet(retry_text or strategy_text)
            )
            return self._get_minimal_fallback_strategy(business_profile, reason="cloud_parse_failure")
        except LLMProviderError as exc:
            logger.error("Ollama cloud strategy generation failed: %s", str(exc))
            return self._get_minimal_fallback_strategy(business_profile, reason="cloud_request_error")
    
    def _build_strategy_prompt(
        self,
        business_profile: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> str:
        """Build prompt for strategy generation"""
        budget_range = business_profile.get('budget_range', 'Not specified')
        marketing_goals = ', '.join(business_profile.get('marketing_goals', []))

        system_prompt = """You are a marketing strategy generator.

You MUST respond ONLY with valid JSON.
Do NOT include explanations.
Do NOT include markdown.
Do NOT include text outside JSON.

Return JSON with the following schema:

{
  "recommended_channels": [string],
  "target_audience_segments": [string],
  "campaign_timeline": {
    "phase_1": {
      "name": string,
      "duration": string,
      "description": string,
      "actions": [string]
    },
    "phase_2": {
      "name": string,
      "duration": string,
      "description": string,
      "actions": [string]
    },
    "phase_3": {
      "name": string,
      "duration": string,
      "description": string,
      "actions": [string]
    }
  }
}

"""

        prompt = system_prompt + f"""You are an expert B2B digital marketing strategy consultant with deep industry knowledge. Generate a comprehensive, data-driven marketing strategy based on the business profile provided.

BUSINESS PROFILE:
- Company Name: {business_profile.get('business_name', 'N/A')}
- Industry: {business_profile.get('industry', 'N/A')}
- Company Size: {business_profile.get('company_size', 'N/A')}
- Annual Revenue: {business_profile.get('revenue', 'Not specified')}
- Geography: {business_profile.get('geography', 'N/A')}
- Marketing Goals: {marketing_goals}
- Budget Range: {budget_range}
- Target Audience: {business_profile.get('target_audience', 'Not specified')}
- Website URL: {business_profile.get('website_link', 'Not specified')}

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
7. Use the website URL context to tailor messaging, channel strategy, and content angles

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
        business_profile: Dict[str, Any],
        allow_fallback: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Parse Ollama response into strategy format"""
        import json
        import re
        from json import JSONDecoder

        def _snippet(value: str) -> str:
            value = (value or "").replace("\n", " ").strip()
            return value[:200]

        def _cleanup_and_load(raw_text: str) -> Optional[Dict[str, Any]]:
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                logger.debug("[JSON_PARSE_DEBUG] stage=cleanup_extract status=no_object snippet=%s", _snippet(raw_text))
                return None
            candidate = raw_text[start:end + 1]
            logger.debug("[JSON_PARSE_DEBUG] stage=cleanup_extract status=attempt snippet=%s", _snippet(candidate))
            try:
                obj = json.loads(candidate)
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                logger.debug("[JSON_PARSE_DEBUG] stage=cleanup_extract status=decode_failed snippet=%s", _snippet(candidate))
                return None

        def _extract_json(text: str) -> Optional[Dict[str, Any]]:
            required_keys = {"recommended_channels"}
            text = text.strip()
            if not text:
                logger.debug("[JSON_PARSE_DEBUG] stage=initial_load status=empty")
                return None

            # Parse attempt 1: direct JSON parse
            logger.debug("[JSON_PARSE_DEBUG] stage=initial_load status=attempt snippet=%s", _snippet(text))
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and required_keys.issubset(parsed.keys()):
                    return parsed
                if isinstance(parsed, dict):
                    logger.debug(
                        "[JSON_PARSE_DEBUG] stage=initial_load status=missing_keys missing=%s",
                        list(required_keys.difference(parsed.keys()))
                    )
            except json.JSONDecodeError:
                logger.debug("[JSON_PARSE_DEBUG] stage=initial_load status=decode_failed snippet=%s", _snippet(text))

            # Parse attempt 2: fenced JSON block
            fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
            if fence_match:
                fenced = fence_match.group(1)
                logger.debug("[JSON_PARSE_DEBUG] stage=fenced_extract status=attempt snippet=%s", _snippet(fenced))
                try:
                    obj = json.loads(fenced)
                    if isinstance(obj, dict) and required_keys.issubset(obj.keys()):
                        return obj
                except json.JSONDecodeError:
                    logger.debug("[JSON_PARSE_DEBUG] stage=fenced_extract status=decode_failed snippet=%s", _snippet(fenced))

            # Parse attempt 3: cleanup parse from first '{' to last '}'
            cleaned = _cleanup_and_load(text)
            if isinstance(cleaned, dict) and required_keys.issubset(cleaned.keys()):
                return cleaned

            # Last tolerant pass using decoder scan
            decoder = JSONDecoder()
            for idx, ch in enumerate(text):
                if ch != "{":
                    continue
                try:
                    obj, _ = decoder.raw_decode(text[idx:])
                    if isinstance(obj, dict) and required_keys.issubset(obj.keys()):
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
        logger.error("Failed to extract JSON from Ollama response")
        if allow_fallback:
            logger.warning("Fallback trigger condition: parse_failure")
            return self._get_minimal_fallback_strategy(business_profile, reason="parse_failure")
        return None
    
    def _get_minimal_fallback_strategy(
        self,
        business_profile: Dict[str, Any],
        reason: str = "unknown"
    ) -> Dict[str, Any]:
        """Minimal fallback strategy if AI parsing completely fails"""
        logger.warning(
            "Returning minimal fallback strategy: provider=ollama_fallback model=%s reason=%s",
            self.model,
            reason
        )
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
- Website URL: {business_profile.get('website_link', 'Not specified')}

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
7. Use the website URL context to tailor messaging, channel strategy, and content angles

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
            provider_type = os.getenv("LLM_PROVIDER", os.getenv("STRATEGY_PROVIDER", "auto"))
        
        provider_type = provider_type.lower()

        if provider_type == "ollama_cloud":
            cloud_provider = OllamaCloudStrategyProvider()
            if cloud_provider.is_available():
                logger.info("Using Ollama cloud strategy provider")
                return cloud_provider
            raise LLMProviderError("Ollama cloud provider selected but API key is missing")
        
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
    def validate_environment() -> str:
        provider_type = os.getenv("LLM_PROVIDER", os.getenv("STRATEGY_PROVIDER", "auto")).lower()
        timeout = int(os.getenv("REQUEST_TIMEOUT", os.getenv("OLLAMA_TIMEOUT", "120")))
        if timeout <= 0:
            raise LLMProviderError("REQUEST_TIMEOUT must be greater than 0")
        if provider_type == "ollama_cloud":
            if not os.getenv("OLLAMA_API_KEY"):
                raise LLMProviderError("OLLAMA_API_KEY is required when LLM_PROVIDER=ollama_cloud")
            base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/api")
            if not base_url.startswith("https://"):
                raise LLMProviderError("OLLAMA_BASE_URL must use https in ollama_cloud mode")
        return provider_type
    
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
