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
