from datetime import datetime
from typing import Any, Dict, List, Tuple

from .lead_source_provider import LeadSourceProvider
from services.shared.api_keys import get_org_api_key


class GitHubProvider(LeadSourceProvider):
    def provider_name(self) -> str:
        return "github"

    def validate_config(self, org_context: Dict[str, Any]) -> bool:
        db = org_context.get("db_session")
        organization_id = org_context.get("organization_id")
        if db is None or not organization_id:
            return False
        api_key, _ = get_org_api_key(db, organization_id, self.provider_name())
        return bool(api_key)

    async def scrape(
        self,
        request: Any,
        org_context: Dict[str, Any],
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        print("DEBUG: ENTERED GitHub scrape")
        try:
            db = org_context.get("db_session")
            organization_id = org_context.get("organization_id")
            token, _ = get_org_api_key(db, organization_id, self.provider_name())
            print("DEBUG: GitHub token prefix:", token[:6] if token else "NONE")
            if not token:
                return "error", [], "Provider not configured for this organization."

            max_results = max(1, min(int(request.max_results or 30), 30))
            query = f"location:{request.location} {request.business_type} in:bio"
            print("DEBUG: GitHub query:", query)
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                search_response = await client.get(
                    "https://api.github.com/search/users",
                    params={
                        "q": query,
                        "per_page": max_results,
                        "page": 1,
                        "type": "Users",
                    },
                    headers=headers,
                )
                print("DEBUG: GitHub status:", search_response.status_code)
                print("DEBUG: GitHub response:", search_response.text[:500])

                if search_response.status_code == 403:
                    remaining = search_response.headers.get("X-RateLimit-Remaining", "")
                    if remaining == "0":
                        return "error", [], "GitHub API rate limit exceeded."
                    return "error", [], "GitHub API access forbidden."

                if search_response.status_code != 200:
                    return "error", [], f"GitHub API returned status {search_response.status_code}."

                search_json = search_response.json() if search_response.content else {}
                items = search_json.get("items", []) if isinstance(search_json, dict) else []

                leads: List[Dict[str, Any]] = []
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    username = item.get("login")
                    if not username:
                        continue

                    user_response = await client.get(
                        f"https://api.github.com/users/{username}",
                        headers=headers,
                    )
                    if user_response.status_code == 403 and user_response.headers.get("X-RateLimit-Remaining") == "0":
                        return "error", leads, "GitHub API rate limit exceeded."
                    if user_response.status_code != 200:
                        continue

                    user_data = user_response.json() if user_response.content else {}
                    if not isinstance(user_data, dict):
                        continue

                    repos_response = await client.get(
                        f"https://api.github.com/users/{username}/repos",
                        params={"sort": "updated", "per_page": 5},
                        headers=headers,
                    )

                    repos_data = repos_response.json() if repos_response.status_code == 200 and repos_response.content else []
                    top_repos = [
                        repo.get("name")
                        for repo in repos_data[:3]
                        if isinstance(repo, dict) and repo.get("name")
                    ]

                    business_name = user_data.get("company") or user_data.get("login") or username
                    website = user_data.get("blog") or user_data.get("html_url") or "N/A"

                    lead = {
                        "business_name": business_name,
                        "contact_name": user_data.get("name") or "N/A",
                        "email": user_data.get("email") or "N/A",
                        "phone": None,
                        "website": website,
                        "address": user_data.get("location") or request.location,
                        "source": "github",
                        "category": request.business_type,
                        "scraped_at": datetime.utcnow().isoformat(),
                        "metadata": {
                            "followers": user_data.get("followers", 0),
                            "public_repos": user_data.get("public_repos", 0),
                            "top_repos": top_repos,
                            "bio": user_data.get("bio") or "",
                        },
                    }
                    leads.append(lead)

                return "success", leads, ""
        except Exception as e:
            print("GITHUB SCRAPE ERROR:", str(e))
            return "error", [], f"GitHub scraping failed: {str(e)}"
