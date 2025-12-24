#!/usr/bin/env python3
"""
Batch Queue CLI
AI Publisher Pro - Batch Queue System

Command-line interface for batch document translation.

Usage:
    python -m core.batch_queue.batch_cli add document1.pdf document2.pdf
    python -m core.batch_queue.batch_cli start
    python -m core.batch_queue.batch_cli status
    python -m core.batch_queue.batch_cli list
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import List

from .batch_queue import BatchQueue, QueueConfig, create_batch_queue
from .batch_job import BatchJob, JobStatus, JobPriority


def print_header():
    """Print header"""
    print("""
+======================================================================+
|                                                                      |
|             AI Publisher Pro - Batch Queue                           |
|                                                                      |
+======================================================================+
""")


def print_job(job: BatchJob, verbose: bool = False):
    """Print job details"""
    status_icons = {
        JobStatus.PENDING: "[PENDING]",
        JobStatus.PREPARING: "[PREPARING]",
        JobStatus.PROCESSING: "[PROCESSING]",
        JobStatus.PAUSED: "[PAUSED]",
        JobStatus.COMPLETED: "[COMPLETED]",
        JobStatus.FAILED: "[FAILED]",
        JobStatus.CANCELLED: "[CANCELLED]",
    }

    icon = status_icons.get(job.status, "[?]")
    progress = job.progress.progress_percent

    print(f"  {icon} [{job.id}] {job.name}")
    print(f"     Status: {job.status.value} | Progress: {progress:.1f}%")
    print(f"     Pages: {job.progress.completed_pages}/{job.progress.total_pages}")
    print(f"     Cost: ${job.progress.cost_incurred:.4f}")

    if verbose:
        print(f"     Input: {job.input_path}")
        print(f"     Mode: {job.translation_mode}")
        print(f"     Lang: {job.source_lang} -> {job.target_lang}")
        if job.error_message:
            print(f"     Error: {job.error_message}")
    print()


def cmd_add(args, queue: BatchQueue):
    """Add jobs to queue"""
    print(f"\n[+] Adding {len(args.files)} document(s) to queue...\n")

    for file_path in args.files:
        path = Path(file_path)
        if not path.exists():
            print(f"  [X] File not found: {file_path}")
            continue

        try:
            job = queue.add_job(
                input_path=str(path),
                source_lang=args.source,
                target_lang=args.target,
                translation_mode=args.mode,
                output_format=args.format,
                priority=JobPriority[args.priority.upper()]
            )

            print(f"  [OK] Added: {job.name} [{job.id}]")
            print(f"     Mode: {job.translation_mode} | Priority: {job.priority.name}")

        except Exception as e:
            print(f"  [X] Error adding {file_path}: {e}")

    print(f"\n[i] Queue size: {len(queue.get_queue())} jobs")


def cmd_start(args, queue: BatchQueue):
    """Start processing queue"""
    print("\n[>] Starting batch processing...\n")

    # Set up progress display
    def on_progress(job: BatchJob):
        progress = job.progress.progress_percent
        pages = f"{job.progress.completed_pages}/{job.progress.total_pages}"
        rate = job.progress.pages_per_minute
        print(f"\r  [{job.name}] {progress:.1f}% ({pages}) - {rate:.1f} pages/min    ", end="")

    def on_complete(job: BatchJob):
        print(f"\n  [OK] Completed: {job.name}")
        print(f"     Output: {job.output_path}")
        print(f"     Cost: ${job.progress.cost_incurred:.4f}")

    def on_error(job: BatchJob, error: str):
        print(f"\n  [X] Failed: {job.name}")
        print(f"     Error: {error}")

    def on_empty():
        print("\n\n[OK] All jobs completed!")

    queue.on_job_progress = on_progress
    queue.on_job_complete = on_complete
    queue.on_job_error = on_error
    queue.on_queue_empty = on_empty

    # Start queue
    queue.start()

    # Wait for completion
    try:
        while queue._is_running:
            time.sleep(1)
            if len(queue.get_queue()) == 0 and len(queue.get_processing()) == 0:
                break
    except KeyboardInterrupt:
        print("\n\n[!] Stopping queue...")
        queue.stop()

    # Print summary
    summary = queue.get_summary()
    print(f"\n[i] Summary:")
    print(f"   Completed: {summary.completed_jobs}/{summary.total_jobs}")
    print(f"   Total cost: ${summary.total_cost:.4f}")


def cmd_status(args, queue: BatchQueue):
    """Show queue status"""
    status = queue.get_status()
    summary = status["summary"]

    print("\n[i] Queue Status")
    print("=" * 50)
    print(f"  Running: {'Yes' if status['is_running'] else 'No'}")
    print(f"  Paused: {'Yes' if status['is_paused'] else 'No'}")
    print(f"  Queue size: {status['queue_size']}")
    print(f"  Processing: {status['processing_count']}")
    print()
    print("[i] Summary:")
    print(f"  Total jobs: {summary['total_jobs']}")
    print(f"  Pending: {summary['pending_jobs']}")
    print(f"  Completed: {summary['completed_jobs']}")
    print(f"  Failed: {summary['failed_jobs']}")
    print()
    print(f"  Total pages: {summary['total_pages']}")
    print(f"  Progress: {summary['progress_percent']:.1f}%")
    print(f"  Total cost: ${summary['total_cost']:.4f}")
    print(f"  Est. remaining: {summary['estimated_remaining_minutes']:.1f} min")


def cmd_list(args, queue: BatchQueue):
    """List all jobs"""
    print("\n[i] Job List")
    print("=" * 50)

    jobs = queue.get_all_jobs()

    if not jobs:
        print("  No jobs in queue")
        return

    # Group by status
    by_status = {}
    for job in jobs:
        status = job.status.value
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(job)

    for status, status_jobs in by_status.items():
        print(f"\n{status.upper()} ({len(status_jobs)}):")
        for job in status_jobs:
            print_job(job, verbose=args.verbose)


def cmd_cancel(args, queue: BatchQueue):
    """Cancel a job"""
    for job_id in args.job_ids:
        if queue.cancel_job(job_id):
            print(f"  [OK] Cancelled: {job_id}")
        else:
            print(f"  [X] Could not cancel: {job_id}")


def cmd_retry(args, queue: BatchQueue):
    """Retry a failed job"""
    for job_id in args.job_ids:
        if queue.retry_job(job_id):
            print(f"  [OK] Retrying: {job_id}")
        else:
            print(f"  [X] Could not retry: {job_id}")


def cmd_clear(args, queue: BatchQueue):
    """Clear completed jobs"""
    queue._store.clear_completed()
    print("  [OK] Cleared completed jobs")


def cmd_estimate(args, queue: BatchQueue):
    """Estimate batch cost"""
    estimates = queue.estimate_batch_cost()

    print("\n[i] Cost Estimate")
    print("=" * 50)
    for mode, cost in estimates.items():
        if mode != "total":
            print(f"  {mode}: ${cost:.4f}")
    print(f"\n  TOTAL: ${estimates['total']:.4f}")


def main():
    print_header()

    parser = argparse.ArgumentParser(
        description="Batch Queue CLI for AI Publisher Pro"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add documents to queue")
    add_parser.add_argument("files", nargs="+", help="PDF files or folders")
    add_parser.add_argument("-s", "--source", default="Chinese", help="Source language")
    add_parser.add_argument("-t", "--target", default="Vietnamese", help="Target language")
    add_parser.add_argument("-m", "--mode", default="balanced",
                           choices=["economy", "balanced", "quality"],
                           help="Translation mode")
    add_parser.add_argument("-f", "--format", default="docx",
                           choices=["docx", "pdf", "txt", "md"],
                           help="Output format")
    add_parser.add_argument("-p", "--priority", default="normal",
                           choices=["low", "normal", "high", "urgent"],
                           help="Job priority")

    # Start command
    subparsers.add_parser("start", help="Start processing queue")

    # Status command
    subparsers.add_parser("status", help="Show queue status")

    # List command
    list_parser = subparsers.add_parser("list", help="List all jobs")
    list_parser.add_argument("-v", "--verbose", action="store_true",
                            help="Show detailed info")

    # Cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel jobs")
    cancel_parser.add_argument("job_ids", nargs="+", help="Job IDs to cancel")

    # Retry command
    retry_parser = subparsers.add_parser("retry", help="Retry failed jobs")
    retry_parser.add_argument("job_ids", nargs="+", help="Job IDs to retry")

    # Clear command
    subparsers.add_parser("clear", help="Clear completed jobs")

    # Estimate command
    subparsers.add_parser("estimate", help="Estimate batch cost")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Create queue
    queue = create_batch_queue()

    # Execute command
    commands = {
        "add": cmd_add,
        "start": cmd_start,
        "status": cmd_status,
        "list": cmd_list,
        "cancel": cmd_cancel,
        "retry": cmd_retry,
        "clear": cmd_clear,
        "estimate": cmd_estimate,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args, queue)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
