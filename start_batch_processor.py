#!/usr/bin/env python3
"""
Start batch processor for port 9000
Phase 2.0.4 - OMML testing
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.batch_processor import run_batch_processor
from core.job_queue import JobQueue

async def main():
    """Start batch processor for Phase 2.0.4"""

    # Create queue (uses default database)
    queue = JobQueue()

    print("=" * 70)
    print("🚀 Starting Batch Processor for Phase 2.0.4 Testing")
    print("=" * 70)
    print(f"   Database: {queue.db_path}")
    print(f"   Max concurrent jobs: 1")
    print(f"   Scheduler: Enabled")
    print("=" * 70)
    print()

    # Run processor
    await run_batch_processor(
        queue=queue,
        max_concurrent_jobs=1,
        enable_scheduler=True
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Batch processor stopped by user")
        sys.exit(0)
