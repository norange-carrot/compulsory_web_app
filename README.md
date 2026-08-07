# Code of Points Helper

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## How it works

- **Part 1 -- `extract_catalog.py`**: reads the source PDF (a `.pdf` file in this
  folder) and saves everything the app needs into `data/`:
  - `data/catalog.json` -- text fields (code, name, technical value, criteria, etc.) for every element
  - `data/images/*` -- the illustration for each element
- **Part 2 -- `main.py`**: a Streamlit app that reads `data/catalog.json`
  and `data/images/`.
  - You can upload a PDF in the sidebar and extract automatically in one step.
  - Or you can still run `extract_catalog.py` manually.

Run extraction whenever the source PDF changes.

## Run

```bash
streamlit run main.py       # upload+extract in app OR browse existing extracted data

# optional manual extraction path:
python extract_catalog.py   # PDF -> data/catalog.json + data/images/
```

## Disclaimer

This project is an unofficial, independent tool and is **not affiliated with,
endorsed by, or sponsored by** the International Pole Sports Federation (IPSF)
or any other rulebook publisher.

The Code of Points PDF is copyrighted material owned by its publisher. This
repository does not include or distribute that PDF, nor the `data/catalog.json`
and `data/images/` extracted from it -- you must supply your own legally
obtained copy of the PDF and generate that data locally by running
`extract_catalog.py`. Only the extraction/viewing code in this repository is
distributed; the rulebook content itself remains the property of its original
publisher.
