# Contributing to Unfold 🤝

Thank you for your interest in contributing to Unfold! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- UV package manager (recommended) or pip
- Git

### Setting Up Development Environment

1. **Fork and Clone**
   ```bash
   git clone https://github.com/cyborgoat/unfold.git
   cd unfold
   ```

2. **Install Dependencies**
   ```bash
   # Using UV (recommended)
   uv pip install -e ".[dev]"
   
   # Using pip
   pip install -e ".[dev]"
   ```

3. **Verify Installation**
   ```bash
   # Run tests
   pytest
   
   # Check code style
   black --check unfold/
   flake8 unfold/
   
   # Type checking
   mypy unfold/
   ```

## 🎯 How to Contribute

### 🐛 Bug Reports

When filing a bug report, please include:

- **Clear description** of the issue
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, package versions)
- **Error messages or logs** if applicable

Use the bug report template:

```markdown
**Bug Description**
A clear description of what the bug is.

**To Reproduce**
1. Run command '...'
2. See error

**Expected Behavior**
What you expected to happen.

**Environment**
- OS: [e.g. macOS 12.0]
- Python: [e.g. 3.9.7]
- Unfold: [e.g. 0.1.0]

**Additional Context**
Any other context about the problem.
```

### 💡 Feature Requests

For feature requests, please include:

- **Clear description** of the feature
- **Use case** - why is this feature needed?
- **Proposed implementation** (if you have ideas)
- **Alternatives considered**

### 🔧 Code Contributions

1. **Check existing issues** to see if your change is already planned
2. **Create an issue** to discuss major changes before implementing
3. **Fork the repository** and create a feature branch
4. **Implement your changes** following our coding standards
5. **Add tests** for new functionality
6. **Update documentation** if needed
7. **Submit a pull request**

#### Branch Naming
- `feature/description-of-feature`
- `bugfix/description-of-fix`
- `docs/description-of-docs-change`

## 📝 Coding Standards

### Python Style Guide
We follow PEP 8 with some specific preferences:

- **Line length**: 88 characters (Black default)
- **Imports**: Use absolute imports, group by standard library, third-party, local
- **Type hints**: Required for all public functions and methods
- **Docstrings**: Google style docstrings for all public APIs

### Code Formatting
```bash
# Format code
black unfold/ tests/ examples/

# Check style
flake8 unfold/ tests/ examples/

# Type checking
mypy unfold/
```

### Example Code Style
```python
"""
Module docstring describing the purpose.
"""

import os
import time
from typing import List, Dict, Optional

from third_party_package import SomeClass

from .local_module import LocalClass


class ExampleClass:
    """Class docstring describing the class.
    
    Attributes:
        attribute_name: Description of the attribute.
    """
    
    def __init__(self, param: str, optional_param: Optional[int] = None) -> None:
        """Initialize the class.
        
        Args:
            param: Description of the parameter.
            optional_param: Description of optional parameter.
        """
        self.attribute_name = param
        self._private_attr = optional_param
    
    def public_method(self, input_data: List[str]) -> Dict[str, int]:
        """Perform some operation.
        
        Args:
            input_data: List of strings to process.
            
        Returns:
            Dictionary mapping strings to counts.
            
        Raises:
            ValueError: If input_data is empty.
        """
        if not input_data:
            raise ValueError("Input data cannot be empty")
        
        return {item: len(item) for item in input_data}
```

## 🧪 Testing

### Writing Tests
- Use `pytest` for all tests
- Aim for >90% test coverage
- Test both happy path and error cases
- Use descriptive test names

### Test Structure
```python
"""
Tests for the example module.
"""

import pytest
from unfold.core.example import ExampleClass


class TestExampleClass:
    """Test cases for ExampleClass."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.example = ExampleClass("test_param")
    
    def test_public_method_success(self):
        """Test successful operation of public_method."""
        result = self.example.public_method(["hello", "world"])
        assert result == {"hello": 5, "world": 5}
    
    def test_public_method_empty_input(self):
        """Test public_method with empty input raises ValueError."""
        with pytest.raises(ValueError, match="Input data cannot be empty"):
            self.example.public_method([])
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=unfold --cov-report=html

# Run specific test file
pytest tests/test_database.py

# Run tests matching pattern
pytest -k "test_search"
```

## 📚 Documentation

### Docstring Standards
We use Google-style docstrings:

```python
def search_files(self, query: str, limit: int = 50) -> List[SearchResult]:
    """Search for files matching the query.
    
    This method performs a comprehensive search using multiple algorithms
    including exact matching, fuzzy matching, and keyword-based search.
    
    Args:
        query: The search query string.
        limit: Maximum number of results to return. Defaults to 50.
        
    Returns:
        List of SearchResult objects sorted by relevance score.
        
    Raises:
        ValueError: If query is empty or invalid.
        DatabaseError: If database connection fails.
        
    Example:
        >>> searcher = FileSearcher()
        >>> results = searcher.search_files("python", limit=10)
        >>> print(f"Found {len(results)} files")
    """
```

### README Updates
When adding features, update:
- Feature list in README.md
- Usage examples
- Configuration options
- Performance benchmarks (if applicable)

## 🏗️ Architecture Guidelines

### Core Principles
1. **Modularity**: Keep components loosely coupled
2. **Performance**: Optimize for speed in search operations
3. **Extensibility**: Design for easy addition of new search algorithms
4. **Reliability**: Handle errors gracefully and provide useful feedback

### Component Structure
```
unfold/
├── core/               # Core functionality
│   ├── database.py     # Database operations
│   ├── indexer.py      # File indexing
│   └── searcher.py     # Search algorithms
├── utils/              # Utility modules
│   └── config.py       # Configuration management
└── cli.py              # Command-line interface
```

### Adding New Components
1. **Create the module** in the appropriate directory
2. **Add comprehensive tests** in the `tests/` directory
3. **Update imports** in `__init__.py` files
4. **Document the component** with examples
5. **Update integration tests** if needed

## 🚦 Pull Request Process

### Before Submitting
- [ ] Code follows style guidelines
- [ ] Tests pass (`pytest`)
- [ ] Code coverage maintained
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Type checking passes

### PR Description Template
```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process
1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainers
3. **Testing** on different platforms (if needed)
4. **Merge** after approval

## 🌟 Recognition

Contributors will be recognized in:
- **README.md** acknowledgments section
- **CHANGELOG.md** for their contributions
- **GitHub releases** notes

## 📞 Getting Help

- **Documentation**: Check README.md and docstrings
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **Direct contact**: Tag maintainers in issues

## 📋 Development Checklist

When working on Unfold:

### For New Features
- [ ] Issue created and discussed
- [ ] Design documented
- [ ] Code implemented
- [ ] Tests written (unit + integration)
- [ ] Documentation updated
- [ ] Performance tested
- [ ] Backward compatibility checked

### For Bug Fixes
- [ ] Issue reproduced
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Regression tests added
- [ ] Related issues checked
- [ ] Edge cases considered

### For Documentation
- [ ] Accuracy verified
- [ ] Examples tested
- [ ] Links checked
- [ ] Formatting consistent
- [ ] Typos corrected

## 🎉 Thank You!

Your contributions help make Unfold better for everyone. Whether it's a bug fix, new feature, documentation improvement, or just feedback, every contribution is valuable!

---

*For questions about contributing, please create an issue or reach out to the maintainers.* 