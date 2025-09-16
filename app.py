import streamlit as st
import pandas as pd
import re

# --------------------
# Helper Functions
# --------------------
@st.cache_data
def load_data():
    df = pd.read_csv("Merged_CSV_3.csv")

    def clean_html(text):
        text = str(text)
        text = re.sub(r'<em>(.*?)</em>', r'*\1*', text)  # italic text
        text = re.sub(r'<[^>]+>', '', text)  # remove other HTML tags
        return text

    for col in ["Short_definition", "Long_definition", "Term", "RegionalTerm"]:
        df[col] = df[col].apply(clean_html)

    return df


# --------------------
# Streamlit UI
# --------------------
st.title("🌿 NAMASTE Terminology Search")

df = load_data()
query = st.text_input("🔍 Search for a diagnosis (term, code, or definition)")

if query:
    query_lower = query.lower()
    namaste_results = df[
        df.apply(lambda row: query_lower in str(row['Code']).lower()
                 or query_lower in str(row['Term']).lower()
                 or query_lower in str(row['RegionalTerm']).lower()
                 or query_lower in str(row['Short_definition']).lower()
                 or query_lower in str(row['Long_definition']).lower(),
                 axis=1)
    ]

    st.subheader("📘 NAMASTE Terminology")
    st.write(f"Found {len(namaste_results)} matches")

    for _, row in namaste_results.iterrows():
        with st.expander(f"{row['Code']} - {row['Term']}"):
            st.markdown(f"**Regional Term:** {row['RegionalTerm']}")
            st.markdown(f"**Short Definition:** {row['Short_definition']}")
            st.markdown(f"**Long Definition:** {row['Long_definition']}")
else:
    st.info("Type a diagnosis in the search box above 👆")
