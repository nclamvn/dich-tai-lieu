#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Job Management CLI - Command-line interface for batch job management

Usage:
    python scripts/job_cli.py create --input file.txt --output translated.txt
    python scripts/job_cli.py list
    python scripts/job_cli.py status <job_id>
    python scripts/job_cli.py process
    python scripts/job_cli.py cancel <job_id>
"""

import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.job_queue import JobQueue, JobStatus, JobPriority
from core.batch_processor import BatchProcessor, run_batch_processor


def format_timestamp(ts: Optional[float]) -> str:
    """Format timestamp for display"""
    if ts is None:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def format_duration(start: Optional[float], end: Optional[float]) -> str:
    """Format duration"""
    if start is None or end is None:
        return "-"
    duration = end - start
    if duration < 60:
        return f"{duration:.1f}s"
    elif duration < 3600:
        return f"{duration/60:.1f}m"
    else:
        return f"{duration/3600:.1f}h"


def cmd_create(args):
    """Create a new translation job"""
    queue = JobQueue()

    # Resolve paths
    input_file = Path(args.input).resolve()
    output_file = Path(args.output).resolve()

    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return 1

    # Parse priority
    priority_map = {
        'low': JobPriority.LOW,
        'normal': JobPriority.NORMAL,
        'high': JobPriority.HIGH,
        'urgent': JobPriority.URGENT,
        'critical': JobPriority.CRITICAL
    }
    priority = priority_map.get(args.priority.lower(), JobPriority.NORMAL)

    # Create job
    job = queue.create_job(
        job_name=args.name or input_file.stem,
        input_file=str(input_file),
        output_file=str(output_file),
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        priority=priority,
        provider=args.provider,
        model=args.model,
        domain=args.domain,
        glossary=args.glossary,
        concurrency=args.concurrency,
        chunk_size=args.chunk_size,
        input_format=input_file.suffix[1:] if input_file.suffix else 'txt',
        output_format=args.format
    )

    print("✅ Job created successfully!")
    print(f"   Job ID: {job.job_id}")
    print(f"   Name: {job.job_name}")
    print(f"   Priority: {job.priority}")
    print(f"   Input: {job.input_file}")
    print(f"   Output: {job.output_file}")
    print(f"   Languages: {job.source_lang} → {job.target_lang}")
    print(f"\nRun 'python scripts/job_cli.py process' to start processing.")

    return 0


def cmd_list(args):
    """List all jobs"""
    queue = JobQueue()

    # Get jobs
    if args.status:
        jobs = queue.list_jobs(status=args.status, limit=args.limit)
    else:
        jobs = queue.list_jobs(limit=args.limit)

    if not jobs:
        print("No jobs found.")
        return 0

    # Print header
    print("\n" + "="*120)
    print(f"{'JOB ID':<12} {'NAME':<25} {'STATUS':<12} {'PRIORITY':<10} {'PROGRESS':<10} {'CREATED':<20}")
    print("="*120)

    # Print jobs
    for job in jobs:
        progress = f"{job.progress*100:.1f}%" if job.progress > 0 else "-"
        created = format_timestamp(job.created_at)

        print(f"{job.job_id:<12} {job.job_name:<25} {job.status:<12} "
              f"{job.priority:<10} {progress:<10} {created:<20}")

    print("="*120)
    print(f"Total: {len(jobs)} jobs")

    # Show stats
    if args.stats:
        print("\n📊 Queue Statistics:")
        stats = queue.get_queue_stats()
        for status, count in stats.items():
            if count > 0:
                print(f"   {status}: {count}")

    return 0


def cmd_status(args):
    """Show detailed job status"""
    queue = JobQueue()

    job = queue.get_job(args.job_id)
    if not job:
        print(f"❌ Job not found: {args.job_id}")
        return 1

    # Print job details
    print("\n" + "="*70)
    print(f"📋 JOB: {job.job_name}")
    print("="*70)

    print(f"\n🆔 Identification:")
    print(f"   Job ID: {job.job_id}")
    print(f"   Name: {job.job_name}")
    print(f"   Status: {job.status}")
    print(f"   Priority: {job.priority}")

    print(f"\n📂 Files:")
    print(f"   Input: {job.input_file}")
    print(f"   Output: {job.output_file}")
    print(f"   Formats: {job.input_format} → {job.output_format}")

    print(f"\n🌐 Translation:")
    print(f"   Languages: {job.source_lang} → {job.target_lang}")
    print(f"   Provider: {job.provider}")
    print(f"   Model: {job.model}")
    print(f"   Domain: {job.domain or 'default'}")
    print(f"   Glossary: {job.glossary or 'none'}")

    print(f"\n📊 Progress:")
    print(f"   Overall: {job.progress*100:.1f}%")
    print(f"   Chunks: {job.completed_chunks}/{job.total_chunks}")
    print(f"   Failed: {job.failed_chunks}")

    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        print(f"\n💎 Quality:")
        print(f"   Avg Quality Score: {job.avg_quality_score:.2f}")
        print(f"   Cost (est.): ${job.total_cost_usd:.4f}")
        print(f"   TM Hits: {job.tm_hits}")
        print(f"   Cache Hits: {job.cache_hits}")

    print(f"\n⏱️  Timing:")
    print(f"   Created: {format_timestamp(job.created_at)}")
    print(f"   Started: {format_timestamp(job.started_at)}")
    print(f"   Completed: {format_timestamp(job.completed_at)}")
    if job.started_at and job.completed_at:
        duration = format_duration(job.started_at, job.completed_at)
        print(f"   Duration: {duration}")

    if job.error_message:
        print(f"\n❌ Error:")
        print(f"   {job.error_message[:200]}")
        print(f"   Retry Count: {job.retry_count}/{job.max_retries}")

    print("="*70 + "\n")

    return 0


def cmd_cancel(args):
    """Cancel a job"""
    queue = JobQueue()

    if queue.cancel_job(args.job_id):
        print(f"✅ Job cancelled: {args.job_id}")
        return 0
    else:
        print(f"❌ Cannot cancel job: {args.job_id}")
        print("   (Job may be running or already completed)")
        return 1


def cmd_delete(args):
    """Delete a job"""
    queue = JobQueue()

    job = queue.get_job(args.job_id)
    if not job:
        print(f"❌ Job not found: {args.job_id}")
        return 1

    # Confirm deletion
    if not args.force:
        response = input(f"Delete job '{job.job_name}' ({args.job_id})? [y/N] ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0

    if queue.delete_job(args.job_id):
        print(f"✅ Job deleted: {args.job_id}")
        return 0
    else:
        print(f"❌ Cannot delete job: {args.job_id}")
        print("   (Only completed/failed/cancelled jobs can be deleted)")
        return 1


def cmd_process(args):
    """Process jobs from queue"""
    queue = JobQueue()

    print("🚀 Starting batch processor...")
    print(f"   Max concurrent jobs: {args.concurrent}")
    print(f"   Continuous mode: {not args.once}")

    # Run processor
    try:
        asyncio.run(run_batch_processor(
            queue=queue,
            max_concurrent_jobs=args.concurrent,
            enable_scheduler=True
        ))
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")

    return 0


def cmd_stats(args):
    """Show queue statistics"""
    queue = JobQueue()

    stats = queue.get_queue_stats()

    print("\n📊 QUEUE STATISTICS")
    print("="*50)

    # Status breakdown
    print("\n📋 By Status:")
    status_order = [
        JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING,
        JobStatus.PAUSED, JobStatus.RETRYING,
        JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED
    ]

    for status in status_order:
        count = stats.get(status, 0)
        if count > 0:
            bar = "█" * min(count, 40)
            print(f"   {status:<12} {count:>4}  {bar}")

    print(f"\n   {'TOTAL':<12} {stats['total']:>4}")
    print("="*50)

    # Recent jobs
    recent_jobs = queue.list_jobs(limit=5)
    if recent_jobs:
        print("\n📅 Recent Jobs:")
        for job in recent_jobs:
            status_icon = {
                JobStatus.COMPLETED: "✅",
                JobStatus.FAILED: "❌",
                JobStatus.RUNNING: "⏳",
                JobStatus.PENDING: "⏸️",
                JobStatus.CANCELLED: "🚫"
            }.get(job.status, "❓")

            print(f"   {status_icon} {job.job_name[:30]:<30} ({job.status})")

    return 0


def cmd_cleanup(args):
    """Cleanup old jobs"""
    queue = JobQueue()

    # Confirm cleanup
    if not args.force:
        response = input(f"Delete completed/failed jobs older than {args.days} days? [y/N] ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0

    deleted = queue.cleanup_old_jobs(days=args.days)
    print(f"✅ Deleted {deleted} old jobs")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Job Management CLI for Translation System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new translation job')
    create_parser.add_argument('--input', '-i', required=True, help='Input file path')
    create_parser.add_argument('--output', '-o', required=True, help='Output file path')
    create_parser.add_argument('--name', '-n', help='Job name (default: input filename)')
    create_parser.add_argument('--source-lang', default='en', help='Source language (default: en)')
    create_parser.add_argument('--target-lang', default='vi', help='Target language (default: vi)')
    create_parser.add_argument('--priority', default='normal', choices=['low', 'normal', 'high', 'urgent', 'critical'], help='Job priority')
    create_parser.add_argument('--provider', default='openai', choices=['openai', 'anthropic'], help='AI provider')
    create_parser.add_argument('--model', default='gpt-4o-mini', help='Model name')
    create_parser.add_argument('--domain', help='Domain (finance/literature/medical/technology)')
    create_parser.add_argument('--glossary', help='Glossary name')
    create_parser.add_argument('--concurrency', type=int, default=5, help='Parallel chunks')
    create_parser.add_argument('--chunk-size', type=int, default=3000, help='Chunk size')
    create_parser.add_argument('--format', default='txt', choices=['txt', 'docx', 'pdf', 'html', 'md'], help='Output format')

    # List command
    list_parser = subparsers.add_parser('list', help='List jobs')
    list_parser.add_argument('--status', choices=[s.value for s in JobStatus], help='Filter by status')
    list_parser.add_argument('--limit', type=int, default=50, help='Max jobs to show')
    list_parser.add_argument('--stats', action='store_true', help='Show statistics')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show job status')
    status_parser.add_argument('job_id', help='Job ID')

    # Cancel command
    cancel_parser = subparsers.add_parser('cancel', help='Cancel a job')
    cancel_parser.add_argument('job_id', help='Job ID')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a job')
    delete_parser.add_argument('job_id', help='Job ID')
    delete_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process jobs from queue')
    process_parser.add_argument('--concurrent', type=int, default=1, help='Max concurrent jobs')
    process_parser.add_argument('--once', action='store_true', help='Process once and exit')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show queue statistics')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old jobs')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Delete jobs older than N days')
    cleanup_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to command handlers
    commands = {
        'create': cmd_create,
        'list': cmd_list,
        'status': cmd_status,
        'cancel': cmd_cancel,
        'delete': cmd_delete,
        'process': cmd_process,
        'stats': cmd_stats,
        'cleanup': cmd_cleanup
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
