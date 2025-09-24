# DebtEase Backend Testing Framework

Comprehensive testing framework for the DebtEase backend API, covering unit tests, integration tests, API tests, and end-to-end workflows.

## 🧪 Test Structure

```
test/
├── conftest.py                 # Pytest fixtures and configuration
├── test_models_comprehensive.py # Unit tests for Pydantic models
├── test_repositories_integration.py # Integration tests for repositories
├── test_api_comprehensive.py   # API endpoint tests
├── test_ai_endpoints.py        # AI-specific endpoint tests
├── test_ai_agents.py          # AI agent functionality tests
├── test_e2e_workflows.py       # End-to-end user journey tests
├── test_performance.py         # Performance and load tests
└── README.md                   # This file
```

## 🏃‍♂️ Running Tests

### Quick Commands

```bash
# Run all tests with coverage
python run_tests.py all

# Run complete test suite (linting, type checking, security, all tests)
python run_tests.py full-suite

# Run specific test categories
python run_tests.py unit          # Unit tests only
python run_tests.py integration   # Integration tests only
python run_tests.py api           # API endpoint tests only
python run_tests.py ai            # AI agent tests only
python run_tests.py e2e           # End-to-end tests only
python run_tests.py performance   # Performance tests only

# Run code quality checks
python run_tests.py lint          # Linting (flake8, black, isort)
python run_tests.py type-check    # Type checking (mypy)
python run_tests.py security      # Security scanning (bandit)
```

### Manual Pytest Commands

```bash
# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run specific test markers
pytest -m "unit and not slow"
pytest -m "integration"
pytest -m "api"
pytest -m "ai"
pytest -m "e2e"
pytest -m "performance"

# Run specific test files
pytest test/test_models_comprehensive.py -v
pytest test/test_e2e_workflows.py::TestUserOnboardingWorkflow::test_complete_user_onboarding_journey -v

# Run with different output formats
pytest --tb=short  # Shorter traceback
pytest --durations=10  # Show slowest tests
```

## 🗂️ Test Categories

### Unit Tests (`pytest -m unit`)
- Test individual functions and classes in isolation
- Mock external dependencies
- Focus on business logic validation
- Files: `test_models_comprehensive.py`

### Integration Tests (`pytest -m integration`)
- Test repository layer with actual database
- Test component interactions
- Verify data persistence and retrieval
- Files: `test_repositories_integration.py`

### API Tests (`pytest -m api`)
- Test FastAPI endpoints with HTTP client
- Verify request/response formats
- Test authentication and authorization
- Files: `test_api_comprehensive.py`, `test_ai_endpoints.py`

### AI Agent Tests (`pytest -m ai`)
- Test AI agent functionality
- Mock LLM calls for deterministic testing
- Verify recommendation algorithms
- Files: `test_ai_agents.py`

### End-to-End Tests (`pytest -m e2e`)
- Test complete user workflows
- From registration to AI insights
- Verify data flows between components
- Files: `test_e2e_workflows.py`

### Performance Tests (`pytest -m performance`)
- Test response times and throughput
- Load testing with concurrent requests
- Memory usage monitoring
- Files: `test_performance.py`

## 🛠️ Test Fixtures

### Database Fixtures
- `test_engine`: Async PostgreSQL engine for testing
- `test_session`: Database session with transaction rollback
- `test_user`: Pre-created test user
- `test_debts`: Pre-created test debts for user

### API Fixtures
- `test_app`: FastAPI test application
- `test_client`: HTTPX async client for API testing
- `authenticated_user`: User with valid session token

### AI Fixtures
- `ai_agent_config`: Configuration for AI agent testing
- `mock_ai_response`: Mock AI agent responses

## 📊 Coverage Requirements

- **Target Coverage**: 80% minimum
- **Source**: `app/` package only
- **Reports**: HTML, XML, and terminal output
- **Exclusions**: Test files, migrations, main entry point

## 🔧 Configuration

### Pytest Configuration (`pyproject.toml`)
```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "--cov=app",
    "--cov-report=html:htmlcov",
    "--cov-report=xml",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
    "-v",
    "--asyncio-mode=auto"
]
testpaths = ["test"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "api: API endpoint tests",
    "e2e: End-to-end tests",
    "auth: Authentication tests",
    "ai: AI agent tests",
    "slow: Slow running tests",
    "database: Database related tests"
]
```

### Test Database
- **Database**: `debtease_test`
- **Host**: `localhost:5432`
- **Credentials**: `postgres/postgres`
- **Auto-migrations**: Run before test execution

## 🚀 CI/CD Integration

### GitHub Actions
- Automatic test execution on push/PR
- PostgreSQL service for database tests
- Coverage reporting to Codecov
- Security scanning with Bandit
- Performance testing pipeline

### Local Development
```bash
# Set up test database
createdb debtease_test

# Run tests
python run_tests.py full-suite
```

## 🎯 Key Testing Features

### Authentication Testing
- Session-based authentication validation
- Protected endpoint access control
- Token expiration handling

### AI Integration Testing
- Mock LLM responses for deterministic tests
- Caching behavior verification
- Performance benchmarking

### Database Testing
- Transaction rollback for test isolation
- Schema validation
- Migration testing

### API Testing
- Request/response validation
- Error handling verification
- Rate limiting simulation

### Performance Testing
- Response time monitoring (<500ms target)
- Concurrent request handling
- Memory usage tracking

## 📈 Test Results

After running tests, check:
- **Coverage Report**: `htmlcov/index.html`
- **Performance Metrics**: Response times and throughput
- **Error Logs**: Any test failures with detailed traces

## 🔍 Debugging Tests

```bash
# Debug specific test
pytest test/test_e2e_workflows.py::TestUserOnboardingWorkflow::test_complete_user_onboarding_journey -v -s

# Run with debugging
pytest --pdb  # Drop into debugger on failure

# Profile performance
pytest --durations=10  # Show slowest tests
```

## 📚 Best Practices

1. **Test Isolation**: Each test should be independent
2. **Mock External Services**: Don't rely on real APIs/LLMs in tests
3. **Use Fixtures**: Reuse test data and setup
4. **Clear Naming**: Test functions should describe what they test
5. **Coverage Goals**: Aim for high coverage but prioritize meaningful tests
6. **Performance**: Keep tests fast, mark slow tests appropriately

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and test database exists
2. **Import Errors**: Check Python path and dependencies
3. **Async Issues**: Ensure proper async/await usage in tests
4. **Fixture Errors**: Check fixture dependencies and scope

### Getting Help

- Check test output for detailed error messages
- Use `--tb=long` for full tracebacks
- Review fixture setup in `conftest.py`
- Check database logs for connection issues
