# who_icd_debug.py
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from pprint import pformat

load_dotenv()

st.set_page_config(page_title="WHO ICD Debugger", layout="wide")

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
API_URL = "https://id.who.int/icd/release/11"

# -------------------------
# Helper utilities
# -------------------------
def load_default_credentials():
    cid = ''
    csec = ''
    try:
        cid = os.getenv("WHO_CLIENT_ID")
        csec = os.getenv("WHO_CLIENT_SECRET")
    except Exception:
       print("Exception occured here!!!!")
    return cid, csec

def mask_secret(s, keep=4):
    if not s:
        return "Not provided"
    if len(s) <= keep * 2:
        return "*" * len(s)
    return s[:keep] + "..." + s[-keep:]

def pretty_json(obj):
    try:
        return pformat(obj, indent=2)
    except Exception:
        return str(obj)

def post_token_request(client_id, client_secret, scope="icdapi_access", timeout=15):
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
        "grant_type": "client_credentials"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=timeout)
    return r, data, headers

def get_search(q, token, timeout=15):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "API-Version": "v2",
        "Accept-Language": "en"
    }
    search_url = f"{API_URL}/2024-01/mms/search?q={requests.utils.requote_uri(q)}"
    r = requests.get(search_url, headers=headers, timeout=timeout)
    return r, search_url, headers

# -------------------------
# Page layout
# -------------------------
st.title("🔧 WHO ICD-11 — Stepwise Debugger (Token → Query)")

with st.sidebar:
    st.header("Credentials & Options")
    default_cid, default_csec = load_default_credentials()
    st.markdown("Credentials are loaded in this priority:\n- Streamlit Secrets\n- Environment variables (`.env`)\n- Manual input (below)")
    manual = st.checkbox("🔑 Paste / override credentials manually")
    if manual:
        client_id = st.text_input("Client ID", value=default_cid or "", help="Paste WHO client id", placeholder="paste client_id here")
        client_secret = st.text_input("Client Secret", value="", type="password", help="Paste WHO client secret (won't be shown)", placeholder="paste client_secret here")
    else:
        client_id = default_cid or ""
        client_secret = ""
        st.write("Detected Client ID:", mask_secret(client_id))
        st.write("Client Secret:", "Configured (hidden)" if default_csec else "Not provided")

    st.write("---")
    st.checkbox("Show raw request/response details", key="show_debug", value=True)
    st.button("Clear stored token & responses", on_click=lambda: st.session_state.clear())

# Initialize session_state keys we will use
if "started" not in st.session_state:
    st.session_state.started = False
if "token_response" not in st.session_state:
    st.session_state.token_response = None
if "token_value" not in st.session_state:
    st.session_state.token_value = None
if "token_status" not in st.session_state:
    st.session_state.token_status = None
if "search_response" not in st.session_state:
    st.session_state.search_response = None
if "search_status" not in st.session_state:
    st.session_state.search_status = None
if "last_search_url" not in st.session_state:
    st.session_state.last_search_url = None

# -------------------------
# STEP 1: Start server / session
# -------------------------
st.header("Step 1 — Start debug session")
col1, col2 = st.columns([1, 2])
with col1:
    if st.button("▶️ Start debug session"):
        st.session_state.started = True
        st.success("Debug session started — ready for token retrieval.")
with col2:
    st.markdown(
        """
        This step simply confirms that the app is ready and shows where credentials come from.
        If you didn't paste credentials above and Streamlit Secrets / env are empty, the next step will tell you.
        """
    )

if st.session_state.started:
    st.info("Session is started. You can now Request Token (Step 2).")

    # show detected / used client id (masked)
    if manual:
        used_cid = client_id.strip()
        used_csec = client_secret.strip()
    else:
        used_cid = default_cid or ""
        used_csec = default_csec or ""

    st.write("Using client_id:", mask_secret(used_cid))
    st.write("Client secret provided?" , "Yes" if used_csec else "No — using manual input required to send token request")

# -------------------------
# STEP 2: Get token
# -------------------------
st.header("Step 2 — Request access token (POST)")
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🔐 Get Token (POST)"):
        # determine credentials to use
        if manual:
            cid_for_call = client_id.strip()
            csec_for_call = client_secret.strip()
        else:
            cid_for_call = default_cid or ""
            csec_for_call = default_csec or ""

        if not cid_for_call or not csec_for_call:
            st.session_state.token_response = None
            st.session_state.token_value = None
            st.error("Missing client_id or client_secret. Provide credentials via Streamlit Secrets, env, or manual input in sidebar.")
        else:
            with st.spinner("Requesting token from WHO..."):
                try:
                    r, body, req_headers = post_token_request(cid_for_call, csec_for_call)
                    st.session_state.token_status = r.status_code
                    # try parse json
                    try:
                        parsed = r.json()
                    except Exception:
                        parsed = None
                    st.session_state.token_response = {
                        "status_code": r.status_code,
                        "headers": dict(r.headers),
                        "text": r.text,
                        "json": parsed,
                        "used_client_id_masked": mask_secret(cid_for_call)
                    }
                    if r.status_code == 200 and parsed and parsed.get("access_token"):
                        st.session_state.token_value = parsed.get("access_token")
                        st.success("Token retrieved successfully ✅")
                        st.info("Token stored in session (masked below).")
                    else:
                        st.session_state.token_value = None
                        st.warning("Token request did not return an access_token. Check response below for details.")
                except requests.exceptions.RequestException as e:
                    st.session_state.token_response = {"error": str(e)}
                    st.session_state.token_value = None
                    st.error(f"Request failed: {e}")

