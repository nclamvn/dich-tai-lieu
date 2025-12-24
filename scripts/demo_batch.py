#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch Processing Demo - Showcase Phase 5 features

Demonstrates:
- Job creation with different priorities
- Queue management
- Priority scheduling
- Batch processing
- Job monitoring
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.job_queue import JobQueue, JobPriority, JobStatus


def create_demo_text_files():
    """Create demo input files for testing"""
    data_dir = Path("data/input/demo_batch")
    data_dir.mkdir(exist_ok=True, parents=True)

    # Create sample texts
    samples = {
        "urgent_announcement.txt": """
URGENT ANNOUNCEMENT

Due to unforeseen circumstances, our annual meeting scheduled for next Monday
has been postponed to the following week. We apologize for any inconvenience
this may cause. All registered participants will receive a confirmation email
with the new date and time.

Thank you for your understanding.
""",
        "normal_article.txt": """
The Future of Artificial Intelligence

Artificial intelligence continues to evolve at a rapid pace, transforming
industries and reshaping how we work and live. From healthcare diagnostics
to autonomous vehicles, AI applications are becoming increasingly sophisticated
and ubiquitous.

Experts predict that the next decade will see even more dramatic advances in
machine learning, natural language processing, and computer vision. However,
these developments also raise important questions about ethics, privacy, and
the future of work.
""",
        "low_priority_notes.txt": """
Personal Notes

Remember to:
- Review the quarterly report
- Schedule team meeting
- Update project documentation
- Send thank you emails

These can be handled whenever convenient.
"""
    }

    for filename, content in samples.items():
        file_path = data_dir / filename
        file_path.write_text(content.strip(), encoding='utf-8')

    return data_dir


def demo_job_creation():
    """Demo: Create jobs with different priorities"""
    print("\n" + "="*70)
    print("DEMO 1: JOB CREATION WITH PRIORITIES")
    print("="*70)

    # Create demo files
    input_dir = create_demo_text_files()
    output_dir = Path("data/output/demo_batch")
    output_dir.mkdir(exist_ok=True, parents=True)

    queue = JobQueue()

    # Create jobs with different priorities
    jobs_config = [
        {
            "name": "Urgent Announcement Translation",
            "input": input_dir / "urgent_announcement.txt",
            "priority": JobPriority.URGENT,
            "domain": "technology"
        },
        {
            "name": "Normal Article Translation",
            "input": input_dir / "normal_article.txt",
            "priority": JobPriority.NORMAL,
            "domain": "technology"
        },
        {
            "name": "Low Priority Notes",
            "input": input_dir / "low_priority_notes.txt",
            "priority": JobPriority.LOW,
            "domain": None
        }
    ]

    created_jobs = []
    for config in jobs_config:
        output_file = output_dir / config["input"].name

        job = queue.create_job(
            job_name=config["name"],
            input_file=str(config["input"]),
            output_file=str(output_file),
            priority=config["priority"],
            domain=config["domain"],
            source_lang="en",
            target_lang="vi",
            provider="openai",
            model="gpt-4o-mini"
        )

        created_jobs.append(job)

        priority_str = {
            JobPriority.LOW: "🔵 LOW",
            JobPriority.NORMAL: "🟢 NORMAL",
            JobPriority.HIGH: "🟡 HIGH",
            JobPriority.URGENT: "🔴 URGENT",
            JobPriority.CRITICAL: "⚫ CRITICAL"
        }.get(job.priority, str(job.priority))

        print(f"\n✅ Created: {job.job_name}")
        print(f"   Job ID: {job.job_id}")
        print(f"   Priority: {priority_str}")
        print(f"   Input: {job.input_file}")
        print(f"   Output: {job.output_file}")

    return created_jobs


def demo_queue_stats():
    """Demo: Show queue statistics"""
    print("\n" + "="*70)
    print("DEMO 2: QUEUE STATISTICS")
    print("="*70)

    queue = JobQueue()
    stats = queue.get_queue_stats()

    print("\n📊 Current Queue Status:")
    print("-" * 40)

    status_icons = {
        JobStatus.PENDING: "⏸️",
        JobStatus.QUEUED: "📋",
        JobStatus.RUNNING: "⏳",
        JobStatus.PAUSED: "⏸️",
        JobStatus.RETRYING: "🔄",
        JobStatus.COMPLETED: "✅",
        JobStatus.FAILED: "❌",
        JobStatus.CANCELLED: "🚫"
    }

    for status, count in stats.items():
        if status != 'total' and count > 0:
            icon = status_icons.get(status, "❓")
            bar = "█" * min(count, 20)
            print(f"{icon} {status:<12} {count:>3}  {bar}")

    print("-" * 40)
    print(f"   {'TOTAL':<12} {stats['total']:>3}")
    print()


def demo_priority_scheduling():
    """Demo: Show priority-based scheduling"""
    print("\n" + "="*70)
    print("DEMO 3: PRIORITY-BASED SCHEDULING")
    print("="*70)

    queue = JobQueue()

    # List all pending jobs
    pending_jobs = queue.list_jobs(status=JobStatus.PENDING)

    if not pending_jobs:
        print("\n No pending jobs to schedule.")
        return

    print("\n📋 Jobs will be processed in this order (by priority):")
    print("-" * 60)

    # Sort by priority (descending) and created_at (ascending)
    sorted_jobs = sorted(
        pending_jobs,
        key=lambda j: (-j.priority, j.created_at)
    )

    for i, job in enumerate(sorted_jobs, 1):
        priority_name = {
            1: "LOW", 5: "NORMAL", 10: "HIGH",
            20: "URGENT", 50: "CRITICAL"
        }.get(job.priority, str(job.priority))

        print(f"{i}. [{priority_name:>8}] {job.job_name}")

    print()


