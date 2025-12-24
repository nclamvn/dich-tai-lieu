#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo Export Module - Test các tính năng export
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.export import ExportConfig, UniversalExporter, create_comparison_document


def main():
    """Demo export module"""
    print("=" * 70)
    print("AI TRANSLATOR PRO - EXPORT MODULE DEMO".center(70))
    print("=" * 70)

    # Sample Vietnamese translated text
    sample_text = """
# Chương 1: Giới Thiệu về Trí Tuệ Nhân Tạo

Trí tuệ nhân tạo (AI) đang thay đổi thế giới theo những cách mà chúng ta chưa từng tưởng tượng được.

## Các Tính Năng Chính

Hệ thống dịch thuật AI chuyên nghiệp của chúng tôi hỗ trợ nhiều định dạng xuất:

* **DOCX**: Định dạng đầy đủ với styles chuyên nghiệp
* **PDF**: Bố cục chuyên nghiệp sử dụng ReportLab
* **HTML**: Sẵn sàng cho web với styles nhúng
* **Markdown**: Cho tài liệu kỹ thuật
* **Plain Text**: Tương thích toàn cầu

## Ví Dụ Code

```python
def translate(text):
    # Logic dịch thuật nâng cao
    result = translator.translate(text)
    return result
```

### Chỉ Số Chất Lượng

Chất lượng dịch thuật được đo lường qua nhiều chỉ số:

1. Phân tích tỷ lệ độ dài
2. Kiểm tra tính đầy đủ
3. Tính nhất quán thuật ngữ
4. Xác thực ngữ pháp

> "Bản dịch tốt nhất là bản dịch vô hình - nó đọc như thể được viết gốc bằng ngôn ngữ đích."

## Kết Luận

Module export này cung cấp khả năng tạo tài liệu chất lượng chuyên nghiệp cho mọi nhu cầu dịch thuật của bạn.
"""

    # Create output directory
    output_dir = Path("data/export_demo")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Initialize exporter with custom config
    config = ExportConfig(
        title="Demo Dịch Thuật AI",
        author="AI Translator Pro",
        subject="Demo Tính Năng Export",
        keywords=["dịch thuật", "AI", "export", "demo"],
        add_header=True,
        add_footer=True,
        add_page_numbers=True,
        detect_headers=True,
        preserve_formatting=True
    )

    exporter = UniversalExporter(config)

    print(f"\n📦 Formats hỗ trợ: {', '.join(exporter.supported_formats)}")
    print(f"📁 Thư mục output: {output_dir.absolute()}")
    print("-" * 70)

    # Export to different formats
    formats_to_test = ['docx', 'pdf', 'html', 'md', 'txt']

    success_count = 0
    for format in formats_to_test:
        output_file = output_dir / f"demo_vietnamese.{format}"
        print(f"\n📄 Đang export sang {format.upper()}...", end=" ")

        try:
            if exporter.export(sample_text, str(output_file), format):
                file_size = output_file.stat().st_size / 1024  # KB
                print(f"✅ Thành công! ({file_size:.1f} KB)")
                print(f"   └─ {output_file}")
                success_count += 1
            else:
                print("❌ Thất bại")
        except Exception as e:
            print(f"❌ Lỗi: {e}")

    # Create comparison document
    print("\n" + "-" * 70)
    print("\n📊 Tạo document so sánh (Original vs Translated)...", end=" ")

    original_text = """
# Chapter 1: Introduction to Artificial Intelligence

Artificial Intelligence (AI) is changing the world in ways we never imagined.

## Key Features

Our professional AI translation system supports multiple export formats...
"""

    comparison_file = output_dir / "comparison_side_by_side.docx"
    try:
        if create_comparison_document(
            original_text,
            sample_text,
            str(comparison_file),
            'docx',
            side_by_side=True
        ):
            file_size = comparison_file.stat().st_size / 1024
            print(f"✅ Thành công! ({file_size:.1f} KB)")
            print(f"   └─ {comparison_file}")
            success_count += 1
        else:
            print("❌ Thất bại")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

    # Summary
    print("\n" + "=" * 70)
    print(f"✅ Hoàn thành! {success_count}/{len(formats_to_test) + 1} exports thành công")
    print(f"📂 Kiểm tra thư mục: {output_dir.absolute()}")
    print("=" * 70)

    # List all created files
    created_files = list(output_dir.glob("*"))
    if created_files:
        print("\n📋 Files đã tạo:")
        for file in created_files:
            size_kb = file.stat().st_size / 1024
            print(f"   • {file.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Đã hủy bởi người dùng")
    except Exception as e:
        print(f"\n\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
