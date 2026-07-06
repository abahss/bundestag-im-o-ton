## practice-preach-ui

- Deployed app: https://bundestag-im-o-ton.streamlit.app/
### Uv

[Install uv](https://docs.astral.sh/uv/getting-started/installation/) then
install dependencies:

```
uv sync
```

Run in dev mode:

```
uv run streamlit app.py
```

### Themes

Themes and basic design choices can be changed in the config.toml file found in the folder .streamlit
Alternatively, as we import more stuff, we can also use CSS injection in st.markdown() to customise better
