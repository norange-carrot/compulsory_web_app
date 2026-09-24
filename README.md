# Code of Points Helper

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## How it works

- **`extract_catalog.py`** provides the PDF extraction functions used by the app.
- **`main.py`** is a Streamlit app that lets you upload a source PDF and extract
  its catalog in one step.
- Extracted records and image data are kept in the Streamlit session. Images are
  staged in a temporary directory during extraction and are not persisted as
  catalog data by the app.
- A PDF must be uploaded again after the session is restarted; the app does not
  load a previously extracted `catalog.json` or `images/` directory.

The source PDF is processed in memory, but image extraction currently uses a
temporary local directory internally. That directory is removed after extraction
finishes.

## Run

```bash
streamlit run src/main.py
```

## Disclaimer

This project is an unofficial, independent tool and is **not affiliated with,
endorsed by, or sponsored by** the International Pole Sports Federation (IPSF)
or any other rulebook publisher.

The Code of Points PDF is copyrighted material owned by its publisher. This
repository does not include or distribute that PDF. You must supply your own
legally obtained copy and upload it to the app. Only the extraction and viewing
code is intended to be distributed; the rulebook content itself remains the
property of its original publisher.
