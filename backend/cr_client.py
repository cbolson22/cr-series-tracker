import requests
from .config import CR_TOKEN

if not CR_TOKEN:
    raise ValueError("Missing CR_TOKEN in environment or config.")

BASE = "https://api.clashroyale.com/v1"
HEADERS = {
    "Authorization": f"Bearer {CR_TOKEN}",
    "Accept": "application/json",
}

"""
Fetch the (25?) most recent battles for a given player tag.
Tag must include the leading '#'.
Returns: list of battle dictionaries (JSON-decoded).
"""
def player_battlelog(tag: str):
    # tag must be URL-encoded (# -> %23) when used in URL
    safe_tag = tag.replace("#", "%23")
    try:
        url = f"{BASE}/players/{safe_tag}/battlelog"
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error {r.status_code}: {r.text}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    return None