with col2:
    st.markdown(
        "When you click **Get Token**, the app will POST to the WHO token endpoint using `client_credentials`. "
        "If you receive `invalid_client`, common causes are:\n\n"
        "- Wrong client_id / client_secret (copy-paste error, extra spaces).\n"
        "- Credentials are not enabled for client_credentials grant.\n"
        "- Using the wrong credential (e.g., a different API or test credentials).\n\n"
        "If you don't see credentials, set them in **Streamlit Secrets** or check your `.env`."
    )

# show token response debug
if st.session_state.token_response:
    st.write("---")
    st.subheader("Token response (debug)")
    tr = st.session_state.token_response
    if isinstance(tr, dict) and "error" in tr:
        st.error(tr["error"])
    else:
        st.write("Status code:", tr.get("status_code"))
        if st.session_state.get("show_debug", True):
            st.write("Response headers:")
            st.text(pretty_json(tr.get("headers")))
            st.write("Response JSON (if any):")
            st.code(pretty_json(tr.get("json")))
            st.write("Raw response text:")
            st.code(tr.get("text")[:4000])  # cap to avoid overflows

    if st.session_state.token_value:
        st.write("Stored access token (masked):")
        st.code(mask_secret(st.session_state.token_value, keep=6))

    if tr.get("status_code") == 400 or tr.get("status_code") == 401:
        st.error("Token endpoint returned 400/401 (invalid_client or unauthorized). See the checklist below.")
        st.markdown(
            """
            **Debug checklist for `invalid_client`:**
            1. Ensure your `client_id` and `client_secret` are the exact values from WHO (no leading/trailing spaces).  
            2. Confirm the credentials are for the ICD API and support `client_credentials` grant.  
            3. If you are using environment variables, make sure the Streamlit app is receiving them (on Cloud use Secrets).  
            4. Try pasting the client_id manually (sidebar) and request token again.  
            5. If possible, create a fresh client in the WHO Access Management portal and try those credentials.
            """
        )

# -------------------------
# STEP 3: Run search
# -------------------------
st.header("Step 3 — Run ICD search using the token")
q_col, btn_col = st.columns([4, 1])
query = q_col.text_input("Search query", value="epilepsy")
with btn_col:
    if st.button("🔎 Run search"):
        if not st.session_state.token_value:
            st.error("No access token available. Run Step 2 (Get Token) first.")
        else:
            with st.spinner("Calling ICD search..."):
                try:
                    r_search, search_url, req_headers = get_search(query, st.session_state.token_value)
                    st.session_state.search_status = r_search.status_code
                    try:
                        parsed_search = r_search.json()
                    except Exception:
                        parsed_search = None
                    st.session_state.search_response = {
                        "status_code": r_search.status_code,
                        "headers": dict(r_search.headers),
                        "text": r_search.text,
                        "json": parsed_search,
                        "url": search_url
                    }
                    st.session_state.last_search_url = search_url
                    if r_search.status_code == 200:
                        st.success("Search completed (200). Results below.")
                    else:
                        st.warning(f"Search returned status {r_search.status_code}. See raw response below.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Search request failed: {e}")
                    st.session_state.search_response = {"error": str(e)}
                    st.session_state.search_status = None

# show search debug
if st.session_state.search_response:
    st.write("---")
    st.subheader("Search response (debug)")
    sr = st.session_state.search_response
    if "error" in sr:
        st.error(sr["error"])
    else:
        st.write("Requested URL:")
        st.text(sr.get("url"))
        st.write("Status code:", sr.get("status_code"))
        if st.session_state.get("show_debug", True):
            st.write("Response headers:")
            st.text(pretty_json(sr.get("headers")))
            st.write("Response JSON (partial):")
            st.code(pretty_json(sr.get("json"))[:20000])

        # Try to parse and display entities if present
        if sr.get("json") and isinstance(sr.get("json"), dict):
            entities = sr["json"].get("destinationEntities") or sr["json"].get("entities") or []
            if entities:
                st.write(f"Found {len(entities)} destinationEntities (showing first 10):")
                for ent in entities[:10]:
                    code = ent.get("theCode", "N/A")
                    title = ent.get("title", "")
                    # remove highlight tags if present
                    if isinstance(title, str):
                        title = title.replace("<em class='found'>", "").replace("</em>", "").strip()
                    st.markdown(f"**{code} — {title}**")
                    # show some matchingPVs if any
                    mpvs = ent.get("matchingPVs", [])
                    if mpvs:
                        for pv in mpvs[:3]:
                            st.markdown(f"- {pv.get('propertyId')}: {pv.get('label')}")
            else:
                st.info("No destinationEntities array found in the response JSON. Inspect raw JSON above.")

# -------------------------
# Footer & tips
# -------------------------
st.write("---")
st.markdown(
    """
    **Helpful notes**

    - On Streamlit Cloud: set `WHO_CLIENT_ID` and `WHO_CLIENT_SECRET` under **Settings → Secrets** (or paste them manually).
    - If you keep getting `invalid_client`, double-check the exact values (no extra whitespace), ensure the client supports `client_credentials`, and that you are using the correct credentials from the WHO Access Management portal.
    - If everything looks correct but the error persists, try creating a new client in WHO portal or contact WHO API support (they may need to enable the client).
    """
)
