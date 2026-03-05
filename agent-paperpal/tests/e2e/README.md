# tests/e2e/README.md
# End-to-End Integration Tests

This directory contains E2E tests that verify the full pipeline:
1. Upload a test manuscript via the API
2. Wait for pipeline completion
3. Download and verify the formatted output
4. Validate the compliance report

## Running E2E Tests

```bash
# Ensure the dev stack is running
make dev

# Run E2E tests
pytest tests/e2e/ -v
```
