# 🔄 Agent 2 → Agent 3 Contract

## Core Principle

```
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   Agent 2 OUTPUT = Agent 3 INPUT                                    ║
║                                                                      ║
║   Nếu Agent 2 chuẩn bị output ĐÚNG CÁCH:                            ║
║   → Agent 3 xử lý mượt mà                                           ║
║   → Không phụ thuộc độ dài document                                 ║
║   → Không vỡ cấu trúc                                               ║
║   → Không overflow memory                                            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Output Structure (Agent 2 → Agent 3)

```
book_output/
│
├── manifest.json              # DNA của document
│   ├── document_type         # ebook | academic | business
│   ├── render_mode           # ebook | academic | business
│   ├── structure             # counts: chapters, sections, paragraphs
│   ├── chapters[]            # list of chapter info
│   │   ├── id               # "001", "002", ...
│   │   ├── file             # "chapters/001_chapter.md"
│   │   ├── title            # "Khởi đầu"
│   │   ├── word_count       # 3500
│   │   └── sections[]       # list of section info
│   └── render_hints          # page_break, indent, style
│
├── metadata.json              # Book metadata
│   ├── title                 # "Tiểu sử Sam Altman"
│   ├── subtitle              # "CEO OpenAI"
│   ├── author                # "Chu Hằng Tinh"
│   ├── translator            # "AI Publisher Pro"
│   ├── language              # {source: "zh", target: "vi"}
│   └── publication           # {year, publisher, isbn}
│
├── chapters/                  # Từng chapter riêng biệt
│   ├── 001_chapter.md        # Chapter 1
│   ├── 002_chapter.md        # Chapter 2
│   ├── 003_chapter.md        # Chapter 3
│   └── ...
│
└── assets/
    └── glossary.json          # Thuật ngữ đã dịch
        ├── terms             # {"AI": "trí tuệ nhân tạo", ...}
        ├── names             # {"Sam Altman": "Sam Altman", ...}
        └── places            # {"Silicon Valley": "Thung lũng Silicon", ...}
```

---

## Chapter File Format

```markdown
---
chapter_id: "001"
chapter_title: "Khởi đầu"
chapter_number: 1
---

# Khởi đầu

Đoạn mở đầu không có indent. Đây là first paragraph sau heading.

Đoạn thứ hai có first-line indent. Nội dung tiếp tục với nhiều câu
và ý tưởng được phát triển đầy đủ trong paragraph.

## Tuổi thơ

Phần này nói về tuổi thơ của nhân vật.

> Đây là một trích dẫn quan trọng từ nhân vật hoặc nguồn khác.

Tiếp tục nội dung sau trích dẫn.

## Gia đình

Phần tiếp theo về gia đình.

**Bold text** và *italic text* được hỗ trợ.

- Danh sách item 1
- Danh sách item 2
- Danh sách item 3
```

---

## Workflow

### Agent 2: Translator (Chuẩn bị output)

```python
from agent2_output_format import Agent2OutputBuilder

# 1. Khởi tạo builder
builder = Agent2OutputBuilder("./output/my_book")

# 2. Set metadata
builder.set_metadata(
    title="Tiểu sử Sam Altman",
    author="Chu Hằng Tinh",
    subtitle="CEO OpenAI, Cha đẻ ChatGPT",
    source_language="zh",
    target_language="vi"
)

# 3. Set document type
builder.set_document_type(DocumentType.EBOOK)

# 4. Add chapters one by one (as translated)
# QUAN TRỌNG: Mỗi chapter được add riêng, không load toàn bộ
for i, chapter_content in enumerate(translated_chapters):
    builder.add_chapter(
        chapter_id=f"{i+1:03d}",
        title=chapter_titles[i],
        content=chapter_content
    )
    
    # Update glossary nếu có term mới
    for term, translation in new_terms:
        builder.add_glossary_term(term, translation)

# 5. Finalize (save manifest, validate)
builder.finalize()

# Output: ./output/my_book/ folder ready for Agent 3
```

### Agent 3: Publisher (Consume output)

```python
from agent3_publisher import Agent3_Publisher

