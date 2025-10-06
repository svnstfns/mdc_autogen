"""
Module for analyzing quality of existing MDC files.
"""

import os
import re
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from .llm_utils.models import MDCResponse
from .logging_utils import log_section, log_file_status, log_summary


class MDCQualityReport:
    """Data class for holding quality analysis results."""
    
    def __init__(self):
        self.files_analyzed = 0
        self.files_with_issues = []
        self.high_quality_files = []
        self.missing_files = []
        self.quality_scores = {}
        self.issues_by_file = {}
        
    def add_file_analysis(self, file_path: str, score: float, issues: List[str], is_high_quality: bool):
        """Add analysis results for a file."""
        self.files_analyzed += 1
        self.quality_scores[file_path] = score
        
        if issues:
            self.files_with_issues.append(file_path)
            self.issues_by_file[file_path] = issues
        
        if is_high_quality:
            self.high_quality_files.append(file_path)
    
    def add_missing_file(self, file_path: str):
        """Mark a file as missing MDC."""
        self.missing_files.append(file_path)
    
    def get_summary(self) -> str:
        """Generate a summary report."""
        summary = []
        summary.append("=" * 80)
        summary.append("MDC Quality Assessment Report")
        summary.append("=" * 80)
        summary.append(f"Total MDC files analyzed: {self.files_analyzed}")
        summary.append(f"High-quality files: {len(self.high_quality_files)}")
        summary.append(f"Files with quality issues: {len(self.files_with_issues)}")
        summary.append(f"Missing MDC files: {len(self.missing_files)}")
        summary.append("")
        
        if self.files_with_issues:
            summary.append("Files requiring updates:")
            for file_path in self.files_with_issues:
                score = self.quality_scores.get(file_path, 0.0)
                issues = self.issues_by_file.get(file_path, [])
                summary.append(f"  - {file_path} (Score: {score:.2f}/10)")
                for issue in issues:
                    summary.append(f"    • {issue}")
        
        summary.append("")
        return "\n".join(summary)


