# Contributing to HyperLiquidWalletTracker

Thank you for your interest in contributing to HyperLiquidWalletTracker! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Basic understanding of async Python programming

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/hyperliquidwallettracker.git
   cd hyperliquidwallettracker
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Install development dependencies**:
   ```bash
   pip install black isort ruff mypy pytest pytest-asyncio pytest-cov
   ```

## 🛠️ Development Workflow

### Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **ruff** for linting
- **mypy** for type checking

Run these before committing:
```bash
black hyperliquidwallettracker/
isort hyperliquidwallettracker/
ruff check hyperliquidwallettracker/
mypy hyperliquidwallettracker/
```

### Testing

Run tests with:
```bash
pytest tests/ -v --cov=hyperliquidwallettracker
```

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

## 📝 Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-telegram-support`
- `bugfix/fix-websocket-reconnection`
- `docs/update-readme`

### Commit Messages

Use clear, descriptive commit messages:
```
feat: add Discord rich embeds support
fix: resolve WebSocket connection timeout
docs: update installation instructions
```

### Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** with clear, focused commits
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Run all checks** (formatting, linting, tests)
6. **Submit a pull request** with a clear description

## 🐛 Reporting Issues

When reporting issues, please include:

- **Python version**
- **Operating system**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Error messages/logs**

## 💡 Feature Requests

For feature requests, please:

- **Check existing issues** first
- **Describe the use case** clearly
- **Explain the expected behavior**
- **Consider implementation complexity**

## 📋 Code Review Guidelines

### For Contributors

- **Keep PRs focused** - one feature/fix per PR
- **Write clear descriptions** of changes
- **Add tests** for new functionality
- **Update documentation** as needed
- **Respond to feedback** promptly

### For Reviewers

- **Be constructive** in feedback
- **Test the changes** locally if possible
- **Check for security issues**
- **Verify documentation** is updated
- **Approve when ready** for merge

## 🏗️ Architecture Guidelines

### Adding New Features

1. **Follow the existing patterns** in the codebase
2. **Use async/await** for I/O operations
3. **Add proper error handling** and logging
4. **Include type hints** for all functions
5. **Write comprehensive tests**

### Notification Channels

When adding new notification channels:

1. **Create a new module** in `notifications/`
2. **Implement the channel interface**
3. **Add configuration options**
4. **Update the dispatcher**
5. **Add tests and documentation**

### Alert Rules

When adding new alert rules:

1. **Define the rule** in `alerts/rules.py`
2. **Implement the condition** logic
3. **Add configuration options**
4. **Update the rules engine**
5. **Add tests and examples**

## 📚 Documentation

### Code Documentation

- **Use docstrings** for all public functions
- **Include type hints** for parameters and returns
- **Add examples** for complex functions
- **Document configuration options**

### User Documentation

- **Update README.md** for new features
- **Add usage examples** in documentation
- **Include configuration examples**
- **Update CLI help text**

## 🚀 Release Process

Releases are managed by the maintainers:

1. **Version bump** in `pyproject.toml`
2. **Update CHANGELOG.md**
3. **Create release tag**
4. **Build and publish** to PyPI

## 🤝 Community Guidelines

- **Be respectful** and inclusive
- **Help others** learn and grow
- **Share knowledge** and best practices
- **Follow the code of conduct**

## 📞 Getting Help

- **GitHub Issues** for bug reports and feature requests
- **GitHub Discussions** for questions and ideas
- **Discord/Telegram** for real-time chat (if available)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to HyperLiquidWalletTracker! 🚀
