import os
from datetime import datetime
from PIL import Image
import streamlit as st
import requests
import Topics

BACKEND_URL = st.secrets.get("BACKEND_URL", os.environ.get("BACKEND_URL", "http://localhost:8000"))

st.set_page_config(
    page_title="Bundestag im O-Ton",
    page_icon=Image.open("glaskuppel_emoji.png"),
    layout='wide'
)

st.markdown("""
<style>
header.stAppHeader { background-color: transparent; }
section.stMain .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; z-index: 1; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #023047;
}
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] {
    background-color: #219EBC !important;
    border-radius: 6px;
}
[data-testid="stSidebarNav"] a:hover {
    background-color: #FFB703 !important;
    color: #023047 !important;
    border-radius: 6px;
}
[data-testid="stSidebarNav"] a:hover * {
    color: #023047 !important;
}

/* Headings */
h1, h2, h3 { color: #023047 !important; }

/* Containers / cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1.5px solid #219EBC !important;
    border-radius: 8px !important;
}

/* Spinner */
[data-testid="stSpinner"] { color: #219EBC; }

/* Links */
a { color: #FB8500 !important; }
</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=None)
def fetch_topics():
    try:
        return requests.get(f"{BACKEND_URL}/topics").json()
    except Exception:
        return []

topics_response = fetch_topics()

# Store KW and earliest date for Home page
if topics_response:
    dates = [datetime.strptime(t["date"], "%d.%m.%Y") for t in topics_response]
    st.session_state.kw_info = max(dates).strftime("%d.%m.%Y")
    st.session_state.earliest_date = min(dates).strftime("%d.%m.%Y")

pages = [st.Page("Home.py", title="Home")]
topic_pages = {}  # top_key → st.Page object
for t in topics_response:
    top_key = t["top_key"]
    title = t["title"] or t["top_id"]
    subtitle = t.get("subtitle", "")
    nav_label = t["top_id"].replace("Tagesordnungspunkt ", "TOP ").replace("Zusatzpunkt ", "ZP ")
    url_path = top_key.lower().replace(" ", "_").replace("/", "_")
    subs = t.get("subtopics") or []
    dt = t.get("date", "")
    tp = t.get("topic", "")
    page = st.Page(lambda tk=top_key, ti=title, su=subtitle, sb=subs, dt=dt, tp=tp: Topics.render(tk, ti, su, sb, dt, tp), title=nav_label, url_path=url_path)
    pages.append(page)
    topic_pages[top_key] = page

st.session_state.topic_pages = topic_pages

# pg = st.navigation(pages)  # sidebar navigation — uncomment to re-enable
pg = st.navigation(pages, position="hidden")
pg.run()
