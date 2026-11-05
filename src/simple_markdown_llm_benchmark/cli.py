import sys

from pydantic import ValidationError
from pydantic_settings import CliApp

from simple_markdown_llm_benchmark.benchmark import generate
from simple_markdown_llm_benchmark.config import BenchmarkConfig
from simple_markdown_llm_benchmark.sampling import GenerationError


def main() -> None:
    """Write one JSON line per table to stdout."""
    try:
        config = CliApp.run(BenchmarkConfig)
        for record in generate(config):
            print(record.model_dump_json())
    except (ValidationError, GenerationError) as error:
        sys.exit(f"error: {error}")
