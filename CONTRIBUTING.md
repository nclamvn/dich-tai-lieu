# 🤝 Contributing to AI Publisher Pro

Cảm ơn bạn đã quan tâm đến việc đóng góp cho dự án! Dưới đây là hướng dẫn để bạn có thể contribute.

## 📋 Code of Conduct

- Tôn trọng mọi người
- Constructive feedback
- Không spam, không quảng cáo

## 🐛 Báo lỗi (Bug Reports)

1. Kiểm tra [Issues](https://github.com/nclamvn/dich-tai-lieu/issues) xem bug đã được báo chưa
2. Nếu chưa, tạo issue mới với template:

```markdown
**Mô tả bug**
Mô tả ngắn gọn về bug.

**Các bước tái hiện**
1. Mở '...'
2. Click '...'
3. Scroll xuống '...'
4. Thấy lỗi

**Expected behavior**
Mô tả behavior bạn mong đợi.

**Screenshots**
Nếu có thể, thêm screenshots.

**Environment:**
 - OS: [e.g. macOS, Windows, Linux]
 - Python version: [e.g. 3.10]
 - Browser: [e.g. Chrome, Safari]
```

## 💡 Đề xuất tính năng (Feature Requests)

1. Kiểm tra [Issues](https://github.com/nclamvn/dich-tai-lieu/issues) xem đã có ai đề xuất chưa
2. Tạo issue với label `enhancement`
3. Mô tả rõ:
   - Vấn đề bạn muốn giải quyết
   - Giải pháp bạn đề xuất
   - Alternatives bạn đã cân nhắc

## 🔧 Pull Requests

### Setup Development Environment

```bash
# Fork repo trên GitHub

# Clone fork của bạn
git clone https://github.com/YOUR_USERNAME/dich-tai-lieu.git
cd dich-tai-lieu

# Tạo virtual environment
python -m venv venv
source venv/bin/activate

# Cài dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# Tạo branch mới
git checkout -b feature/your-feature-name
```

### Coding Standards

- **Python**: Follow PEP 8
- **Docstrings**: Google style
- **Type hints**: Sử dụng type hints
- **Tests**: Viết tests cho code mới

```python
def translate_document(
    file_path: str,
    target_language: str = "vi"
) -> TranslationResult:
    """
    Translate a document to target language.
    
    Args:
        file_path: Path to the document file.
        target_language: Target language code.
        
    Returns:
        TranslationResult with translated content.
        
    Raises:
        FileNotFoundError: If file doesn't exist.
        TranslationError: If translation fails.
    """
    ...
```

### Commit Messages

Sử dụng format:

```
type: short description

Longer description if needed.

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code change
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

### Submit PR

1. Push changes lên fork của bạn
2. Tạo Pull Request
3. Điền template PR
4. Wait for review

## 📁 Project Structure

```
dich-tai-lieu/
├── api/              # FastAPI routers + services
├── core/             # Core subsystems (rendering, ocr, tm, glossary, …)
│   ├── smart_extraction/   # Document analysis & extraction routing
│   └── rendering/          # AST renderer stack (DOCX/PDF/EPUB + covers)
├── core_v2/          # Claude-native publish pipeline (orchestrator, chunker)
├── ai_providers/     # LLM integrations (OpenAI/Anthropic/DeepSeek/Gemini)
├── frontend/         # Next.js 16 app
└── tests/            # Test suite (~3,200 tests)
```

## 🧪 Running Tests & CI gates

```bash
# All tests (use --no-cov to skip the coverage threshold; must be 100% green)
pytest tests/ -q --no-cov

# Specific module
pytest tests/unit/test_smart_extraction.py -v

# With coverage
pytest tests/ --cov=core --cov-report=html
```

CI blocks a PR unless ALL of these pass — run them locally first:

```bash
ruff check .                    # lint (hard gate)
pytest tests/ -q --no-cov       # Python 3.11 & 3.12 in CI
cd frontend && npx vitest run   # frontend unit tests
cd frontend && npx tsc --noEmit # type check (hard gate)
```

Python 3.11+ required.

## 📝 Documentation

- Update README.md nếu thêm features mới
- Thêm docstrings cho functions/classes mới
- Update CHANGELOG.md

## ❓ Questions?

- Tạo [Discussion](https://github.com/nclamvn/dich-tai-lieu/discussions)
- Hoặc comment trong Issue/PR

---

Cảm ơn bạn đã contribute! 🙏
