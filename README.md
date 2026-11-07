# NetSight

Independent, sensor-neutral assurance for sonar survey contacts: how much to trust each find, and how well each patch of seabed was really searched.

**Status:** under construction. Nothing here has been validated yet.

- Project plan: [docs/plan/final.md](docs/plan/final.md)
- Research behind the plan: [docs/research/](docs/research/)

## Development

    uv sync --all-groups
    uv run pytest
    uv run ruff check .
    uv run netsight --help

Data lives outside the repo; see [docs/data/README.md](docs/data/README.md).