def parse_mdc_file(file_path: str) -> Optional[Dict]:
    """
    Parse an MDC file and extract its components.
    
    Args:
        file_path: Path to the MDC file
        
    Returns:
        Dictionary with parsed components or None if parsing fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n\n(.*)$', content, re.DOTALL)
        if not frontmatter_match:
            logging.warning(f"Could not parse frontmatter in {file_path}")
            return None
        
        frontmatter_raw = frontmatter_match.group(1)
        markdown_content = frontmatter_match.group(2)
        
        # Parse frontmatter fields
        description_match = re.search(r'^description:\s*(.+)$', frontmatter_raw, re.MULTILINE)
        globs_match = re.search(r'^globs:\s*(\[.*?\])$', frontmatter_raw, re.MULTILINE)
        always_apply_match = re.search(r'^alwaysApply:\s*(.+)$', frontmatter_raw, re.MULTILINE)
        
        return {
            'description': description_match.group(1).strip() if description_match else '',
            'globs': globs_match.group(1) if globs_match else '[]',
            'always_apply': always_apply_match.group(1).strip() if always_apply_match else 'false',
            'content': markdown_content,
            'file_path': file_path
        }
    except Exception as e:
        logging.error(f"Error parsing MDC file {file_path}: {e}")
        return None


def check_structure_quality(parsed_mdc: Dict) -> Tuple[float, List[str]]:
    """
    Check if MDC has proper structure.
    
    Returns:
        Tuple of (score, list of issues)
    """
    issues = []
    score = 10.0  # Start with perfect score
    
    # Check if description exists and is meaningful
    description = parsed_mdc.get('description', '')
    if not description:
        issues.append("Missing description")
        score -= 3.0
    elif len(description) < 20:
        issues.append("Description too short (< 20 characters)")
        score -= 1.5
    
    # Check globs
    globs = parsed_mdc.get('globs', '[]')
    if globs == '[]' or globs == '':
        issues.append("Missing or empty globs")
        score -= 2.0
    
    # Check always_apply
    always_apply = parsed_mdc.get('always_apply', 'false')
    if always_apply not in ['true', 'false']:
        issues.append("Invalid alwaysApply value")
        score -= 1.0
    
    return max(0, score), issues


def check_content_quality(parsed_mdc: Dict) -> Tuple[float, List[str]]:
    """
    Check the quality of markdown content.
    
    Returns:
        Tuple of (score, list of issues)
    """
    issues = []
    score = 10.0
    content = parsed_mdc.get('content', '')
    
    if not content or len(content.strip()) < 50:
        issues.append("Content is too short or empty")
        score -= 5.0
        return max(0, score), issues
    
    # Check for meaningful headers
    headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
    if len(headers) < 2:
        issues.append("Lacks proper section structure (< 2 headers)")
        score -= 2.0
    
    # Check for lists or examples (signs of detailed content)
    has_lists = bool(re.search(r'^[\*\-]\s+', content, re.MULTILINE))
    has_code_blocks = bool(re.search(r'```', content))
    
    if not has_lists and not has_code_blocks:
        issues.append("Lacks detailed examples or structured information")
        score -= 1.5
    
    # Check for generic/placeholder content
    generic_phrases = [
        'TODO', 'FIXME', 'placeholder', 'example content',
        'lorem ipsum', 'TBD', 'to be determined'
    ]
    for phrase in generic_phrases:
        if phrase.lower() in content.lower():
            issues.append(f"Contains placeholder/generic content: '{phrase}'")
            score -= 2.0
            break
    
    return max(0, score), issues


def check_precision_and_focus(parsed_mdc: Dict) -> Tuple[float, List[str]]:
    """
    Check if content is precise and focused.
    
    Returns:
        Tuple of (score, list of issues)
    """
    issues = []
    score = 10.0
    content = parsed_mdc.get('content', '')
    description = parsed_mdc.get('description', '')
    
    # Check content length - should be informative but not excessively long
    content_length = len(content)
    lines = content.split('\n')
    line_count = len(lines)
    
    if content_length > 10000:
        issues.append(f"Content too long ({content_length} chars, {line_count} lines) - may lack focus")
        score -= 2.0
    elif content_length > 5000:
        issues.append(f"Content quite long ({content_length} chars) - consider if all is necessary")
        score -= 1.0
    
    # Check for overly generic descriptions
    generic_descriptions = [
        'this file', 'this module', 'provides functionality',
        'contains code', 'implements features'
    ]
    desc_lower = description.lower()
    generic_count = sum(1 for phrase in generic_descriptions if phrase in desc_lower)
    if generic_count >= 2:
        issues.append("Description appears generic/vague")
        score -= 1.5
    
    # Check for repeated words in content (sign of poor quality)
    words = re.findall(r'\b\w+\b', content.lower())
    if len(words) > 50:
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Only check longer words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Check if any word appears excessively
        max_freq = max(word_freq.values()) if word_freq else 0
        total_words = len(words)
        if max_freq > total_words * 0.1:  # More than 10% of content is one word
            issues.append("Content has excessive word repetition")
            score -= 2.0
    
    return max(0, score), issues


def analyze_mdc_quality(file_path: str) -> Tuple[float, List[str], bool]:
    """
    Comprehensive quality analysis of an MDC file.
    
    Args:
        file_path: Path to the MDC file
        
    Returns:
        Tuple of (overall_score, issues, is_high_quality)
    """
    parsed = parse_mdc_file(file_path)
    if not parsed:
        return 0.0, ["Failed to parse file"], False
    
    # Run all quality checks
    structure_score, structure_issues = check_structure_quality(parsed)
    content_score, content_issues = check_content_quality(parsed)
    precision_score, precision_issues = check_precision_and_focus(parsed)
    
    # Calculate weighted overall score
    overall_score = (structure_score * 0.3 + content_score * 0.4 + precision_score * 0.3)
    
    # Combine all issues
    all_issues = structure_issues + content_issues + precision_issues
    
    # Consider high quality if score is above 8.0 and has at most 1 minor issue
    is_high_quality = overall_score >= 8.0 and len(all_issues) <= 1
    
    return overall_score, all_issues, is_high_quality


def scan_existing_mdc_files(rules_dir: str, expected_files: List[str]) -> MDCQualityReport:
    """
    Scan existing MDC files and assess their quality.
    
    Args:
        rules_dir: Path to .cursor/rules directory
        expected_files: List of files that should have MDC documentation
        
    Returns:
        MDCQualityReport with analysis results
    """
    report = MDCQualityReport()
    
    if not os.path.exists(rules_dir):
        logging.info(f"Rules directory {rules_dir} does not exist")
        # Mark all expected files as missing
        for file_path in expected_files:
            report.add_missing_file(file_path)
        return report
    
    # Get all existing MDC files
    existing_mdc_files = {}
    for filename in os.listdir(rules_dir):
        if filename.endswith('.mdc'):
            full_path = os.path.join(rules_dir, filename)
            existing_mdc_files[filename] = full_path
    
    logging.info(f"Analyzing {len(existing_mdc_files)} MDC files")
    
    # Analyze each existing MDC file
    for mdc_file, full_path in existing_mdc_files.items():
        try:
            score, issues, is_high_quality = analyze_mdc_quality(full_path)
            report.add_file_analysis(mdc_file, score, issues, is_high_quality)
            
            if is_high_quality:
                log_file_status(mdc_file, "high quality", score=score)
            else:
                status = "needs update" if len(issues) <= 2 else "poor quality"
                log_file_status(mdc_file, status, f"{len(issues)} issues", score=score)
        except Exception as e:
            logging.error(f"Error analyzing {mdc_file}: {e}")
            report.add_file_analysis(mdc_file, 0.0, [f"Analysis error: {str(e)}"], False)
    
    # Check for missing MDC files
    expected_mdc_names = set()
    for file_path in expected_files:
        flat_name = file_path.replace("/", "_").replace("\\", "_")
        expected_mdc_names.add(f"{flat_name}.mdc")
    
    for expected_name in expected_mdc_names:
        if expected_name not in existing_mdc_files:
            report.add_missing_file(expected_name)
            logging.info(f"Missing MDC file: {expected_name}")
    
    return report


def filter_files_needing_update(
    file_data: Dict, 
    quality_report: MDCQualityReport,
    rules_dir: str
) -> Dict:
    """
    Filter file_data to only include files that need MDC updates.
    
    Args:
        file_data: Original file data dictionary
        quality_report: Quality report from scanning
        rules_dir: Path to rules directory
        
    Returns:
        Filtered file_data dictionary with only files needing updates
    """
    files_to_update = {}
    
    for file_path, snippets in file_data.items():
        # Convert file path to MDC filename
        flat_name = file_path.replace("/", "_").replace("\\", "_")
        mdc_filename = f"{flat_name}.mdc"
        
        # Include file if:
        # 1. MDC doesn't exist (missing)
        # 2. MDC has quality issues (not high quality)
        if mdc_filename in quality_report.missing_files:
            files_to_update[file_path] = snippets
            log_file_status(file_path, "missing", "will create")
        elif mdc_filename in quality_report.files_with_issues:
            files_to_update[file_path] = snippets
            score = quality_report.quality_scores.get(mdc_filename, 0.0)
            log_file_status(file_path, "updating", score=score)
        else:
            log_file_status(file_path, "skipped", "high quality")
    
    summary = {
        "Files to update": f"{len(files_to_update)}/{len(file_data)}",
        "Skipped": f"{len(file_data) - len(files_to_update)}"
    }
    log_summary(summary, "Update Filter Results")
    return files_to_update


def save_quality_report(report: MDCQualityReport, output_dir: str):
    """
    Save quality report to a file.
    
    Args:
        report: MDCQualityReport object
        output_dir: Directory to save the report
    """
    report_path = os.path.join(output_dir, "mdc_quality_report.md")
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# MDC Quality Assessment Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- **Total MDC files analyzed**: {report.files_analyzed}\n")
            f.write(f"- **High-quality files**: {len(report.high_quality_files)}\n")
            f.write(f"- **Files with quality issues**: {len(report.files_with_issues)}\n")
            f.write(f"- **Missing MDC files**: {len(report.missing_files)}\n\n")
            
            if report.files_with_issues:
                f.write("## Files Requiring Updates\n\n")
                for file_path in report.files_with_issues:
                    score = report.quality_scores.get(file_path, 0.0)
                    issues = report.issues_by_file.get(file_path, [])
                    f.write(f"### {file_path}\n")
                    f.write(f"**Quality Score**: {score:.2f}/10\n\n")
                    f.write("**Issues**:\n")
                    for issue in issues:
                        f.write(f"- {issue}\n")
                    f.write("\n")
            
            if report.high_quality_files:
                f.write("## High-Quality Files\n\n")
                for file_path in report.high_quality_files:
                    score = report.quality_scores.get(file_path, 0.0)
                    f.write(f"- {file_path} (Score: {score:.2f}/10)\n")
                f.write("\n")
            
            if report.missing_files:
                f.write("## Missing MDC Files\n\n")
                for file_path in report.missing_files:
                    f.write(f"- {file_path}\n")
                f.write("\n")
        
        logging.info(f"Quality report saved to {report_path}")
    except Exception as e:
        logging.error(f"Error saving quality report: {e}")
