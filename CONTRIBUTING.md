# Contributing to MariaGPT-Nexus

We're excited that you're interested in contributing to MariaGPT-Nexus! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the problem, not the person
- Follow our coding standards and guidelines

## Getting Started

1. Fork the repository
2. Clone your fork:
bash
git clone https://github.com/your-username/mariagpt-nexus.git
cd mariagpt-nexus

3. Create a new branch:
bash
git checkout -b feature/your-feature-name

## Development Environment

### Prerequisites
- Python 3.8+
- pip
- virtualenv (recommended)

### Setup
1. Create and activate virtual environment:
bash
python -m venv venv
source venv/bin/activate  # Unix
venv\Scripts\activate     # Windows

2. Install dependencies:
bash
pip install -r requirements.txt
pip install -r requirements-dev.txt

## Coding Standards

### Python Style Guide
- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for classes and methods

### Documentation
- Update docstrings for new classes/methods
- Add type hints for parameters and return values
- Include usage examples in docstrings
- Update README.md if adding new features

### Testing
- Write unit tests for new features
- Maintain test coverage above 80%
- Use pytest for testing
- Mock external services in tests
- Follow existing test patterns

## Pull Request Process

1. Update documentation
2. Add/update tests
3. Run test suite:
bash
pytest tests/

4. Commit your changes:
bash
git add .
git commit -m "feat: description of your changes"

5. Push to your fork:
bash
git push origin feature/your-feature-name

6. Create Pull Request

### PR Requirements
- Clear description of changes
- Tests pass
- Documentation updated
- Code follows style guide
- No merge conflicts

## Agent Development Guidelines

### Creating New Agents
1. Inherit from BaseAgent
2. Implement required methods
3. Add comprehensive tests
4. Document agent capabilities

### Agent Integration
1. Update AgentRouter
2. Add necessary service integrations
3. Implement conversation handling
4. Add agent-specific tests

## Testing Guidelines

### Unit Tests
- Test each agent method
- Mock external services
- Test error conditions
- Verify conversation flow

### Integration Tests
- Test agent interactions
- Verify routing logic
- Test conversation context
- Check state management

## Documentation

### Code Documentation
- Clear class/method docstrings
- Type hints for all parameters
- Usage examples
- Error handling details

### API Documentation
- Document all endpoints
- Include request/response examples
- Note authentication requirements
- List error responses

## Submitting Issues

### Bug Reports
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- System information

### Feature Requests
- Clear use case
- Expected behavior
- Business value
- Implementation suggestions

## Getting Help

- Create an issue for questions
- Join our community discussions
- Check existing documentation
- Contact: hello@mudakka.com

## License

By contributing, you agree that your contributions will be licensed under the project's dual-license terms.

## Recognition

Contributors will be acknowledged in:
- CONTRIBUTORS.md
- Release notes
- Project documentation

Thank you for contributing to MariaGPT-Nexus!
```

</rewritten_file>