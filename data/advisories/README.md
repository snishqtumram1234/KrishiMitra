# Advisory sources

- `pdfs/`: the source documents.
- `excerpts.json`: verbatim, descriptive passages built by `backend/scripts/build_advisory_excerpts.py` (never doses or chemicals;
  the script refuses them). `published_at` is null where the PDF gives only an edition year, which is in the title.
- `verification.json`: **which sources count as verified.** This is a human decision, not the script's.
  - `http://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf` (ICAR-IISR Extension Bulletin 18, Revised Edition 2023):
    marked verified on 2026-10-02 by the project owner, as an official ICAR publication.

Labels with no excerpt (healthy, leaf spot) still get a clearly labelled demo source. Leaf spot has no usable passage in the
downloaded documents (only a table row), so none was invented.
