# Advisory sources

- `pdfs/`: the source documents.
- `excerpts.json`: verbatim, descriptive passages built by `backend/scripts/build_advisory_excerpts.py` (never doses or chemicals;
  the script refuses them). `published_at` is null where the PDF gives only an edition year, which is in the title.
- `verification.json`: **which sources count as verified.** This is a human decision, not the script's.
  - `http://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf` (ICAR-IISR Extension Bulletin 18, Revised Edition 2023):
    marked verified on 2026-10-02 by the project owner, as an official ICAR publication.
  - `https://niphm.gov.in/IPMPackages/Soyabean.pdf` (Integrated Pest Management Package for Soybean, NCIPM and DPPQ&S,
    2014; local copy `pdfs/SoyabeanBulletin.pdf`): marked verified on 2026-10-03 by the project owner, as an official
    Government of India publication. Its text is stored shifted in the PDF; the build script decodes it with PyMuPDF.

Leaf spot (cause, monitoring, cultural practices, resistant varieties) and healthy crops (routine field monitoring) come
from the IPM package. Table rows are copied cell by cell and labelled with the table's own column headers.
