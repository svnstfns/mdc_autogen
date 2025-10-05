"""
rule_id_allocator.py

Manages rule ID allocation within category ranges.
Ensures unique IDs are assigned and tracks used IDs across the rules directory.
"""

import os
import re
import glob
from typing import Dict, List, Set, Tuple, Optional


class RuleIDAllocator:
    """Allocates unique rule IDs within category-specific ranges."""

    DEFAULT_RANGES: Dict[str, Tuple[int, int]] = {
        "00-foundation": (100, 199),
        "01-frontend": (200, 299),
        "02-backend": (300, 399),
        "03-mobile": (400, 499),
        "04-css": (500, 599),
        "05-state": (600, 699),
        "06-db-api": (700, 799),
        "07-testing": (800, 899),
        "08-build-dev": (900, 999),
        "09-language": (1000, 1099),
        "99-other": (9000, 9999),
    }

    def __init__(self, rules_dir: str, custom_ranges: Optional[Dict[str, Tuple[int, int]]] = None):
        """
        Initialize the allocator.

        Args:
            rules_dir: Path to .cursor/rules directory
            custom_ranges: Optional custom ID ranges to override defaults
        """
        self.rules_dir = rules_dir
        self.ranges = custom_ranges if custom_ranges else self.DEFAULT_RANGES.copy()
        self.used_ids: Set[int] = set()
        self.category_ids: Dict[str, Set[int]] = {cat: set() for cat in self.ranges.keys()}
        self._scan_existing_rules()

    def _scan_existing_rules(self) -> None:
        """Scan existing .mdc files to track used IDs."""
        if not os.path.isdir(self.rules_dir):
            return

        pattern = os.path.join(self.rules_dir, "**", "*.mdc")
        for path in glob.glob(pattern, recursive=True):
            filename = os.path.basename(path)
            # Extract rule_id from filename pattern: {id}-{slug}.mdc
            match = re.match(r"^(\d+)-([a-z0-9\-]+)\.mdc$", filename)
            if match:
                rule_id = int(match.group(1))
                self.used_ids.add(rule_id)
                
                # Determine category from path or ID range
                category = self._get_category_from_path(path)
                if category and category in self.category_ids:
                    self.category_ids[category].add(rule_id)

    def _get_category_from_path(self, path: str) -> Optional[str]:
        """Extract category from file path."""
        rel_path = os.path.relpath(path, self.rules_dir)
        parts = rel_path.split(os.sep)
        if len(parts) >= 2:
            # First part should be the category directory
            potential_category = parts[0]
            if potential_category in self.ranges:
                return potential_category
        return None

    def allocate_id(self, category: str) -> int:
        """
        Allocate the next available ID for a category.

        Args:
            category: Category slug (e.g., "02-backend")

        Returns:
            Next available rule ID

        Raises:
            ValueError: If category is unknown or no IDs available
        """
        if category not in self.ranges:
            raise ValueError(f"Unknown category: {category}. Valid categories: {list(self.ranges.keys())}")

        start, end = self.ranges[category]
        category_used = self.category_ids.get(category, set())

        # Find first available ID in range
        for rule_id in range(start, end + 1):
            if rule_id not in self.used_ids and rule_id not in category_used:
                # Reserve the ID
                self.used_ids.add(rule_id)
                self.category_ids[category].add(rule_id)
                return rule_id

        raise ValueError(f"No available IDs in range {start}-{end} for category {category}")

    def allocate_multiple(self, category: str, count: int) -> List[int]:
        """
        Allocate multiple IDs for a category.

        Args:
            category: Category slug
            count: Number of IDs to allocate

        Returns:
            List of allocated rule IDs

        Raises:
            ValueError: If not enough IDs available
        """
        if category not in self.ranges:
            raise ValueError(f"Unknown category: {category}")

        start, end = self.ranges[category]
        available = (end - start + 1) - len(self.category_ids.get(category, set()))

        if available < count:
            raise ValueError(
                f"Cannot allocate {count} IDs for category {category}. "
                f"Only {available} available in range {start}-{end}"
            )

        allocated = []
        for _ in range(count):
            allocated.append(self.allocate_id(category))
        return allocated

    def is_id_available(self, rule_id: int, category: Optional[str] = None) -> bool:
        """
        Check if a specific ID is available.

        Args:
            rule_id: ID to check
            category: Optional category to verify ID is in correct range

        Returns:
            True if ID is available
        """
        if rule_id in self.used_ids:
            return False

        if category:
            if category not in self.ranges:
                return False
            start, end = self.ranges[category]
            if not (start <= rule_id <= end):
                return False

        return True

    def get_category_stats(self, category: str) -> Dict[str, int]:
        """
        Get statistics for a category's ID usage.

        Args:
            category: Category slug

        Returns:
            Dict with total, used, and available counts
        """
        if category not in self.ranges:
            raise ValueError(f"Unknown category: {category}")

        start, end = self.ranges[category]
        total = end - start + 1
        used = len(self.category_ids.get(category, set()))
        available = total - used

        return {
            "total": total,
            "used": used,
            "available": available,
            "range_start": start,
            "range_end": end,
        }

    def get_all_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics for all categories."""
        return {cat: self.get_category_stats(cat) for cat in self.ranges.keys()}


def allocate_rule_id(rules_dir: str, category: str, custom_ranges: Optional[Dict[str, Tuple[int, int]]] = None) -> int:
    """
    Convenience function to allocate a single rule ID.

    Args:
        rules_dir: Path to .cursor/rules directory
        category: Category slug
        custom_ranges: Optional custom ID ranges

    Returns:
        Allocated rule ID
    """
    allocator = RuleIDAllocator(rules_dir, custom_ranges)
    return allocator.allocate_id(category)
