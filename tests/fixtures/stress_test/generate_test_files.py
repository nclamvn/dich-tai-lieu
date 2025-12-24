#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stress Test File Generator for AI Translator Pro

Generates 6 test files designed to stress-test the translation pipeline:
1. large_100_pages.txt      - Scale test (100+ pages, 20 chapters)
2. extreme_paragraphs.txt   - Mixed paragraph sizes (tiny to huge)
3. repetitive_content.txt   - Similar but not identical content (fuzzy match killer)
4. complex_structure.txt    - Mixed content types (code, tables, lists)
5. unicode_stress.txt       - Multi-language and special characters
6. checkpoint_killer.txt    - Exactly 100 chunks for checkpoint testing

Usage:
    python generate_test_files.py

Author: AI Translator Pro Test Suite
"""

import random
import os
from pathlib import Path

# Seed for reproducibility
random.seed(42)

OUTPUT_DIR = Path(__file__).parent

# ============================================================================
# CONTENT TEMPLATES
# ============================================================================

AI_ML_TOPICS = [
    "neural networks", "deep learning", "machine learning", "artificial intelligence",
    "natural language processing", "computer vision", "reinforcement learning",
    "gradient descent", "backpropagation", "convolutional networks", "transformers",
    "attention mechanisms", "BERT", "GPT", "large language models", "embeddings",
    "feature extraction", "classification", "regression", "clustering",
    "supervised learning", "unsupervised learning", "semi-supervised learning",
    "transfer learning", "fine-tuning", "hyperparameter optimization",
    "cross-validation", "overfitting", "underfitting", "regularization",
    "batch normalization", "dropout", "activation functions", "loss functions"
]

AI_ML_SENTENCES = [
    "The {topic} algorithm processes input data through multiple layers of abstraction.",
    "Research in {topic} has shown significant improvements in accuracy and efficiency.",
    "Modern approaches to {topic} leverage large-scale datasets for training.",
    "The implementation of {topic} requires careful consideration of computational resources.",
    "Recent advances in {topic} have enabled new applications across various domains.",
    "The theoretical foundations of {topic} are rooted in statistical learning theory.",
    "Practitioners of {topic} must balance model complexity with generalization ability.",
    "The evolution of {topic} has been driven by both algorithmic innovations and hardware advances.",
    "Applications of {topic} span healthcare, finance, autonomous systems, and more.",
    "The future of {topic} promises even more sophisticated and capable systems.",
    "Understanding {topic} requires knowledge of linear algebra, calculus, and probability.",
    "The training process for {topic} involves iterative optimization of model parameters.",
    "Evaluation metrics for {topic} include precision, recall, F1-score, and AUC-ROC.",
    "The deployment of {topic} systems requires careful attention to latency and throughput.",
    "Ethical considerations in {topic} include bias, fairness, and transparency.",
]

VIETNAMESE_SENTENCES = [
    "Trí tuệ nhân tạo đang thay đổi cách chúng ta sống và làm việc.",
    "Học máy là một nhánh quan trọng của trí tuệ nhân tạo.",
    "Các mô hình ngôn ngữ lớn có khả năng hiểu và sinh văn bản tự nhiên.",
    "Việt Nam đang đầu tư mạnh vào nghiên cứu và phát triển AI.",
    "Ứng dụng của deep learning rất đa dạng từ y tế đến tài chính.",
    "Xử lý ngôn ngữ tự nhiên giúp máy tính hiểu được tiếng người.",
    "Thị giác máy tính cho phép máy nhận diện và phân tích hình ảnh.",
    "Học tăng cường được sử dụng trong các hệ thống tự động.",
]

CHINESE_SENTENCES = [
    "人工智能正在改变我们的世界。",
    "机器学习是人工智能的重要分支。",
    "深度学习已经取得了显著的进展。",
    "自然语言处理使计算机能够理解人类语言。",
    "计算机视觉让机器能够看见和理解图像。",
]

JAPANESE_SENTENCES = [
    "人工知能は私たちの生活を変えています。",
    "機械学習はAIの重要な分野です。",
    "ディープラーニングは多くの分野で応用されています。",
    "自然言語処理は人間の言語を理解することを目指しています。",
]

KOREAN_SENTENCES = [
    "인공지능은 우리의 삶을 변화시키고 있습니다.",
    "머신러닝은 AI의 중요한 분야입니다.",
    "딥러닝은 다양한 분야에서 활용되고 있습니다.",
    "자연어 처리는 인간의 언어를 이해하는 것을 목표로 합니다.",
]

CODE_EXAMPLES = [
    '''```python
def train_model(X, y, epochs=100, lr=0.01):
    """Train a simple neural network."""
    model = NeuralNetwork()
    optimizer = Adam(lr=lr)

    for epoch in range(epochs):
        predictions = model.forward(X)
        loss = compute_loss(predictions, y)
        gradients = model.backward(loss)
        optimizer.step(gradients)

        if epoch % 10 == 0:
            print(f"Epoch {epoch}, Loss: {loss:.4f}")

    return model
```''',
    '''```python
class Transformer:
    def __init__(self, d_model=512, n_heads=8):
        self.attention = MultiHeadAttention(d_model, n_heads)
        self.ffn = FeedForward(d_model)
        self.norm1 = LayerNorm(d_model)
        self.norm2 = LayerNorm(d_model)

    def forward(self, x):
        attn_output = self.attention(x, x, x)
        x = self.norm1(x + attn_output)
        ffn_output = self.ffn(x)
        return self.norm2(x + ffn_output)
```''',
    '''```sql
SELECT
    model_name,
    AVG(accuracy) as avg_accuracy,
    COUNT(*) as num_runs
FROM experiments
WHERE created_at > '2024-01-01'
GROUP BY model_name
HAVING AVG(accuracy) > 0.9
ORDER BY avg_accuracy DESC;
```''',
]

# ============================================================================
# GENERATOR FUNCTIONS
# ============================================================================

def generate_paragraph(min_words=80, max_words=150):
    """Generate a random AI/ML paragraph."""
    num_sentences = random.randint(4, 8)
    sentences = []
    for _ in range(num_sentences):
        template = random.choice(AI_ML_SENTENCES)
        topic = random.choice(AI_ML_TOPICS)
        sentences.append(template.format(topic=topic))

    paragraph = " ".join(sentences)
    words = paragraph.split()
    if len(words) > max_words:
        words = words[:max_words]
        paragraph = " ".join(words) + "."
    return paragraph


def generate_long_paragraph(min_words=400, max_words=700):
    """Generate a very long paragraph without line breaks."""
    paragraphs = []
    current_words = 0
    while current_words < min_words:
        p = generate_paragraph(60, 100)
        paragraphs.append(p)
        current_words += len(p.split())

    result = " ".join(paragraphs)
    words = result.split()
    if len(words) > max_words:
        words = words[:max_words]
        result = " ".join(words) + "."
    return result


def generate_short_sentence():
    """Generate a very short sentence (10-20 words)."""
    templates = [
        "The {topic} model achieved state-of-the-art results.",
        "{topic} is a fundamental concept in modern AI.",
        "This approach leverages {topic} for improved performance.",
        "The {topic} technique was first introduced in 2020.",
        "{topic} remains an active area of research.",
    ]
    template = random.choice(templates)
    topic = random.choice(AI_ML_TOPICS)
    return template.format(topic=topic)


# ============================================================================
# FILE GENERATORS
# ============================================================================

def generate_large_100_pages():
    """Generate FILE 1: large_100_pages.txt - 100+ pages, 20 chapters."""
    print("Generating large_100_pages.txt...")

    content = []
    content.append("# TEST FILE: large_100_pages.txt")
    content.append("# Purpose: Test chunker with large file (100+ pages, 20 chapters)")
    content.append("# Expected: ~150 chunks, proper chapter ordering, no memory leak")
    content.append("")
    content.append("=" * 80)
    content.append("")

    for chapter_num in range(1, 21):
        chapter_title = f"CHAPTER {chapter_num}: {random.choice(AI_ML_TOPICS).title()} Fundamentals"
        content.append(chapter_title)
        content.append("=" * len(chapter_title))
        content.append("")

        # Introduction paragraph
        content.append(generate_paragraph(150, 200))
        content.append("")

        # 3-5 sections per chapter
        num_sections = random.randint(3, 5)
        for section_num in range(1, num_sections + 1):
            section_title = f"Section {chapter_num}.{section_num}: {random.choice(AI_ML_TOPICS).title()}"
            content.append(section_title)
            content.append("-" * len(section_title))
            content.append("")

            # 3-5 paragraphs per section
            num_paragraphs = random.randint(3, 5)
            for _ in range(num_paragraphs):
                content.append(generate_paragraph(100, 180))
                content.append("")

            # Sometimes add a subsection
            if random.random() > 0.6:
                subsection_title = f"{chapter_num}.{section_num}.1 Advanced Topics"
                content.append(subsection_title)
                content.append("")
                content.append(generate_paragraph(80, 120))
                content.append("")

        content.append("")

    text = "\n".join(content)

    output_path = OUTPUT_DIR / "large_100_pages.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    word_count = len(text.split())
    return output_path, word_count, len(text)


def generate_extreme_paragraphs():
    """Generate FILE 2: extreme_paragraphs.txt - mixed paragraph sizes."""
    print("Generating extreme_paragraphs.txt...")

    content = []
    content.append("# TEST FILE: extreme_paragraphs.txt")
    content.append("# Purpose: Test chunker with extreme paragraph sizes")
    content.append("# Contains: 10 tiny (1 sentence), 10 huge (500-800 words), 10 normal")
    content.append("# Expected: Proper handling of long paragraphs exceeding chunk size")
    content.append("")
    content.append("=" * 80)
    content.append("")

    # Create mixed list of paragraph types
    paragraphs = []

    # 10 tiny paragraphs
    for _ in range(10):
        paragraphs.append(("tiny", generate_short_sentence()))

    # 10 huge paragraphs
    for _ in range(10):
        paragraphs.append(("huge", generate_long_paragraph(500, 800)))

    # 10 normal paragraphs
    for _ in range(10):
        paragraphs.append(("normal", generate_paragraph(100, 150)))

    # Shuffle
    random.shuffle(paragraphs)

    for i, (ptype, para) in enumerate(paragraphs, 1):
        content.append(f"[Paragraph {i} - Type: {ptype.upper()}]")
        content.append("")
        content.append(para)
        content.append("")
        content.append("")

    text = "\n".join(content)

    output_path = OUTPUT_DIR / "extreme_paragraphs.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    word_count = len(text.split())
    return output_path, word_count, len(text)


def generate_repetitive_content():
    """Generate FILE 3: repetitive_content.txt - similar but not identical content."""
    print("Generating repetitive_content.txt...")

    content = []
    content.append("# TEST FILE: repetitive_content.txt")
    content.append("# Purpose: Test fuzzy matching - similar but NOT identical paragraphs")
    content.append("# This is the HARDEST CASE for overlap detection")
    content.append("# Expected: No false positives, correct duplicate detection")
    content.append("")
    content.append("=" * 80)
    content.append("")

    # Base templates with variants
    base_templates = [
        [
            "The system processes data efficiently using advanced algorithms.",
            "The system processes information efficiently using modern algorithms.",
            "The application processes data effectively using advanced methods.",
            "The platform processes data efficiently using sophisticated algorithms.",
            "The system handles data efficiently using advanced techniques.",
        ],
        [
            "Machine learning models require large datasets for effective training.",
            "Machine learning systems require substantial datasets for effective training.",
            "ML models need large datasets for efficient training.",
            "Machine learning algorithms require extensive datasets for effective learning.",
            "Deep learning models require large datasets for effective training.",
        ],
        [
            "The neural network achieved 95% accuracy on the test set.",
            "The neural network achieved 94% accuracy on the validation set.",
            "The deep network achieved 95% accuracy on the test dataset.",
            "The neural model achieved 95% accuracy on the benchmark set.",
            "The convolutional network achieved 95% accuracy on the test set.",
        ],
        [
            "Gradient descent optimizes the loss function iteratively.",
            "Gradient descent minimizes the loss function iteratively.",
            "Stochastic gradient descent optimizes the cost function iteratively.",
            "Gradient descent optimizes the objective function iteratively.",
            "Batch gradient descent optimizes the loss function step by step.",
        ],
        [
            "Attention mechanisms allow the model to focus on relevant parts of the input.",
            "Attention mechanisms enable the model to focus on important parts of the input.",
            "Self-attention mechanisms allow the model to focus on relevant input regions.",
            "Attention layers allow the network to focus on relevant parts of the sequence.",
            "Multi-head attention mechanisms allow the model to attend to different parts.",
        ],
    ]

    # Generate document with repeated variants
    for chapter in range(1, 7):
        content.append(f"Chapter {chapter}: Repeated Concepts with Variations")
        content.append("=" * 50)
        content.append("")

        for section in range(1, 6):
            content.append(f"Section {chapter}.{section}")
            content.append("-" * 20)
            content.append("")

            # Pick random variants from different base templates
            for _ in range(5):
                template_group = random.choice(base_templates)
                variant = random.choice(template_group)

                # Add some context around the variant
                prefix = generate_paragraph(30, 50)
                suffix = generate_paragraph(30, 50)

                content.append(prefix)
                content.append("")
                content.append(variant + " " + generate_paragraph(40, 60))
                content.append("")
                content.append(suffix)
                content.append("")

            content.append("")

    text = "\n".join(content)

    output_path = OUTPUT_DIR / "repetitive_content.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    word_count = len(text.split())
    return output_path, word_count, len(text)


def generate_complex_structure():
    """Generate FILE 4: complex_structure.txt - mixed content types."""
    print("Generating complex_structure.txt...")

    content = []
    content.append("# TEST FILE: complex_structure.txt")
    content.append("# Purpose: Test handling of mixed content types")
    content.append("# Contains: Paragraphs, bullet lists, numbered lists, code blocks, tables, quotes")
    content.append("# Expected: Code blocks not split, tables preserved, lists intact")
    content.append("")
    content.append("=" * 80)
    content.append("")

    for chapter in range(1, 9):
        content.append(f"Chapter {chapter}: Complex Document Structure")
        content.append("=" * 50)
        content.append("")

        # Regular paragraph
        content.append(generate_paragraph(100, 150))
        content.append("")

        # Bullet list
        content.append("Key points to consider:")
        content.append("")
        for i in range(random.randint(5, 10)):
            point = generate_short_sentence()
            content.append(f"• {point}")
        content.append("")

        # Another paragraph
        content.append(generate_paragraph(80, 120))
        content.append("")

        # Numbered list
        content.append("Implementation steps:")
        content.append("")
        for i in range(1, random.randint(5, 8)):
            step = generate_short_sentence()
            content.append(f"{i}. {step}")
        content.append("")

        # Code block
        content.append("Here is a code example:")
        content.append("")
        content.append(random.choice(CODE_EXAMPLES))
        content.append("")

        # Table
        content.append("Table {}.1: Performance Comparison".format(chapter))
        content.append("")
        content.append("| Method          | Accuracy | Precision | Recall | F1-Score |")
        content.append("|-----------------|----------|-----------|--------|----------|")
        for method in ["Baseline", "Proposed", "SOTA"]:
            acc = random.uniform(0.85, 0.99)
            prec = random.uniform(0.85, 0.99)
            rec = random.uniform(0.85, 0.99)
            f1 = 2 * prec * rec / (prec + rec)
            content.append(f"| {method:15} | {acc:.2%}   | {prec:.2%}    | {rec:.2%} | {f1:.2%}   |")
        content.append("")

        # Quote
        author = random.choice(["Smith", "Johnson", "Williams", "Brown", "Jones"])
        year = random.randint(2020, 2024)
        content.append(f'According to {author} ({year}):')
        content.append("")
        quote = generate_paragraph(60, 100)
        content.append(f'> "{quote}"')
        content.append("")

        # Mathematical formula
        content.append("The optimization objective can be expressed as:")
        content.append("")
        formulas = [
            "L = -∑(y_i * log(p_i) + (1 - y_i) * log(1 - p_i))",
            "∇θJ(θ) = 1/m * ∑(h_θ(x_i) - y_i) * x_i",
            "attention(Q, K, V) = softmax(QK^T / √d_k) * V",
            "E = mc² where m is mass and c is the speed of light",
            "σ(x) = 1 / (1 + e^(-x)) for sigmoid activation",
        ]
        content.append(f"    {random.choice(formulas)}")
        content.append("")

        # Final paragraph
        content.append(generate_paragraph(100, 150))
        content.append("")
        content.append("")

    text = "\n".join(content)

    output_path = OUTPUT_DIR / "complex_structure.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    word_count = len(text.split())
    return output_path, word_count, len(text)


def generate_unicode_stress():
    """Generate FILE 5: unicode_stress.txt - multi-language and special characters."""
    print("Generating unicode_stress.txt...")

    content = []
    content.append("# TEST FILE: unicode_stress.txt")
    content.append("# Purpose: Test Unicode handling across multiple languages")
    content.append("# Contains: English, Vietnamese, Chinese, Japanese, Korean, math symbols, emojis")
    content.append("# Expected: Correct character counting, no encoding corruption")
    content.append("")
    content.append("=" * 80)
    content.append("")

    for chapter in range(1, 11):
        content.append(f"Chapter {chapter}: Multilingual Content Test")
        content.append("=" * 50)
        content.append("")

        # English
        content.append("## English Section")
        content.append(generate_paragraph(80, 120))
        content.append("")

        # Vietnamese
        content.append("## Phần Tiếng Việt (Vietnamese Section)")
        for _ in range(3):
            content.append(random.choice(VIETNAMESE_SENTENCES))
        content.append("")

        # Chinese
        content.append("## 中文部分 (Chinese Section)")
        for _ in range(3):
            content.append(random.choice(CHINESE_SENTENCES))
        content.append("")

        # Japanese
        content.append("## 日本語セクション (Japanese Section)")
        for _ in range(3):
            content.append(random.choice(JAPANESE_SENTENCES))
        content.append("")

        # Korean
        content.append("## 한국어 섹션 (Korean Section)")
        for _ in range(3):
            content.append(random.choice(KOREAN_SENTENCES))
        content.append("")

        # Mathematical symbols
        content.append("## Mathematical Expressions")
        math_content = [
            "∑_{i=1}^{n} x_i = x_1 + x_2 + ... + x_n",
            "∫_a^b f(x)dx represents the definite integral",
            "∞ represents infinity in mathematics",
            "∀x ∈ ℝ: x² ≥ 0 (for all real numbers, square is non-negative)",
            "∃y: y > 0 ∧ y < 1 (there exists y between 0 and 1)",
            "√(a² + b²) = c according to Pythagorean theorem",
            "lim_{x→∞} (1 + 1/x)^x = e ≈ 2.71828",
            "α, β, γ, δ, ε, θ, λ, μ, π, σ, φ, ω are Greek letters",
        ]
        for expr in math_content:
            content.append(f"  • {expr}")
        content.append("")

        # Emojis and special punctuation
        content.append("## Special Characters and Emojis")
        special_content = [
            "🚀 Launching new AI models",
            "📊 Data analysis complete",
            "✅ All tests passed successfully",
            "⚠️ Warning: High memory usage",
            "💡 Tip: Use batch processing for large files",
            "🔬 Research findings: significant improvement observed",
            "French quotes: \u00AB text \u00BB",
            "German quotes: \u201E text \u201C",
            "\u300C Japanese brackets \u300D",
            "\u300E Korean brackets \u300F",
        ]
        for item in special_content:
            content.append(f"  {item}")
        content.append("")

        # Mixed paragraph
        content.append("## Mixed Language Paragraph")
        mixed = (
            "This paragraph mixes English with tiếng Việt có dấu, "
            "中文字符, 日本語テキスト, and 한국어 텍스트. "
            "Mathematical symbols like \u2211, \u222B, \u221E, \u2264, \u2265, \u2260, \u221A are also included. "
            "Emojis and special quotes from various languages are included above."
        )
        content.append(mixed)
        content.append("")
        content.append("")

    text = "\n".join(content)

    output_path = OUTPUT_DIR / "unicode_stress.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    word_count = len(text.split())
    return output_path, word_count, len(text)


def generate_checkpoint_killer():
    """Generate FILE 6: checkpoint_killer.txt - exactly 100 chunks."""
    print("Generating checkpoint_killer.txt...")

    # Target: exactly 100 chunks
    # Assume chunk size ~2000 chars, so we need ~200,000 chars total
    # Each chunk marker section should be ~1900 chars to account for metadata

    content = []
    content.append("# TEST FILE: checkpoint_killer.txt")
    content.append("# Purpose: Test checkpoint resume at exact chunk boundaries")
    content.append("# Contains: Exactly 100 predictable chunks with boundary markers")
    content.append("# Expected: Resume from chunk 25, 50, 75 works correctly")
    content.append("")
    content.append("=" * 80)
    content.append("")

    TARGET_CHUNK_SIZE = 1900  # chars per chunk

    for chunk_num in range(1, 101):
        marker = f"[CHUNK_BOUNDARY_{chunk_num:03d}]"
        content.append(marker)
        content.append("")

        # Generate content to fill exactly TARGET_CHUNK_SIZE chars
        current_length = len(marker) + 2  # marker + newlines
        chunk_content = []

        # Add chunk header
        header = f"=== Content Block {chunk_num} of 100 ==="
        chunk_content.append(header)
        chunk_content.append("")
        current_length += len(header) + 2

        # Fill with paragraphs until we reach target size
        while current_length < TARGET_CHUNK_SIZE - 200:  # Leave room for final paragraph
            para = generate_paragraph(100, 150)
            chunk_content.append(para)
            chunk_content.append("")
            current_length += len(para) + 2

        # Add final filler to reach exact size
        remaining = TARGET_CHUNK_SIZE - current_length - 50
        if remaining > 0:
            # Generate filler text
            filler_words = []
            while len(" ".join(filler_words)) < remaining:
                filler_words.append(random.choice(AI_ML_TOPICS))
            filler = "Additional concepts covered: " + ", ".join(filler_words[:remaining//15]) + "."
            chunk_content.append(filler)

        content.extend(chunk_content)
        content.append("")
        content.append("-" * 40)
        content.append("")

    text = "\n".join(content)

    output_path = OUTPUT_DIR / "checkpoint_killer.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    word_count = len(text.split())
    return output_path, word_count, len(text)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("STRESS TEST FILE GENERATOR")
    print("AI Translator Pro - Test Suite")
    print("=" * 60)
    print()

    results = []

    # Generate all files
    generators = [
        generate_large_100_pages,
        generate_extreme_paragraphs,
        generate_repetitive_content,
        generate_complex_structure,
        generate_unicode_stress,
        generate_checkpoint_killer,
    ]

    for generator in generators:
        path, words, chars = generator()
        estimated_chunks = chars // 2000 + 1
        results.append({
            "file": path.name,
            "words": words,
            "chars": chars,
            "size_kb": os.path.getsize(path) / 1024,
            "estimated_chunks": estimated_chunks
        })
        print(f"  ✓ {path.name}: {words:,} words, {chars:,} chars, ~{estimated_chunks} chunks")

    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print()

    total_words = sum(r["words"] for r in results)
    total_size = sum(r["size_kb"] for r in results)
    total_chunks = sum(r["estimated_chunks"] for r in results)

    print(f"Generated files in: {OUTPUT_DIR}")
    print()
    print("Summary:")
    print("-" * 60)
    print(f"{'File':<30} {'Words':>10} {'Size (KB)':>12} {'~Chunks':>10}")
    print("-" * 60)
    for r in results:
        print(f"{r['file']:<30} {r['words']:>10,} {r['size_kb']:>12.1f} {r['estimated_chunks']:>10}")
    print("-" * 60)
    print(f"{'TOTAL':<30} {total_words:>10,} {total_size:>12.1f} {total_chunks:>10}")
    print()
    print("Ready for integration testing!")


if __name__ == "__main__":
    main()
