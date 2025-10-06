"""
Enhanced logging utilities with colors and formatting.
"""

import logging
from typing import Optional
from colorama import Fore, Style, init

# Initialize colorama for cross-platform color support
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors and icons to log messages.
    """
    
    # Color mappings for different log levels
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    # Icon mappings for different log levels
    ICONS = {
        'DEBUG': '🔍',
        'INFO': '✓',
        'WARNING': '⚠',
        'ERROR': '❌',
        'CRITICAL': '🔥',
    }
    
    def format(self, record):
        """Format the log record with colors and icons."""
        # Get the color and icon for this level
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')
        
        # Format the level name with fixed width for alignment
        level_name = f"{record.levelname:<8}"
        
        # Build the formatted message
        log_fmt = f"{color}{icon} {level_name}{Style.RESET_ALL} | %(message)s"
        
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_colored_logging(log_level: str = "INFO") -> None:
    """
    Setup colored logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Get the root logger
    logger = logging.getLogger()
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler with colored formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter())
    
    # Set level and add handler
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(console_handler)


def log_section(title: str, width: int = 80) -> None:
    """
    Log a section header with decorative borders.
    
    Args:
        title: Section title
        width: Width of the section (default: 80)
    """
    border = "=" * width
    padding = (width - len(title) - 2) // 2
    centered_title = f"{' ' * padding}{title}{' ' * (width - len(title) - padding - 2)}"
    
    logging.info(f"\n{Fore.CYAN}{border}")
    logging.info(f"{Fore.CYAN}{Style.BRIGHT}{centered_title}")
    logging.info(f"{Fore.CYAN}{border}{Style.RESET_ALL}")


def log_table_row(columns: list, widths: Optional[list] = None) -> str:
    """
    Format a table row with aligned columns.
    
    Args:
        columns: List of column values
        widths: Optional list of column widths (defaults to auto-sizing)
    
    Returns:
        Formatted table row
    """
    if widths is None:
        widths = [max(len(str(col)), 15) for col in columns]
    
    formatted_cols = []
    for col, width in zip(columns, widths):
        col_str = str(col)
        # Truncate if too long, add ellipsis
        if len(col_str) > width:
            col_str = col_str[:width-3] + "..."
        formatted_cols.append(col_str.ljust(width))
    
    return " | ".join(formatted_cols)


def log_file_status(file_path: str, status: str, details: str = "", score: Optional[float] = None) -> None:
    """
    Log a file status with consistent formatting.
    
    Args:
        file_path: Path to the file
        status: Status message (e.g., "High quality", "Missing", "Updated")
        details: Optional additional details
        score: Optional quality score
    """
    # Determine color based on status
    if status.lower() in ["high quality", "created", "generated", "updated"]:
        color = Fore.GREEN
        icon = "✓"
    elif status.lower() in ["missing", "quality issues"]:
        color = Fore.YELLOW
        icon = "⚠"
    elif status.lower() in ["failed", "error"]:
        color = Fore.RED
        icon = "❌"
    else:
        color = Fore.WHITE
        icon = "•"
    
    # Truncate file path if too long
    max_path_len = 50
    if len(file_path) > max_path_len:
        display_path = "..." + file_path[-(max_path_len-3):]
    else:
        display_path = file_path.ljust(max_path_len)
    
    # Build the message
    msg_parts = [f"{color}{icon}{Style.RESET_ALL}", display_path, f"{color}{status}{Style.RESET_ALL}"]
    
    if score is not None:
        score_color = Fore.GREEN if score >= 8.0 else Fore.YELLOW if score >= 6.0 else Fore.RED
        msg_parts.append(f"({score_color}{score:.1f}/10{Style.RESET_ALL})")
    
    if details:
        msg_parts.append(f"- {details}")
    
    logging.info(" ".join(msg_parts))


def log_progress(current: int, total: int, item_name: str = "items") -> None:
    """
    Log progress with a progress indicator.
    
    Args:
        current: Current count
        total: Total count
        item_name: Name of items being processed
    """
    percentage = (current / total * 100) if total > 0 else 0
    bar_length = 40
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    
    logging.info(
        f"{Fore.CYAN}Progress: {Style.RESET_ALL}[{Fore.GREEN}{bar}{Style.RESET_ALL}] "
        f"{current}/{total} {item_name} ({percentage:.1f}%)"
    )


def log_summary(items: dict, title: str = "Summary") -> None:
    """
    Log a summary table.
    
    Args:
        items: Dictionary of summary items (key: value pairs)
        title: Title for the summary
    """
    log_section(title, 60)
    
    max_key_len = max(len(str(k)) for k in items.keys()) if items else 0
    
    for key, value in items.items():
        key_str = str(key).ljust(max_key_len)
        logging.info(f"  {Fore.CYAN}{key_str}{Style.RESET_ALL} : {Fore.WHITE}{value}{Style.RESET_ALL}")


def log_compact_list(items: list, prefix: str = "", max_items: int = 10) -> None:
    """
    Log a compact list with optional truncation.
    
    Args:
        items: List of items to log
        prefix: Optional prefix for each item
        max_items: Maximum items to show before truncating
    """
    for i, item in enumerate(items[:max_items]):
        logging.info(f"  {prefix}{item}")
    
    if len(items) > max_items:
        remaining = len(items) - max_items
        logging.info(f"  {Fore.YELLOW}... and {remaining} more{Style.RESET_ALL}")
