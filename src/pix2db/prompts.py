"""Prompts. The SQL prompt is also the instruction used for fine-tuning (keep it stable)."""

SQL_PROMPT = """Convert all data shown in this image into a SQLite database.
Output only SQL, in a single ```sql code block:
1. CREATE TABLE statements: snake_case table and column names; column types INTEGER, REAL or TEXT; \
PRIMARY KEY and FOREIGN KEY constraints where the image implies a relationship \
(for example a document header and its line items).
2. INSERT statements for every record.
Rules: one row per record (repeat the value of a merged cell in every row it covers); flatten multi-level \
headers into single column names; store numbers without thousand separators or currency symbols; \
write dates as YYYY-MM-DD; use NULL for empty cells; do not store total or subtotal rows (they are derived); for a chart, create one table with the category column and one column per data series; do not invent rows or columns."""

HTML_PROMPT = """Convert every table and form in this image to HTML.
Output only HTML <table> elements, in a single ```html code block. Keep rowspan and colspan exactly as \
in the image. Write each key-value form (label: value) as its own table with one header row of labels \
and one data row of values. Copy cell text exactly as shown."""

PROMPTS = {"sql": SQL_PROMPT, "html": HTML_PROMPT}
