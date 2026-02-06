# Repository Guidelines

## Project Structure & Module Organization

- `config/`: Django project settings, URLs, and Celery configuration.
- `core/`: Main Django app with models, views, serializers, admin, and utilities.
- `pipeline/`: Celery tasks plus processing services (inference, merge, area calculation).
- `TransUNet/`: PyTorch model code used for segmentation.
- `templates/` and `static/`: Django templates and frontend assets.
- `media/`: Runtime data (inputs, outputs, weights, shapefiles). Keep its layout stable.
- `manage.py`: Django entry point; `db.sqlite3` is the default database.

## Build, Test, and Development Commands

- `python manage.py runserver`: Start the Django web UI at `http://127.0.0.1:8000`.
- `celery -A config worker -l info`: Run the background pipeline worker.
- `redis-server`: Start the Redis broker required by Celery.

## Coding Style & Naming Conventions

- Python 3.10+ and PEP8; short, meaningful docstrings for functions/classes.
- Prefer `pathlib.Path` for file paths and avoid hardcoded `media/` strings.
- Use type hints for new or critical logic in `core/` and `pipeline/`.
- Recommended tools: `black`, `isort`, `ruff` (or `flake8`), `mypy`.
- Naming: `snake_case` for Python functions/modules; `CamelCase` for classes.

## Testing Guidelines

- No automated tests are present yet.
- If adding tests, keep them close to the app (e.g., `core/tests/`, `pipeline/tests/`) and name files `test_*.py`.
- Note any test coverage gaps in the PR description.

## Commit & Pull Request Guidelines

- Git history is not available in this workspace, so no commit convention is documented.
- Use clear, scoped commit messages (e.g., `pipeline: guard missing weights`).
- PRs should include: intent, test steps (or rationale for no tests), and screenshots for UI changes.

## Security & Configuration Tips

- Configuration is loaded from `.env` via `config/settings.py`; avoid hardcoding secrets.
- Large `.tif` files are expensive to process. Keep Celery tasks idempotent and log job context.
