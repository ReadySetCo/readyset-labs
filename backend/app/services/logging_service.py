# -*- coding: utf-8 -*-
"""
Persistent Logging Configuration for Brand Intelligence Scraper.
Logs are written to both console and file for later analysis.
"""
import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logging(session_id: int = None) -> logging.Logger:
    """
    Configure logging to write to both console and file.
    
    Args:
        session_id: Optional session ID to include in log filename
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if session_id:
        log_filename = f"session_{session_id}_{timestamp}.log"
    else:
        log_filename = f"scraper_{timestamp}.log"
    
    log_path = log_dir / log_filename
    
    # Create logger
    logger = logging.getLogger("scraper")
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    logger.handlers = []
    
    # File handler - detailed logging
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Console handler - info and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # Log startup
    logger.info(f"=== Logging initialized: {log_path} ===")
    
    return logger


# Global logger instance
_logger = None

def get_logger() -> logging.Logger:
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


def log_research_start(session_id: int, brand_name: str):
    """Log the start of a research session."""
    logger = get_logger()
    logger.info("=" * 60)
    logger.info(f"RESEARCH SESSION STARTED")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Brand: {brand_name}")
    logger.info("=" * 60)


def log_scrape_result(source: str, count: int, details: dict = None):
    """Log scraping results."""
    logger = get_logger()
    logger.info(f"[SCRAPE] {source}: {count} items")
    if details:
        for key, value in details.items():
            logger.debug(f"         {key}: {value}")


def log_analysis_result(analysis_type: str, success: bool, details: dict = None):
    """Log analysis results."""
    logger = get_logger()
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"[ANALYSIS] {analysis_type}: {status}")
    if details:
        for key, value in details.items():
            logger.debug(f"           {key}: {value}")


def log_error(component: str, error: str, details: dict = None):
    """Log an error."""
    logger = get_logger()
    logger.error(f"[ERROR] {component}: {error}")
    if details:
        for key, value in details.items():
            logger.error(f"        {key}: {value}")


def log_ad_library_result(brand: str, ads_found: int, video_count: int, image_count: int):
    """Log Ad Library scraping results."""
    logger = get_logger()
    logger.info(f"[AD_LIBRARY] {brand}")
    logger.info(f"             Total ads: {ads_found}")
    logger.info(f"             Videos: {video_count}, Images: {image_count}")


def log_video_analysis(library_id: str, has_transcription: bool, has_scenes: bool, dimensions_count: int):
    """Log video analysis results."""
    logger = get_logger()
    trans = "Y" if has_transcription else "N"
    scenes = "Y" if has_scenes else "N"
    logger.debug(f"[VIDEO] {library_id}: trans:{trans} scenes:{scenes} dims:{dimensions_count}")


def log_session_complete(session_id: int, total_data: int, insights_generated: bool):
    """Log session completion."""
    logger = get_logger()
    logger.info("=" * 60)
    logger.info(f"SESSION COMPLETE: {session_id}")
    logger.info(f"Total data points: {total_data}")
    logger.info(f"Insights generated: {'Yes' if insights_generated else 'No'}")
    logger.info("=" * 60)


# Also create a daily log that appends all sessions
def get_daily_logger() -> logging.Logger:
    """Get a logger that appends to a daily log file."""
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime("%Y%m%d")
    daily_log = log_dir / f"daily_{today}.log"
    
    logger = logging.getLogger("daily")
    logger.setLevel(logging.INFO)
    
    # Check if handler already exists
    if not logger.handlers:
        handler = logging.FileHandler(daily_log, encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(handler)
    
    return logger