# 1. Khởi tạo với Agent 2 output folder
publisher = Agent3_Publisher("./output/my_book")

# 2. Render PDF
# QUAN TRỌNG: Stream render - process từng chapter, không load toàn bộ
result = publisher.render("./my_book.pdf")

print(f"Created: {result['pages']} pages")
print(f"Size: {result['size_bytes']} bytes")
```

---

## Tại sao workflow này giải quyết mọi vấn đề?

### 1. Context Window Limit

```
❌ TRƯỚC:
Agent 2: Load 300 trang → Dịch 1 lần → Output 1 file lớn
→ Vượt context limit → Vỡ cấu trúc

✅ SAU:
Agent 2: Dịch từng chapter (15-20 trang) → Output từng file
→ Mỗi call nhỏ → Không vượt limit
```

### 2. Vỡ Cấu Trúc

```
❌ TRƯỚC:
Agent 3: Không biết có bao nhiêu chapter
→ Parse markdown → Miss headings → Vỡ structure

✅ SAU:
Agent 3: Đọc manifest.json TRƯỚC
→ Biết trước: 15 chapters, 48 sections, 1247 paragraphs
→ Validate: count(files) == manifest
→ Không thể vỡ
```

### 3. Thuật Ngữ Không Nhất Quán

```
❌ TRƯỚC:
Chapter 1: "artificial intelligence" → "trí tuệ nhân tạo"
Chapter 5: "artificial intelligence" → "trí thông minh nhân tạo"
→ Không nhất quán

✅ SAU:
glossary.json được update mỗi chapter
→ Chapter 1: add term → save glossary
→ Chapter 2: load glossary → use same translation
→ Nhất quán 100%
```

### 4. Memory Overflow khi Render

```
❌ TRƯỚC:
Agent 3: Load toàn bộ 300 trang → Build PDF
→ Memory overflow

✅ SAU:
Agent 3: 
for chapter in reader.iter_chapters():  # Generator
    render_chapter(chapter)              # Process 1 chapter
    flush_pages_if_needed()             # Release memory
→ Bounded memory, unlimited document size
```

### 5. Phụ Thuộc Độ Dài

```
❌ TRƯỚC:
10 chapters: Works
50 chapters: Slow
100 chapters: Crash

✅ SAU:
10 chapters: Loop 10 lần
50 chapters: Loop 50 lần
100 chapters: Loop 100 lần
→ Linear scaling, no crash
```

---

## Validation

### Agent 2 Validation (khi finalize)

```python
def _validate(self):
    # 1. Check all chapter files exist
    for chapter in manifest.chapters:
        assert Path(chapter.file).exists()
    
    # 2. Check counts match
    actual_files = list(chapters_dir.glob("*_chapter.md"))
    assert len(actual_files) == len(manifest.chapters)
    
    # 3. Check word counts reasonable
    for chapter in manifest.chapters:
        assert chapter.word_count > 0
```

### Agent 3 Validation (before render)

```python
def _validate_input(self):
    # 1. manifest.json exists
    assert (input_dir / "manifest.json").exists()
    
    # 2. All chapter files exist
    for chapter in manifest.chapters:
        assert (input_dir / chapter.file).exists()
    
    # 3. Chapter count matches
    actual = len(list(chapters_dir.glob("*.md")))
    expected = len(manifest.chapters)
    assert actual == expected
```

---

## Key Takeaways

1. **Agent 2 output là CONTRACT** - định nghĩa chính xác format
2. **Chunking by design** - mỗi chapter là 1 file riêng
3. **State persistence** - glossary, manifest trong files
4. **Streaming** - không hold toàn bộ trong memory
5. **Validation** - kiểm tra trước khi render

---

## Files Created

```
agent2_output_format/
└── output_format.py     # Agent2OutputBuilder, Agent3InputReader

agent3_publisher/
└── publisher.py         # StreamingEbookRenderer, Agent3_Publisher
```

---

## Usage Example

```bash
# Agent 2: Output to folder
python agent2_translator.py input.pdf --output ./book_output/

# Agent 3: Render from folder
python agent3_publisher.py ./book_output/ -o book.pdf

# Result: book.pdf with any number of pages
```
