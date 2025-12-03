"""Scheduled PDF generation and upload jobs."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta
from src.workflows.pdf_form_orchestrator import PDFFormOrchestrator
from src.utils.config import AppConfig
from loguru import logger
from pathlib import Path


class PDFScheduler:
    """Manage scheduled PDF generation jobs."""

    def __init__(self, config: AppConfig):
        """Initialize PDF scheduler.

        Args:
            config: Application configuration
        """
        self.config = config

        # Configure job store (persist schedule to SQLite)
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=f'sqlite:///{Path(__file__).parent.parent.parent / "data" / "scheduler.db"}'
            )
        }

        self.scheduler = BackgroundScheduler(jobstores=jobstores)
        self.orchestrator = PDFFormOrchestrator(config)

    def start(self):
        """Start the scheduler."""
        logger.info("Starting PDF generation scheduler...")

        # Add scheduled jobs
        self._add_jobs()

        self.scheduler.start()
        logger.info("✓ Scheduler started")

    def _add_jobs(self):
        """Add scheduled jobs."""
        # Daily job: Generate PDFs for yesterday's visits
        self.scheduler.add_job(
            func=self._daily_pdf_generation,
            trigger=CronTrigger(hour=1, minute=0),  # 1:00 AM daily
            id='daily_pdf_generation',
            name='Daily PDF Generation',
            replace_existing=True
        )
        logger.info("Added job: Daily PDF Generation (1:00 AM)")

        # Weekly job: Generate PDFs for past week
        self.scheduler.add_job(
            func=self._weekly_pdf_generation,
            trigger=CronTrigger(day_of_week='mon', hour=2, minute=0),  # Monday 2:00 AM
            id='weekly_pdf_generation',
            name='Weekly PDF Generation',
            replace_existing=True
        )
        logger.info("Added job: Weekly PDF Generation (Monday 2:00 AM)")

    def _daily_pdf_generation(self):
        """Generate PDFs for yesterday's visits."""
        logger.info("=" * 80)
        logger.info("DAILY PDF GENERATION JOB STARTED")
        logger.info("=" * 80)

        # Calculate date range (yesterday)
        yesterday = (datetime.now() - timedelta(days=1)).date()

        try:
            results = self.orchestrator.process_date_range(
                start_date=yesterday,
                end_date=yesterday,
                form_types=['progress_note', 'prescription_form']
            )

            logger.info(f"Daily job completed: {results}")

            # Send notification if configured
            self._send_completion_notification(results, "Daily")

        except Exception as e:
            logger.error(f"Daily job failed: {e}")
            self._send_error_notification(str(e), "Daily")

    def _weekly_pdf_generation(self):
        """Generate PDFs for past week."""
        logger.info("=" * 80)
        logger.info("WEEKLY PDF GENERATION JOB STARTED")
        logger.info("=" * 80)

        # Calculate date range (past 7 days)
        end_date = (datetime.now() - timedelta(days=1)).date()
        start_date = end_date - timedelta(days=7)

        try:
            results = self.orchestrator.process_date_range(
                start_date=start_date,
                end_date=end_date,
                form_types=['intake_form', 'progress_note', 'prescription_form']
            )

            logger.info(f"Weekly job completed: {results}")

            # Send notification
            self._send_completion_notification(results, "Weekly")

        except Exception as e:
            logger.error(f"Weekly job failed: {e}")
            self._send_error_notification(str(e), "Weekly")

    def _send_completion_notification(self, results: dict, job_type: str):
        """Send completion notification (email/webhook).

        Args:
            results: Job results dictionary
            job_type: Type of job (Daily/Weekly)
        """
        # TODO: Implement email/Slack notification
        logger.info(f"{job_type} job notification: {results}")

    def _send_error_notification(self, error: str, job_type: str):
        """Send error notification.

        Args:
            error: Error message
            job_type: Type of job (Daily/Weekly)
        """
        # TODO: Implement error alerting
        logger.error(f"{job_type} job error notification: {error}")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    def run_manual_job(self, start_date: str, end_date: str, form_types: list):
        """Run manual PDF generation job.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            form_types: List of form types to generate

        Returns:
            Job results dictionary
        """
        logger.info(f"Manual job: {start_date} to {end_date}, forms: {form_types}")

        results = self.orchestrator.process_date_range(
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            form_types=form_types
        )

        return results
