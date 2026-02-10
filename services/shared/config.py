# MAi Shared Configuration
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

import os
from typing import Dict, List, Any
import json

# Load config from environment or config files
CONFIG_DIR = os.getenv("CONFIG_DIR", "./config")

# ===== LICENSE FEATURE MATRIX =====

LICENSE_FEATURES = {
    "strategy_only": [
        "strategy_ai",
        "template_library"
    ],
    "strategy_leads": [
        "strategy_ai",
        "lead_enrichment",
        "template_library"
    ],
    "full_suite": [
        "strategy_ai",
        "lead_enrichment",
        "content_ai",
        "campaign_planner",
        "analytics",
        "multi_channel",
        "template_library"
    ]
}

# ===== CHANNEL MAPPINGS (Config-Driven) =====

def load_channel_config() -> Dict[str, List[str]]:
    """Load channel mappings from config file or use defaults"""
    config_file = os.path.join(CONFIG_DIR, "channels.json")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Default mappings
    return {
        "technology": ["LinkedIn", "Email", "Content Marketing", "Webinars"],
        "healthcare": ["Email", "LinkedIn", "Industry Publications", "Conferences"],
        "finance": ["LinkedIn", "Email", "Thought Leadership", "Referrals"],
        "manufacturing": ["LinkedIn", "Trade Shows", "Email", "Direct Sales"],
        "default": ["Email", "LinkedIn", "Social Media"]
    }

# ===== BUDGET ALLOCATION (Config-Driven) =====

def load_budget_config() -> Dict[str, int]:
    """Load budget allocation from config file or use defaults"""
    config_file = os.path.join(CONFIG_DIR, "budget.json")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Default allocation
    return {
        "paid_advertising": 40,
        "content_marketing": 25,
        "email_marketing": 15,
        "social_media": 10,
        "events_webinars": 10
    }

# ===== TARGET SEGMENTS (Config-Driven) =====

def load_segments_config() -> List[str]:
    """Load target segments from config file or use defaults"""
    config_file = os.path.join(CONFIG_DIR, "segments.json")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Default segments
    return ["Decision Makers", "Influencers", "End Users", "Technical Evaluators"]

# ===== CONTENT STRATEGY (Config-Driven) =====

def load_content_strategy_config() -> List[str]:
    """Load content strategy templates from config file or use defaults"""
    config_file = os.path.join(CONFIG_DIR, "content_strategy.json")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Default content types
    return [
        "Thought leadership articles",
        "Case studies and success stories",
        "Industry trend reports",
        "Educational webinars",
        "Product demonstrations"
    ]

# ===== KPI DEFINITIONS (Config-Driven) =====

def load_kpi_config() -> List[str]:
    """Load KPI definitions from config file or use defaults"""
    config_file = os.path.join(CONFIG_DIR, "kpis.json")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Default KPIs
    return [
        "Lead generation rate",
        "Cost per acquisition (CPA)",
        "Conversion rate",
        "Email open rates",
        "Social media engagement",
        "ROI on marketing spend"
    ]

# ===== CAMPAIGN TIMELINE (Config-Driven) =====

def load_timeline_config(timeline_type: str = "default") -> Dict[str, str]:
    """Load campaign timeline from config file or use defaults"""
    config_file = os.path.join(CONFIG_DIR, "timeline.json")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            timelines = json.load(f)
            return timelines.get(timeline_type, timelines.get("default", {}))
    
    # Default timeline
    return {
        "phase_1": "Awareness Building (Months 1-2)",
        "phase_2": "Lead Generation (Months 2-4)",
        "phase_3": "Nurturing & Conversion (Months 4-6)",
        "phase_4": "Retention & Expansion (Months 6+)"
    }
