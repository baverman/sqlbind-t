# AGENTS

## Operational Notes

- Prefer running tests through Dockerized CI wrapper:
  - `./ci/run.sh ci/py3.14 -q`
  - For targeted tests: `./ci/run.sh ci/py3.14 -q <pytest-args>`
- `ci/run.sh` uses `docker run -it`, so commands must run with a TTY-capable executor.