def demo_job_details():
    """Demo: Show detailed job information"""
    print("\n" + "="*70)
    print("DEMO 4: JOB DETAILS")
    print("="*70)

    queue = JobQueue()

    # Get first job
    jobs = queue.list_jobs(limit=1)
    if not jobs:
        print("\n No jobs found.")
        return

    job = jobs[0]

    print(f"\n📋 Detailed view of job: {job.job_name}")
    print("-" * 60)

    print(f"\n🆔 ID: {job.job_id}")
    print(f"📝 Name: {job.job_name}")
    print(f"📊 Status: {job.status}")
    print(f"⚡ Priority: {job.priority}")

    print(f"\n📂 Files:")
    print(f"   Input: {job.input_file}")
    print(f"   Output: {job.output_file}")

    print(f"\n🌐 Translation:")
    print(f"   Languages: {job.source_lang} → {job.target_lang}")
    print(f"   Provider: {job.provider} / {job.model}")
    if job.domain:
        print(f"   Domain: {job.domain}")

    print(f"\n⚙️ Processing Config:")
    print(f"   Concurrency: {job.concurrency}")
    print(f"   Chunk Size: {job.chunk_size}")

    print(f"\n📊 Progress: {job.progress*100:.1f}%")

    print()


def demo_cli_usage():
    """Demo: Show CLI usage examples"""
    print("\n" + "="*70)
    print("DEMO 5: CLI USAGE EXAMPLES")
    print("="*70)

    print("""
The Job Management CLI provides powerful commands for batch processing:

1️⃣  CREATE A JOB:
   python scripts/job_cli.py create \\
       --input data/input/document.txt \\
       --output data/output/translated.txt \\
       --priority urgent \\
       --domain technology

2️⃣  LIST ALL JOBS:
   python scripts/job_cli.py list

3️⃣  CHECK JOB STATUS:
   python scripts/job_cli.py status <job_id>

4️⃣  PROCESS JOBS (Start worker):
   python scripts/job_cli.py process

5️⃣  SHOW QUEUE STATS:
   python scripts/job_cli.py stats

6️⃣  CANCEL A JOB:
   python scripts/job_cli.py cancel <job_id>

7️⃣  DELETE OLD JOBS:
   python scripts/job_cli.py cleanup --days 30

8️⃣  GET HELP:
   python scripts/job_cli.py --help
   python scripts/job_cli.py create --help

📖 For detailed documentation, see README.md Phase 5 section.
""")


def demo_benefits():
    """Demo: Explain batch processing benefits"""
    print("\n" + "="*70)
    print("PHASE 5 BENEFITS: WHY BATCH PROCESSING?")
    print("="*70)

    print("""
✨ KEY BENEFITS:

1. 🔄 QUEUE MANAGEMENT
   - Submit jobs and forget about them
   - Jobs are processed automatically in order
   - No need to manually manage translation tasks

2. ⚡ PRIORITY SCHEDULING
   - Urgent documents get translated first
   - Fair scheduling for normal priority jobs
   - Low priority jobs processed when queue is light

3. 📊 PROGRESS TRACKING
   - Real-time job status updates
   - Detailed progress information
   - Quality metrics and cost tracking

4. 🛡️ FAULT TOLERANCE
   - Automatic retry on failures
   - Jobs persist across restarts
   - Error tracking and reporting

5. 🔧 FLEXIBLE CONFIGURATION
   - Per-job settings (model, domain, glossary)
   - Multiple output formats
   - Language pair configuration

6. 📈 SCALABILITY
   - Process multiple jobs concurrently
   - Efficient resource utilization
   - Suitable for large-scale translation projects

7. 💾 PERSISTENCE
   - SQLite-based job database
   - No external dependencies (no Redis/Celery needed)
   - File-based, portable, easy to backup

8. 🎯 PRODUCTION-READY
   - Job cleanup and maintenance
   - Statistics and monitoring
   - CLI for easy automation
""")


def main():
    """Run all demos"""
    print("\n" + "🎬 "*30)
    print("PHASE 5 - BATCH PROCESSING SYSTEM DEMO")
    print("🎬 "*30)

    try:
        # Demo 1: Job creation
        created_jobs = demo_job_creation()

        # Wait a bit for effect
        time.sleep(1)

        # Demo 2: Queue stats
        demo_queue_stats()

        # Demo 3: Priority scheduling
        demo_priority_scheduling()

        # Demo 4: Job details
        demo_job_details()

        # Demo 5: CLI usage
        demo_cli_usage()

        # Demo 6: Benefits
        demo_benefits()

        # Summary
        print("\n" + "="*70)
        print("DEMO COMPLETE!")
        print("="*70)

        print(f"""
✅ Created {len(created_jobs)} demo jobs

🚀 Next Steps:

1. View all jobs:
   python scripts/job_cli.py list

2. Start processing jobs:
   python scripts/job_cli.py process

3. Monitor progress:
   python scripts/job_cli.py stats

4. Check specific job:
   python scripts/job_cli.py status <job_id>

💡 The batch processor will handle everything automatically!
   Jobs with higher priority will be processed first.
""")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
