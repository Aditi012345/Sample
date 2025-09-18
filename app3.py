import streamlit as st
import requests
import os
from dotenv import load_dotenv

# ----------------------
# Load secrets from .env (or from Streamlit Cloud Secrets Manager)
# ----------------------
load_dotenv()
CLIENT_ID = os.getenv("WHO_CLIENT_ID", st.secrets.get("WHO_CLIENT_ID"))
CLIENT_SECRET = os.getenv("WHO_CLIENT_SECRET", st.secrets.get("WHO_CLIENT_SECRET"))

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
API_URL = "https://id.who.int/icd/release/11"

# ----------------------
# Helper functions
# ----------------------
@st.cache_data(ttl=3600)  # cache token for 1 hour
def get_token():
    """Fetch WHO ICD API access token"""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "icdapi_access",
        "grant_type": "client_credentials"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(TOKEN_URL, data=data, headers=headers)

    if r.status_code == 200:
        return r.json().get("access_token")
    else:
        st.error(f"Failed to get token: {r.text}")
        return None


def search_icd(q: str):
    """Search ICD-11 API for a given query term"""
    token = get_token()
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "API-Version": "v2",
        "Accept-Language": "en"
    }
    search_url = f"{API_URL}/2024-01/mms/search?q={q}"
    r = requests.get(search_url, headers=headers)

    if r.status_code != 200:
        st.error(f"ICD API Error {r.status_code}: {r.text}")
        return []

    try:
        data = r.json()
    except ValueError:
        st.error("Failed to parse JSON response")
        return []

    # Extract useful info
    entities = data.get("destinationEntities", [])
    results = []
    for ent in entities:
        code = ent.get("theCode", "")
        term = ent.get("title", "").replace("<em class='found'>", "").replace("</em>", "")
        definition = None
        for pv in ent.get("matchingPVs", []):
            if pv.get("propertyId") == "Synonym":
                definition = pv.get("label", "").replace("<em class='found'>", "").replace("</em>", "")
                break
        results.append({
            "code": code,
            "term": term,
            "definition": definition if definition else "No definition available"
        })
    return results


# ----------------------
# Streamlit App
# ----------------------
st.title("🌍 WHO ICD-11 Terminology Search")

query = st.text_input("🔍 Enter a diagnosis/term to search ICD-11", "epilepsy")

if query:
    with st.spinner("Fetching results from WHO ICD API..."):
        results = search_icd(query)

    if results:
        st.success(f"Found {len(results)} results")
        for res in results:
            with st.expander(f"{res['code']} - {res['term']}"):
                st.markdown(f"**Code:** {res['code']}")
                st.markdown(f"**Term:** {res['term']}")
                st.markdown(f"**Definition:** {res['definition']}")
    else:
        st.warning("No results found for this query.")
else:
    st.info("Type a term above to search ICD-11 🌿")
