#!/usr/bin/env python3
"""
Document Make-up Pipeline
Quy trình hoàn chỉnh để chuyển đổi tài liệu thô thành sản phẩm chuyên nghiệp
"""

import os
import sys
import subprocess
from datetime import datetime


def run_stage(stage_script, input_file, output_file, extra_args=None):
    """
    Chạy một giai đoạn của pipeline
    """
    cmd = ['python3', stage_script, input_file, output_file]
    if extra_args:
        cmd.extend(extra_args)
    
    print(f"\n{'='*80}")
    print(f"Đang chạy: {stage_script}")
    print(f"{'='*80}")
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"\n❌ Lỗi khi chạy {stage_script}")
        return False
    
    return True


def document_makeup_pipeline(input_file, output_dir="./output", title="", author=""):
    """
    Chạy toàn bộ quy trình make-up
    """
    # Tạo thư mục output nếu chưa có
    os.makedirs(output_dir, exist_ok=True)
    
    # Tạo timestamp cho các file trung gian
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Đường dẫn các file trung gian
    stage1_output = os.path.join(output_dir, f"stage1_sanitized_{timestamp}.docx")
    stage2_output = os.path.join(output_dir, f"stage2_styled_{timestamp}.docx")
    stage3_output = os.path.join(output_dir, f"final_polished_{timestamp}.docx")
    
    print("\n" + "="*80)
    print("DOCUMENT MAKE-UP PIPELINE")
    print("="*80)
    print(f"Input file: {input_file}")
    print(f"Output directory: {output_dir}")
    print(f"Title: {title if title else '(not specified)'}")
    print(f"Author: {author if author else '(not specified)'}")
    
    # Stage 1: Sanitization
    if not run_stage('stage1_sanitization.py', input_file, stage1_output):
        return False
    
    # Stage 2: Styling
    if not run_stage('stage2_styling.py', stage1_output, stage2_output):
        return False
    
    # Stage 3: Polishing
    extra_args = []
    if title:
        extra_args.append(title)
    if author:
        extra_args.append(author)
    
    if not run_stage('stage3_polishing.py', stage2_output, stage3_output, extra_args):
        return False
    
    print("\n" + "="*80)
    print("✅ HOÀN THÀNH TOÀN BỘ QUY TRÌNH MAKE-UP")
    print("="*80)
    print(f"\nFile cuối cùng: {stage3_output}")
    print("\nCác file trung gian (có thể xóa nếu không cần):")
    print(f"  - {stage1_output}")
    print(f"  - {stage2_output}")
    
    return True


def main():
    """
    Hàm chính
    """
    if len(sys.argv) < 2:
        print("Cách sử dụng:")
        print("  python document_makeup_pipeline.py <input.docx> [output_dir] [title] [author]")
        print("\nVí dụ:")
        print("  python document_makeup_pipeline.py input.docx ./output 'Hoàng Tử Bé' 'Antoine de Saint-Exupéry'")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./output"
    title = sys.argv[3] if len(sys.argv) > 3 else ""
    author = sys.argv[4] if len(sys.argv) > 4 else ""
    
    # Kiểm tra file input tồn tại
    if not os.path.exists(input_file):
        print(f"❌ Lỗi: File không tồn tại: {input_file}")
        sys.exit(1)
    
    # Chạy pipeline
    success = document_makeup_pipeline(input_file, output_dir, title, author)
    
    if success:
        print("\n🎉 Tài liệu đã được make-up thành công!")
        sys.exit(0)
    else:
        print("\n❌ Có lỗi xảy ra trong quá trình make-up")
        sys.exit(1)


if __name__ == "__main__":
    main()
