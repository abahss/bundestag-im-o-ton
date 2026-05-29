from datetime import datetime
import streamlit as st
import requests
import Topics

st.set_page_config(
    page_title="Practice What You Preach",
    page_icon="🦔",
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

try:
    topics_response = requests.get("http://localhost:8000/topics").json()
except Exception:
    topics_response = []

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
    page = st.Page(lambda tk=top_key, ti=title, su=subtitle, sb=subs, dt=dt: Topics.render(tk, ti, su, sb, dt), title=nav_label, url_path=url_path)
    pages.append(page)
    topic_pages[top_key] = page

st.session_state.topic_pages = topic_pages

# pg = st.navigation(pages)  # sidebar navigation — uncomment to re-enable
pg = st.navigation(pages, position="hidden")
pg.run()
