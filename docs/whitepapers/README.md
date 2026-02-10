# Whitepapers

## Licensing caution

The PDFs stored in this repository are provided for research and citation. Verify usage rights and licenses before redistributing any content outside this repo.

## Acquisition workflow

- Source-of-truth metadata lives in `docs/whitepapers/links.yaml`.
- Run `python scripts/acquire_whitepapers.py` to download PDFs into `docs/whitepapers/pdfs`.
- Run `python scripts/verify_whitepapers.py` to validate file hashes and title checks.
