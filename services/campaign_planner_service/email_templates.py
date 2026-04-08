import html
import re
from typing import Any, Dict, Optional


TOKEN_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def _safe(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def render_tokens(template: str, variables: Optional[Dict[str, Any]] = None) -> str:
    variables = variables or {}

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return _safe(variables.get(key), "")

    return TOKEN_PATTERN.sub(replace, template or "")


def build_campaign_email(
    *,
    subject: str,
    headline: str,
    body_html: str,
    cta_label: str,
    cta_url: str,
    preheader: str = "",
    footer_text: str = "You are receiving this email because you opted in to marketing communication.",
    company_name: str = "MAi by AIMarketer",
) -> Dict[str, str]:
    safe_subject = _safe(subject, "Marketing Campaign")
    safe_headline = html.escape(_safe(headline, "Hello"))
    safe_preheader = html.escape(_safe(preheader, safe_subject))
    safe_cta_label = html.escape(_safe(cta_label, "Learn more"))
    safe_cta_url = html.escape(_safe(cta_url, "#"), quote=True)
    safe_footer = html.escape(_safe(footer_text))
    safe_company = html.escape(_safe(company_name))

    html_body = f"""\
<!DOCTYPE html>
<html lang="en">
  <body style="margin:0;padding:0;background-color:#f4efe8;font-family:Arial,sans-serif;color:#1f2937;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{safe_preheader}</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f4efe8;margin:0;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background-color:#ffffff;border-radius:18px;overflow:hidden;">
            <tr>
              <td style="background:linear-gradient(135deg,#123524,#1f6f50);padding:28px 36px;color:#ffffff;">
                <div style="font-size:12px;letter-spacing:1.6px;text-transform:uppercase;opacity:0.88;">{safe_company}</div>
                <h1 style="margin:14px 0 0;font-size:28px;line-height:1.25;font-weight:700;">{safe_headline}</h1>
              </td>
            </tr>
            <tr>
              <td style="padding:36px 36px 20px;font-size:16px;line-height:1.7;">
                {body_html}
              </td>
            </tr>
            <tr>
              <td style="padding:0 36px 36px;">
                <a href="{safe_cta_url}" style="display:inline-block;background-color:#c86b2b;color:#ffffff;text-decoration:none;padding:14px 22px;border-radius:999px;font-size:15px;font-weight:700;">{safe_cta_label}</a>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 36px 36px;border-top:1px solid #e5e7eb;font-size:12px;line-height:1.6;color:#6b7280;">
                <p style="margin:0 0 8px;">{safe_footer}</p>
                <p style="margin:0;">{safe_company}</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    text_body = re.sub(r"<[^>]+>", "", body_html or "")
    text_body = html.unescape(text_body)
    text_body = re.sub(r"\n\s+\n", "\n\n", text_body).strip()
    text_version = "\n\n".join(
        [
            _safe(headline, "Hello"),
            text_body,
            f"{_safe(cta_label, 'Learn more')}: {_safe(cta_url, '#')}",
            _safe(footer_text),
        ]
    )

    return {
        "subject": safe_subject,
        "html": html_body,
        "text": text_version,
    }
