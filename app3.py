import streamlit as st
import requests

# WHO endpoints
TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
API_URL = "https://id.who.int/icd/release/11"

st.set_page_config(page_title="🔧 WHO ICD-11 Debugger", layout="centered")

st.title("🔧 WHO ICD-11 — Stepwise Debugger (Manual Credentials)")

# Sidebar inputs for client credentials
st.sidebar.header("🔑 Provide WHO API Credentials")
client_id = st.sidebar.text_input("Client ID", type="default")
client_secret = st.sidebar.text_input("Client Secret", type="password")

# Step 1
st.subheader("Step 1 — Start Debug Session")
if client_id and client_secret:
    st.success("✅ Credentials provided manually")
else:
    st.warning("⚠️ Missing Client ID / Secret — please enter in sidebar")

# Step 2
st.subheader("Step 2 — Request Access Token")
if st.button("Get Token"):
    if not client_id or not client_secret:
        st.error("❌ Cannot request token — missing credentials")
    else:
        data = {
            "client_id": client_id.strip(),
            "client_secret": client_secret.strip(),
            "scope": "icdapi_access",
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = requests.post(TOKEN_URL, data=data, headers=headers)

        if r.status_code == 200:
            token = r.json().get("access_token")
            if token:
                st.session_state["token"] = token
                st.success("✅ Token retrieved successfully!")
                st.code(token[:40] + "...", language="text")
            else:
                st.error("❌ Failed to extract token")
                st.json(r.json())
        else:
            st.error(f"❌ Token request failed — {r.status_code}")
            st.json(r.json())

# Step 3
st.subheader("Step 3 — Run ICD Search")
query = st.text_input("Enter search query", "epilepsy")

if st.button("Search ICD"):
    token = st.session_state.get("token")
    if not token:
        st.error("❌ No token available — run Step 2 first")
    else:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "API-Version": "v2",
            "Accept-Language": "en"
        }
        search_url = f"{API_URL}/2024-01/mms/search?q={query}"
        r2 = requests.get(search_url, headers=headers)

        if r2.status_code == 200:
            try:
                data = r2.json()
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
                st.success("✅ Search successful")
                st.json(results)
            except ValueError:
                st.error("❌ Failed to parse JSON response")
                st.text(r2.text)
        else:
            st.error(f"❌ Search request failed — {r2.status_code}")
            st.text(r2.text)
