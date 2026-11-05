# simple-markdown-llm-benchmark

Generates large markdown tables and questions whose answers are exact text from the table, to measure how often an LLM retrieves table content with 100% accuracy. It only generates data: send the questions to a model and grade by string equality with whatever harness you use.

## Usage

```
uv run simple-markdown-llm-benchmark --rows 1000 --columns 30 --content gibberish --near-duplicates 0.2 --questions 50 --tables 5 > bench.jsonl
```

`uv run simple-markdown-llm-benchmark --help` lists every option with its default. Equal options give byte-identical output.

The same generator is importable:

```python
from simple_markdown_llm_benchmark import BenchmarkConfig, generate

for record in generate(BenchmarkConfig(rows=1000, columns=30, content="gibberish")):
    prompt = f"{record.markdown}\n\n{record.questions[0].question}"
```

## Tables

Every table imitates one order table. `--content plausible` fills it with names, cities, products, prices and dates; `--content gibberish` keeps the same column layout and replaces headers and cells with random lowercase strings of `--cell-length` characters.

Columns appear in rounds of 8. Each round holds a key column, two small categories (such as `status`), two large categories (such as `shipping_city`), two numbers and a date, so every table width has about the same mix of column kinds. The order table has 40 columns; wider tables repeat them with suffixed headers (`status_2`).

Each column is drawn independently of the others: `total` is not `quantity` × `unit_price`, and `ship_date` can precede `order_date`. A model therefore has to retrieve every answer from the table; it cannot compute one from other cells.

A key column is built to give every row a different value: `order_id`, `customer`, `email`, `tracking_number` and `invoice_number`. `--near-duplicates` gives a fraction of key values a near duplicate one substituted or swapped character away (`ORD-984237` and `ORD-994237`). Edits touch only single letters or digits, so near duplicates keep their column's format.

## Output

One JSON line per table: `table_id`, the `config` that produced it, the table as `markdown`, and `questions`. Every question has `question_id`, `kind`, `question` (the text to send, including the instruction on answer format) and `answer`, plus metadata that depends on the kind:

| kind | asks for | answer | metadata |
|---|---|---|---|
| `lookup` | the value of a column in the row where a key column has a given value | one cell | `key_column`, `key_value`, `target_column`, `row_index`, `column_distance`, `key_near_duplicate` |
| `row` | every cell of the row where a key column has a given value | the cells from left to right, joined by newlines | `key_column`, `key_value`, `row_index`, `key_near_duplicate` |
| `filter` | a column's values in every row where another column has a given value (2 to 10 rows match) | the values in table order, joined by newlines | `condition_column`, `condition_value`, `target_column`, `row_indices`, `column_distance` |

`row_index` and `row_indices` are 0-based data row positions, for plotting accuracy against depth in the table. `column_distance` is the absolute difference between the positions of the key or condition column and the target column, 1 for adjacent columns. `key_near_duplicate` is true when another value in the key column is one character edit from the asked one.

Example, from `--rows 6 --columns 8 --questions 3 --seed 3`:

```
| order_id | status | shipping_city | quantity | order_date | payment_method | product | unit_price |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ORD-994237 | returned | Elmford | 31 | 2023-11-12 | bank transfer | Deluxe Speaker | 16.74 |
| ORD-732421 | delivered | Greenshire | 18 | 2024-05-27 | gift card | Canvas Scarf | 19.49 |
| ORD-140019 | shipped | Eastview | 14 | 2023-08-14 | gift card | Modular Bottle | 97.20 |
| ORD-622035 | delivered | Dunbury | 32 | 2024-06-06 | debit card | Cotton Doormat | 20.90 |
| ORD-556284 | delivered | Rockwick | 25 | 2023-01-21 | PayPal | Modular Bottle | 97.20 |
| ORD-653951 | returned | Silverbury | 32 | 2024-11-25 | gift card | Wool Speaker | 159.02 |
```

```json
{"question_id": 0, "question": "What is the value of column \"payment_method\" in the row where column \"order_id\" is \"ORD-556284\"? Reply with the exact cell text and nothing else.", "answer": "PayPal", "kind": "lookup", "key_column": "order_id", "key_value": "ORD-556284", "target_column": "payment_method", "row_index": 4, "column_distance": 5, "key_near_duplicate": false}
{"question_id": 1, "question": "List every cell of the row where column \"order_id\" is \"ORD-994237\", from left to right, one value per line. Reply with those lines and nothing else.", "answer": "ORD-994237\nreturned\nElmford\n31\n2023-11-12\nbank transfer\nDeluxe Speaker\n16.74", "kind": "row", "key_column": "order_id", "key_value": "ORD-994237", "row_index": 0, "key_near_duplicate": false}
{"question_id": 2, "question": "List the value of column \"shipping_city\" in every row where column \"product\" is \"Modular Bottle\", in table order, one value per line. Reply with those lines and nothing else.", "answer": "Eastview\nRockwick", "kind": "filter", "condition_column": "product", "condition_value": "Modular Bottle", "target_column": "shipping_city", "row_indices": [2, 4], "column_distance": 4}
```

## Design

The question kinds and options target failure modes reported for LLM table reading:

- Accuracy falls as tables grow, and faster with columns than with rows (MMTU 2025: GPT-4o 0.81 on 50 rows × 5 columns vs 0.43 on 5 × 50), hence `--rows` and `--columns`.
- The most frequent error is the right row with the wrong column (MMTU: 28% of o4-mini errors), hence `column_distance`.
- Filtering is harder than single lookups (LongTableBench 2025: GPT-4o 79 vs 52), hence `filter`.
- Random values remove the model's priors; plausible values let priors interfere (Bhandari et al. 2024), hence `--content`.
- The research for this project found no study of near-duplicate keys or cell padding, hence `--near-duplicates` and `--pad`.

Cells are rendered by hand: polars, pandas and tabulate rewrite cell text (`120` to `120.0`, `1e3` to `1000`). Values come from word lists in `columns.py`, without Faker or mimesis, so output does not change across library versions; key columns are distinct because generation rejects repeated draws. Every random draw goes through `Random.random()`, whose sequence Python keeps stable across versions. No cell contains `|`, a newline, or leading or trailing spaces.

## Development

`scripts/CI.sh` runs `ruff check`, `ruff format --check`, `pyrefly check` (strict preset) and `pytest`.
