# Contributing to Cyber Threat Visualizer

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Redis 7+
- Npcap (Windows) or libpcap (Linux/macOS)

### Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/cyber-threat-visualizer.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Install dependencies:
   ```bash
   # Backend
   cd backend && pip install -r requirements.txt
   
   # Frontend
   cd frontend && npm install
   ```
5. Copy `.env.example` to `.env` and configure
6. Run tests: `pytest tests/ -v` and `cd frontend && npm test`

## Development Workflow

### Branching Strategy
- `main` - Production ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Urgent production fixes

### Commit Messages
Follow conventional commits:
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(sniffer): add support for IPv6 packet capture
fix(ml): handle edge case in Isolation Forest threshold
docs(readme): update installation instructions for Windows
```

### Pull Request Process
1. Ensure all tests pass
2. Update documentation if needed
3. Add tests for new functionality
4. Keep PR focused and atomic
5. Request review from maintainers
5. Address review comments
6. Squash commits before merge

## Code Standards

### Python (Backend)
- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use `black` for formatting
- Use `isort` for imports
- Type hints required for public APIs
- Docstrings for public functions/classes (Google style)

### TypeScript/React (Frontend)
- Use TypeScript strict mode
- Follow React best practices
- Use functional components with hooks
- Use `clsx` for conditional classes
- Follow Tailwind CSS conventions
- Component names in PascalCase

### Testing
- Unit tests for all new functions
- Integration tests for API endpoints
- Minimum 80% code coverage
- Test edge cases and error conditions

### Documentation
- Update README for user-facing changes
- Update API docs for endpoint changes
- Add inline comments for complex logic
- Update architecture diagrams for structural changes

## Project Structure Guidelines

### Backend
```
backend/
├── api/           # FastAPI routes, websockets, schemas
├── sniffer/       # Packet capture and feature extraction
├── ml/            # ML models and training
├── utils/         # Shared utilities
├── config.py      # Configuration
└── main.py        # Entry point
```

### Frontend
```
frontend/src/
├── components/    # React components
│   ├── globe/     # Three.js globe components
│   ├── hud/       # HUD overlays
│   └── ui/        # UI components
├── hooks/         # Custom React hooks
├── utils/         # Utilities
├── styles/        # Global styles
└── App.tsx        # Main app
```

## Security Considerations

- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all inputs
- Sanitize outputs
- Use parameterized queries
- Keep dependencies updated
- Run security scans regularly

## Reporting Issues

### Bug Reports
Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python/Node versions, Docker version)
- Relevant logs/screenshots
- Minimal reproduction case if possible

### Feature Requests
Include:
- Clear description of the feature
- Use case and motivation
- Proposed implementation approach
- Potential alternatives considered
- Impact on existing functionality

## Release Process

1. Update version in `package.json` and `backend/__init__.py`
2. Update CHANGELOG.md
3. Create release branch
4. Run full test suite
5. Create release PR
6. Tag release after merge
7. Build and push Docker images
8. Update documentation

## Getting Help

- Check existing issues and discussions
- Join our Discord/Slack community
- Read the documentation
- Ask questions in GitHub Discussions

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Annual contributor spotlight

Thank you for contributing to Cyber Threat Visualizer! 🛡️