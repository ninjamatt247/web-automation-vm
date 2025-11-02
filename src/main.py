"""Main automation script for web data transfer."""
from playwright.sync_api import sync_playwright
from src.utils.logger import logger
from src.utils.config import get_config
from src.auth.source_auth import SourceAuth
from src.auth.target_auth import TargetAuth
from src.extractors.data_extractor import DataExtractor
from src.inserters.data_inserter import DataInserter
from datetime import datetime
import sys
from pathlib import Path


def main():
    """Main automation workflow."""
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"Web Automation Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    # Load configuration
    config = get_config()

    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    logger.info("Configuration validated successfully")

    try:
        with sync_playwright() as p:
            # Launch browser
            logger.info(f"Launching browser (headless={config.headless})")
            browser = p.chromium.launch(headless=config.headless)

            # ========================================
            # STEP 1: Authenticate to Source Application
            # ========================================
            logger.info("STEP 1: Authenticating to source application")
            source_auth = SourceAuth(config, browser)

            if not source_auth.login():
                logger.error("Failed to login to source application")
                browser.close()
                sys.exit(1)

            logger.info("✓ Source authentication successful")

            # ========================================
            # STEP 2: Extract Data from Source
            # ========================================
            logger.info("STEP 2: Extracting data from source application")

            # Navigate to data section (customize as needed)
            if not source_auth.navigate_to_data_section():
                logger.error("Failed to navigate to data section")
                browser.close()
                sys.exit(1)

            # Extract data
            extractor = DataExtractor(source_auth.page)

            # Example: Extract table data
            # TODO: Customize these selectors and extraction logic
            data = extractor.extract_table_data("table.data-table")

            # Or extract custom fields
            # custom_selectors = {
            #     "field1": "#field1-selector",
            #     "field2": ".field2-class"
            # }
            # data = [extractor.extract_custom_data(custom_selectors)]

            if not data:
                logger.warning("No data extracted")
                browser.close()
                return

            logger.info(f"✓ Extracted {len(data)} records")

            # Save extracted data
            json_file = extractor.save_to_json()
            csv_file = extractor.save_to_csv()
            logger.info(f"Data saved to: {json_file}, {csv_file}")

            # ========================================
            # STEP 3: Authenticate to Target Application
            # ========================================
            logger.info("STEP 3: Authenticating to target application")
            target_auth = TargetAuth(config, browser)

            if not target_auth.login():
                logger.error("Failed to login to target application")
                browser.close()
                sys.exit(1)

            logger.info("✓ Target authentication successful")

            # ========================================
            # STEP 4: Insert Data into Target
            # ========================================
            logger.info("STEP 4: Inserting data into target application")

            # Navigate to input section
            if not target_auth.navigate_to_input_section():
                logger.error("Failed to navigate to input section")
                browser.close()
                sys.exit(1)

            # Insert data
            inserter = DataInserter(
                target_auth.page,
                retry_attempts=config.retry_attempts,
                retry_delay=config.retry_delay
            )

            # Example: Batch insert
            # TODO: Customize the add button selector
            results = inserter.insert_batch(
                data,
                add_button_selector='button[data-action="add-row"]',
                batch_size=config.batch_size
            )

            logger.info(f"✓ Insertion complete: {results}")

            # ========================================
            # STEP 5: Cleanup
            # ========================================
            logger.info("STEP 5: Cleanup and logout")

            source_auth.logout()
            target_auth.logout()
            browser.close()

            # Archive processed files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if Path(json_file).exists():
                archive_path = Path(f"/app/data/archive/{Path(json_file).stem}_{timestamp}.json")
                Path(json_file).rename(archive_path)
                logger.info(f"Archived: {archive_path}")

            # ========================================
            # Summary
            # ========================================
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info("=" * 80)
            logger.info("AUTOMATION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Start Time:     {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"End Time:       {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Duration:       {duration:.2f} seconds")
            logger.info(f"Records Extracted: {len(data)}")
            logger.info(f"Records Inserted:  {results['success']}")
            logger.info(f"Failed Inserts:    {results['failure']}")
            logger.info(f"Success Rate:      {results['success']/results['total']*100:.1f}%")
            logger.info("=" * 80)
            logger.info("✓ Automation completed successfully")
            logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("Automation interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Automation failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
