import json
import os
import re
import requests
import streamlit as st
import streamlit.components.v1 as components

BACKEND_URL = st.secrets.get("BACKEND_URL", os.environ.get("BACKEND_URL", "https://rag-backend-855077868686.europe-west10.run.app"))


def parse_summary(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Returns (kernposition, [(quote_text, pdf_url), ...])"""
    kernposition = ""
    quotes = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("**Kernposition:**"):
            kernposition = line.replace("**Kernposition:**", "").strip()
        elif line.startswith('*"') or line.startswith('"'):
            id_match = re.search(r'\[(ID\w+)\]', line)
            quote_match = re.search(r'"(.+?)"', line)
            if quote_match:
                quote_text = quote_match.group(1)
                pdf_url = ""
                if id_match:
                    sid = id_match.group(1)
                    wp = sid[2:4]
                    session = sid[4:6].zfill(3)
                    pdf_url = f"https://dserver.bundestag.de/btp/{wp}/{wp}{session}.pdf"
                quotes.append((quote_text, pdf_url))
    return kernposition, quotes


PARTIES = [
    ("LINKE", "Die Linke"),
    ("GRÜNEN", "B90 – Die Grünen"),
    ("SPD", "SPD"),
    ("CDUCSU", "CDU/CSU"),
    ("AFD", "AfD"),
]

PARTY_COLORS = {
    "AFD": "#009EE0",
    "GRÜNEN": "#46962B",
    "CDUCSU": "#000000",
    "LINKE": "#BE3075",
    "SPD": "#E3000F",
}


def _quote_carousel_html(card_id: str, quotes: list) -> str:
    if not quotes:
        return "<style>body{margin:0;padding:0}</style><p style='color:#aaa;font-size:0.78rem;font-style:italic;margin:0'>Keine Zitate verfügbar.</p>"

    safe_quotes = json.dumps([{"text": q[0], "url": q[1]} for q in quotes])
    first_quote = quotes[0][0].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    first_url = quotes[0][1]
    n = len(quotes)
    nav_display = "flex" if n > 1 else "none"

    return f"""
    <style>
      body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
      .qs {{ border-left: 3px solid #ddd; padding-left: 10px; }}
      .qt {{ font-style: italic; font-size: 0.78rem; line-height: 1.5; color: #444; margin: 0 0 6px 0; }}
      .qnav {{ display: flex; align-items: center; gap: 8px; }}
      .nb {{
        background: none; border: 1px solid #ccc; border-radius: 4px;
        padding: 0 6px; cursor: pointer; font-size: 1.05rem; color: #555; line-height: 1.5;
      }}
      .nb:hover {{ background: #f5f5f5; }}
      .sl {{ color: #FB8500; text-decoration: none; font-size: 0.75rem; }}
      .sl:hover {{ text-decoration: underline; }}
      .ctr {{ color: #aaa; font-size: 0.7rem; margin-left: auto; }}
    </style>
    <div class="qs">
      <p class="qt" id="qt_{card_id}">&bdquo;{first_quote}&ldquo;</p>
      <div class="qnav" style="display:{nav_display}">
        <button class="nb" onclick="nav_{card_id}(-1)">&#8249;</button>
        <a class="sl" id="ql_{card_id}" href="{first_url}" target="_blank"
           onclick="navigator.clipboard.writeText(window.qdata_{card_id}[window.qidx_{card_id}].text)">
          &#128203; Quelle
        </a>
        <span class="ctr" id="ctr_{card_id}">1 / {n}</span>
        <button class="nb" onclick="nav_{card_id}(1)">&#8250;</button>
      </div>
    </div>
    <script>
      window.qdata_{card_id} = {safe_quotes};
      window.qidx_{card_id} = 0;
      window.nav_{card_id} = function(d) {{
        const q = window.qdata_{card_id};
        window.qidx_{card_id} = (window.qidx_{card_id} + d + q.length) % q.length;
        const i = window.qidx_{card_id};
        document.getElementById('qt_{card_id}').innerHTML = '&bdquo;' + q[i].text + '&ldquo;';
        const link = document.getElementById('ql_{card_id}');
        link.href = q[i].url || '#';
        link.onclick = function() {{ navigator.clipboard.writeText(q[i].text); }};
        document.getElementById('ctr_{card_id}').textContent = (i + 1) + ' / ' + q.length;
      }};
    </script>
    """


# Plain string template — no f-string, so JS curly braces need no escaping.
# Party data is injected via .replace("%%PARTY_DATA%%", data_json).
_PARLIAMENT_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: transparent; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
#card { max-width: 520px; margin: 16px auto 0; padding: 16px 18px; border: 1.5px solid #e0e0e0; border-radius: 8px; }
#card.empty { display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 0.88rem; min-height: 60px; border: none; }
.hdr { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.pname { font-weight: 700; font-size: 0.95rem; }
.sinfo { margin-left: auto; color: #aaa; font-size: 0.75rem; white-space: nowrap; padding-left: 8px; }
.kp { color: #111; font-size: 0.87rem; line-height: 1.65; margin-bottom: 14px; }
.kp.missing { color: #aaa; font-style: italic; }
.qblock { padding-left: 12px; margin-bottom: 14px; }
.qt { font-style: italic; font-family: Georgia, "Times New Roman", serif; font-size: 0.82rem; color: #444; line-height: 1.6; }
.foot { display: flex; align-items: center; gap: 6px; }
.nb { background: none; border: 1px solid #ccc; border-radius: 4px; padding: 2px 7px; cursor: pointer; font-size: 1rem; color: #555; line-height: 1.5; }
.nb:hover:not(:disabled) { background: #f5f5f5; }
.nb:disabled { opacity: 0.3; cursor: default; }
.ctr { color: #aaa; font-size: 0.75rem; }
.sl { color: #FB8500; text-decoration: none; font-size: 0.75rem; }
.sl:hover { text-decoration: underline; }
.ra { margin-left: auto; display: flex; align-items: center; gap: 6px; }
.rb { background: none; border: 1px solid #ccc; border-radius: 4px; padding: 3px 9px; cursor: pointer; font-size: 0.78rem; color: #555; }
.rb:hover:not(:disabled) { background: #f5f5f5; }
.rb:disabled { opacity: 0.4; cursor: default; }
.rl { color: #aaa; font-size: 0.72rem; }
</style>
</head>
<body>
<svg id="parl" viewBox="0 0 520 270" width="520" height="270"
     xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto"></svg>
<div id="card" class="empty">Wähle eine Partei aus</div>
<script>
(function () {
  var PARTIES = %%PARTY_DATA%%;
  var MAX_REF = 5;
  var CX = 260, CY = 265, R = 250, IR = 155, MR = (R + IR) / 2;
  var TOTAL = PARTIES.reduce(function(s, p) { return s + p.seats; }, 0);
  var GAP   = 0.025;
  var AVAIL = Math.PI - GAP * (PARTIES.length - 1);

  var activeIdx = -1, qIdx = 0;
  var paths = [];
  var card  = document.getElementById('card');

  function pt(a, rad) {
    return (CX + rad * Math.cos(a)).toFixed(2) + ',' + (CY - rad * Math.sin(a)).toFixed(2);
  }
  function sectorPath(a1, a2) {
    var la = a1 - a2 > Math.PI ? 1 : 0;
    return 'M ' + pt(a1,R) + ' A ' + R + ',' + R + ' 0 ' + la + ',1 ' + pt(a2,R) +
           ' L ' + pt(a2,IR) + ' A ' + IR + ',' + IR + ' 0 ' + la + ',0 ' + pt(a1,IR) + ' Z';
  }
  function addLabel(x, y, txt, size, opacity, weight) {
    var t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('x', x.toFixed(2)); t.setAttribute('y', y.toFixed(2));
    t.setAttribute('text-anchor', 'middle'); t.setAttribute('dominant-baseline', 'central');
    t.setAttribute('fill', 'white'); t.setAttribute('fill-opacity', opacity);
    t.setAttribute('font-size', size); t.setAttribute('font-weight', weight);
    t.setAttribute('font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif');
    t.setAttribute('pointer-events', 'none');
    t.textContent = txt;
    return t;
  }

  function updateOpacities() {
    paths.forEach(function(path, i) {
      path.setAttribute('opacity', activeIdx === -1 || i === activeIdx ? '1' : '0.4');
    });
  }

  function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  window._cp = function() {
    var q = (PARTIES[activeIdx].quotes || [])[qIdx];
    if (q) navigator.clipboard.writeText(q.text);
  };

  function renderCard() {
    var p  = PARTIES[activeIdx];
    var qs = p.quotes;
    var q  = qs[qIdx] || {};
    var n  = qs.length;
    var remaining = MAX_REF - (p.refresh_count || 0);
    var atLimit   = remaining <= 0;

    var srcHtml = q.url
      ? '<a class="sl" id="src" href="' + q.url + '" target="_blank"' +
        ' onclick="window._cp()">&#128203; Quelle</a>'
      : '';
    var quoteHtml = n
      ? '<p class="qt" id="qt">&#8222;' + esc(q.text || '') + '&#8220;</p>'
      : '<p class="qt" style="color:#aaa;font-style:italic">Keine Zitate verfügbar.</p>';
    var navHtml = n > 1
      ? '<button class="nb" onclick="window._pQ(-1)">&#8249;</button>' + srcHtml +
        '<span class="ctr" id="ctr">' + (qIdx + 1) + ' / ' + n + '</span>' +
        '<button class="nb" onclick="window._pQ(1)">&#8250;</button>'
      : srcHtml;

    card.className = '';
    card.innerHTML =
      '<div class="hdr">' +
        '<span class="dot" style="background:' + p.color + '"></span>' +
        '<span class="pname" style="color:' + p.color + '">' + esc(p.full) + '</span>' +
        '<span class="sinfo">' + p.seats + ' Sitze · ' + p.pct + '%</span>' +
      '</div>' +
      '<p class="kp' + (p.kernposition ? '' : ' missing') + '">' +
        esc(p.kernposition || 'Keine Zusammenfassung verfügbar.') + '</p>' +
      '<div class="qblock" style="border-left:3px solid ' + p.color + '">' + quoteHtml + '</div>' +
      '<div class="foot">' + navHtml +
        '<div class="ra">' +
          '<button class="rb" onclick="window._ref()"' + (atLimit ? ' disabled' : '') + '>&#8635; Neu generieren</button>' +
          '<span class="rl">' + (atLimit ? 'Limit erreicht' : remaining + ' übrig') + '</span>' +
        '</div>' +
      '</div>';
  }

  window._pQ = function(d) {
    if (activeIdx < 0) return;
    var n = PARTIES[activeIdx].quotes.length;
    qIdx = (qIdx + d + n) % n;
    var q = PARTIES[activeIdx].quotes[qIdx];
    var qtEl = document.getElementById('qt');
    if (qtEl) qtEl.innerHTML = '&#8222;' + esc(q.text) + '&#8220;';
    var src = document.getElementById('src');
    if (src) src.href = q.url || '#';
    var ctr = document.getElementById('ctr');
    if (ctr) ctr.textContent = (qIdx + 1) + ' / ' + n;
  };

  window._ref = function() {
    if (activeIdx < 0) return;
    var p   = PARTIES[activeIdx];
    var btn = document.querySelector('.rb');
    if (!btn || btn.disabled) return;
    var orig = btn.innerHTML;
    btn.disabled = true; btn.innerHTML = '…';
    var subKey = '%%SUB_KEY%%';
    fetch('%%BACKEND_URL%%/summaries/refresh?top_key=' + encodeURIComponent(p.top_key) +
          '&party=' + encodeURIComponent(p.key) +
          (subKey ? '&sub_key=' + encodeURIComponent(subKey) : ''), { method: 'POST' })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var lines = (data.summary || '').split('\\n');
        for (var i = 0; i < lines.length; i++) {
          var s = lines[i].trim();
          if (s.indexOf('**Kernposition:**') === 0) {
            p.kernposition = s.replace('**Kernposition:**', '').trim();
            break;
          }
        }
        p.refresh_count = data.refresh_count != null ? data.refresh_count : (p.refresh_count || 0) + 1;
        renderCard();
      })
      .catch(function() { if (btn) { btn.disabled = false; btn.innerHTML = orig; } });
  };

  var svg   = document.getElementById('parl');
  var angle = Math.PI;

  PARTIES.forEach(function(p, i) {
    var span = (p.seats / TOTAL) * AVAIL;
    var a1 = angle, a2 = angle - span;

    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', sectorPath(a1, a2));
    path.setAttribute('fill', p.color);
    path.style.cursor = 'pointer';
    path.style.transition = 'opacity 0.15s ease';
    svg.appendChild(path);
    paths.push(path);

    path.addEventListener('mouseenter', function() { if (activeIdx !== -1 && i !== activeIdx) path.setAttribute('opacity', '0.65'); });
    path.addEventListener('mouseleave', function() { if (activeIdx !== -1 && i !== activeIdx) path.setAttribute('opacity', '0.4'); });
    path.addEventListener('click', function() { activeIdx = i; qIdx = 0; updateOpacities(); renderCard(); });

    var midA = (a1 + a2) / 2;
    var tx = CX + MR * Math.cos(midA), ty = CY - MR * Math.sin(midA);
    svg.appendChild(addLabel(tx, ty - 9, p.short, '14', '1',   '500'));
    svg.appendChild(addLabel(tx, ty + 9, p.seats + ' Sitze', '11', '0.7', 'normal'));

    angle -= span + (i < PARTIES.length - 1 ? GAP : 0);
  });

  updateOpacities();
}());
</script>
</body>
</html>"""


def _parliament_html(party_data: list, top_key: str) -> str:
    for p in party_data:
        p["top_key"] = top_key
    data_json = json.dumps(party_data, ensure_ascii=False).replace("</", "<\\/")
    return (_PARLIAMENT_TEMPLATE
            .replace("%%PARTY_DATA%%", data_json)
            .replace("%%SUB_KEY%%", "")
            .replace("%%BACKEND_URL%%", BACKEND_URL))


_PARTY_META = [
    ("LINKE",  64,  "#BE3075", "Linke",   "Die Linke"),
    ("GRÜNEN", 85,  "#46962B", "Grüne",   "Bündnis 90/Die Grünen"),
    ("SPD",    120, "#E3000F", "SPD",     "SPD"),
    ("CDUCSU", 208, "#1a1a1a", "CDU/CSU", "CDU/CSU"),
    ("AFD",    152, "#009EE0", "AfD",     "AfD"),
]


def _fetch_summaries(top_key: str) -> dict | None:
    ss_key = f"summaries_{top_key}"
    if ss_key not in st.session_state:
        with st.spinner("Lade Zusammenfassungen...", show_time=True):
            try:
                data = requests.get(f"{BACKEND_URL}/summaries", params={"top_key": top_key}).json()
            except Exception as e:
                st.error(f"Fehler beim Laden: {e}")
                return None
        st.session_state[ss_key] = data
    return st.session_state[ss_key]


def render(top_key: str, title: str = "", subtitle: str = "", subtopics: list = None, date: str = "", topic: str = ""):
    st.markdown(
        "<style>section.stMain .block-container { max-width: calc(50vw + 23rem) !important; }</style>",
        unsafe_allow_html=True,
    )
    if st.button("← Übersicht"):
        if date:
            try:
                from datetime import datetime as _dt
                d = _dt.strptime(date, "%d.%m.%Y")
                st.session_state.cal_year = d.year
                st.session_state.cal_month = d.month
                st.session_state.cal_selected_date = date
            except ValueError:
                pass
        st.session_state.expand_top_key = top_key
        st.switch_page("Home.py")

    heading = topic or title
    if heading:
        st.markdown(f"### {heading}")
    if subtopics:
        for s in subtopics:
            st.caption(f"{s['key']}) {s['title']}")

    data = _fetch_summaries(top_key)
    if not data:
        return

    general = data.get("general", {}).get("summary", "")

    party_data = []
    for key, seats, color, short, full in _PARTY_META:
        entry = data.get(key, {})
        raw = entry.get("summary", "")
        kernposition, quotes = parse_summary(raw) if raw else ("", [])
        party_data.append({
            "key":           key,
            "seats":         seats,
            "pct":           round(seats / 629 * 100),
            "color":         color,
            "short":         short,
            "full":          full,
            "kernposition":  kernposition,
            "quotes":        [{"text": q[0], "url": q[1]} for q in quotes],
            "refresh_count": entry.get("refresh_count", 0),
        })

    if general:
        left_col, right_col = st.columns([2, 3])
        with left_col:
            st.markdown(general)
        with right_col:
            components.html(_parliament_html(party_data, top_key), height=900)
    else:
        components.html(_parliament_html(party_data, top_key), height=900)
