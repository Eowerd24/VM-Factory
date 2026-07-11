import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from library.models import Report

class ReportParserError(Exception):
    """Raised for any reporting or parsing errors."""
    pass

class ReportParser:
    """Parses guest reports, needs list, and progress files."""

    @staticmethod
    def parse_report_json(file_path: Path) -> Report:
        """Parses a guest report.json file directly into a Report Pydantic model."""
        if not file_path.exists():
            raise FileNotFoundError(f"Report file not found: {file_path}")
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return Report.model_validate(data)
        except Exception as e:
            raise ReportParserError(f"Failed to parse report JSON from {file_path}: {e}")

    @staticmethod
    def parse_needs_md(file_path: Path) -> List[str]:
        """Extracts requested dependencies from an agent's NEEDS.md file.
        
        Matches lines of the form:
            - need: <package_name> [reason]
            need: <package_name>
        """
        if not file_path.exists():
            return []
        
        needs = []
        pattern = re.compile(r"^\s*[-*]?\s*need:\s*([^\s#]+)", re.IGNORECASE)
        
        try:
            with open(file_path, "r") as f:
                for line in f:
                    match = pattern.match(line)
                    if match:
                        needs.append(match.group(1).strip())
            return needs
        except Exception as e:
            raise ReportParserError(f"Failed to parse NEEDS.md from {file_path}: {e}")

    @staticmethod
    def parse_progress_identifiers(file_path: Path) -> Dict[str, List[str]]:
        """Parses a PROGRESS.md file and extracts lists of stable identifiers.
        
        Looks for patterns like:
          - W-\\d+ (Work Items)
          - B-\\d+ (Backlog Items)
          - Q-\\d+ (Open Questions)
          - D-\\d+ (Decisions)
          - BLK-\\d+ (Blockers)
          - KI-\\d+ (Known Issues)
        """
        identifiers = {
            "work_items": [],
            "backlog_items": [],
            "open_questions": [],
            "decisions": [],
            "blockers": [],
            "known_issues": []
        }
        
        if not file_path.exists():
            return identifiers

        # Compile regexes
        patterns = {
            "work_items": re.compile(r"\bW-\d+\b"),
            "backlog_items": re.compile(r"\bB-\d+\b"),
            "open_questions": re.compile(r"\bQ-\d+\b"),
            "decisions": re.compile(r"\bD-\d+\b"),
            "blockers": re.compile(r"\bBLK-\d+\b"),
            "known_issues": re.compile(r"\bKI-\d+\b")
        }

        try:
            with open(file_path, "r") as f:
                for line in f:
                    for key, pattern in patterns.items():
                        matches = pattern.findall(line)
                        for match in matches:
                            if match not in identifiers[key]:
                                identifiers[key].append(match)
            return identifiers
        except Exception as e:
            raise ReportParserError(f"Failed to parse PROGRESS.md from {file_path}: {e}")
