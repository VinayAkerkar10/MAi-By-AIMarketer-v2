def rank_posts_for_lead(lead: dict, posts: list, location: str, business_type: str) -> list:
    company_name = str(lead.get("business_name", "")).strip()
    company_name_lower = company_name.lower()
    business_type_lower = str(business_type or "").strip().lower()
    location_lower = str(location or "").strip().lower()

    ranked_posts = []

    for post in posts:
        if not isinstance(post, dict):
            continue

        score = 0
        text = str(post.get("text", ""))
        text_lower = text.lower()

        if company_name_lower:
            if company_name_lower in text_lower:
                score += 10
            else:
                company_parts = [p for p in company_name_lower.split() if p]
                if any(part in text_lower for part in company_parts):
                    score += 5

        if business_type_lower and business_type_lower in text_lower:
            score += 5

        if location_lower and location_lower in text_lower:
            score += 3

        ranked_post = dict(post)
        ranked_post["relevance_score"] = score
        ranked_posts.append(ranked_post)

    ranked_posts.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
    return ranked_posts
