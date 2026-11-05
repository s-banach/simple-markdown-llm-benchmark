# simple-markdown-llm-benchmark

A markdown table reading benchmark for LLMs. It generates large markdown tables, asks questions whose answers are exact text from the table, and grades the replies by exact match.

## Run benchmark v1

```
uv run simple-markdown-llm-benchmark-v1                # writes benchmark_v1_seed0/
# send each tests/<test>.txt to a model unchanged; save its reply as my_answers/<test>.txt
uv run simple-markdown-llm-benchmark-grade benchmark_v1_seed0 my_answers
```

The test set holds 18 tables of 12,000 cells each: 1000×12, 300×40 and 100×120 (rows × columns), with plausible or gibberish content. Each table has 30 questions: look up a cell, copy a whole row, or list a column's values in every row that matches a condition. Each `tests/<test>.txt` is a complete prompt of about 140,000 characters. `keys/<test>.json` holds the answers; never show it to the model.

The model must reply with one block per question, headed `=== Q<n>`, with one value per line for list answers. The grader prints accuracy by table shape, content and question kind, and counts wrong answers by class, such as wrong column or rows missed. `--details details.jsonl` writes the result of every question.

`--seed` draws a fresh test set with the same settings. Seed 0 is the reference set.

## Make your own tables

```
uv run simple-markdown-llm-benchmark --rows 1000 --columns 30 --content gibberish --questions 50 --tables 5 > bench.jsonl
```

This writes one JSON line per table, holding the table's markdown and its questions with answers. `--help` lists every option.

## Test verbatim quoting of paragraphs

```
uv run simple-markdown-llm-benchmark --rows 80 --columns 8 --prose-columns 2 --kinds quote --questions 30 --tables 3 > prose.jsonl
uv run simple-markdown-llm-benchmark-testset prose.jsonl prose_testset
uv run simple-markdown-llm-benchmark-grade prose_testset my_answers
```

`--prose-columns` turns the last columns into prose: each cell holds two or more paragraphs joined by `<br><br>`, which the model must copy exactly. A quote question asks for one prose cell. The grader counts a wrong quote as partial (part of the passage), breaks changed (the right words with other `<br>` tags or line breaks) or edited.

`--prose-length short` uses the same complaints cut to at most 400 characters, from 530 to 1522, by deleting whole sentences, never rewording. Gibberish passages copy the paragraph word counts of these shorter texts.

Plausible prose comes from `narratives_long.jsonl` and `narratives_short.jsonl`: 500 consumer complaints received in July 2026, 466 of them in the short file, from the [CFPB narratives archive](https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/). The CFPB's complaint API marks its data CC0. Each entry keeps its complaint ID. The texts keep the CFPB's redactions (`XXXX`, `XX/XX/year>`, `{$50.00}`), which a model may tidy when copying. The CFPB flattened each narrative to one line, so the paragraph breaks replace spaces between sentences. The archive is public, so models trained after August 2026 may have seen these texts. Gibberish prose has the paragraph word counts of a random narrative, filled with random words.

`simple-markdown-llm-benchmark-testset` writes the output of any generator run as a test set, so the grader can score it.
