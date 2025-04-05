# WebML Mailing List Scraper

Fetches and converts recent messages from the [W3C Web Machine Learning WG](https://lists.w3.org/Archives/Public/public-webmachinelearning-wg/) into Markdown for LLM analysis.

---

## 🛠️ Setup (macOS, Apple Silicon)

1. **Install `uv`**  
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone & run**  
   ```bash
   git clone https://github.com/atsyplikhin/w3-ml.git
   cd w3-ml
   uv venv && source .venv/bin/activate
   uv pip install -r pyproject.toml
   uv run python fetch_messages.py
   ```

---

## 📄 Output

Generates a Markdown file like:

```markdown
<Analysis prompt goes here>

### Message URL: https://...
<converted message content>
```

---

## 📂 Files

- `fetch_messages.py` – Scraper script  
- `pyproject.toml` – Dependencies  
- `uv.lock` – Locked versions

---

## ⚖️ License

Apache-2.0