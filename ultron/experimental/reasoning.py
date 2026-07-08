import os
import sys

# Absolute imports used since ultron/core/ and ultron/experimental/ are on sys.path
from ultron.experimental.design_oracle import (
    detect_circular_dependencies,
    score_coupling_debt,
    detect_abstraction_leaks,
    compute_hotspot_scores
)

class ReasoningCard:
    """
    Structured card explaining an architectural violation or smell.
    """
    def __init__(self, filepath, principle, observation, reason, consequences, severity):
        self.filepath = filepath
        self.principle = principle
        self.observation = observation
        self.reason = reason
        self.consequences = consequences
        self.severity = severity  # ADP=1, SDP=2, DIP=3, SRP=4/5

    def format(self):
        """
        Formats the reasoning card as a structured Markdown block.
        """
        if self.filepath is None or self.principle is None:
            raise ValueError("ReasoningCard fields must not be None")
            
        consequence_lines = "\n".join(f"  - {c}" for c in self.consequences)
        return (
            f"### Violation: {self.principle}\n"
            f"**File:** `{self.filepath}`\n"
            f"**Observation:** {self.observation}\n"
            f"**Reason:** {self.reason}\n"
            f"**Consequences:**\n{consequence_lines}\n"
        )


class ReasoningEngine:
    """
    Architectural reasoning engine mapping codebase metrics to software engineering principles.
    """
    def __init__(self, codebase, repo_path):
        self.codebase = codebase
        self.repo_path = repo_path

    def analyze(self):
        """
        Evaluates the codebase, maps metrics to principles, and returns
        an ordered list of ReasoningCard objects grouped by file and sorted by severity.
        """
        if not isinstance(self.codebase, dict):
            raise TypeError("codebase must be a dictionary")
        if not self.repo_path:
            raise ValueError("repo_path must not be empty or None")

        # 1. Run static metrics gathering
        try:
            cycles = detect_circular_dependencies(self.codebase)
        except Exception as e:
            print(f"[-] ReasoningEngine: failed to detect circular dependencies: {e}", file=sys.stderr)
            cycles = []

        try:
            coupling = score_coupling_debt(self.codebase)
        except Exception as e:
            print(f"[-] ReasoningEngine: failed to compute coupling scores: {e}", file=sys.stderr)
            coupling = []

        try:
            leaks = detect_abstraction_leaks(self.codebase, self.repo_path)
        except Exception as e:
            print(f"[-] ReasoningEngine: failed to detect abstraction leaks: {e}", file=sys.stderr)
            leaks = {}

        try:
            hotspots = compute_hotspot_scores(self.codebase, self.repo_path, [])
        except Exception as e:
            print(f"[-] ReasoningEngine: failed to compute hotspots: {e}", file=sys.stderr)
            hotspots = []

        # Convert coupling/hotspots to helper dicts for fast lookups
        coupling_by_file = {entry["file"]: entry for entry in coupling}
        hotspot_by_file = {entry["file"]: entry for entry in hotspots}

        cards_by_file = {}

        for rel_path in self.codebase:
            file_cards = []

            # Smell A: Acyclic Dependencies Principle (ADP)
            file_cycles = [c for c in cycles if rel_path in c]
            if file_cycles:
                cycle_descriptions = []
                for cycle in file_cycles:
                    cycle_descriptions.append(" → ".join(cycle))
                file_cards.append(ReasoningCard(
                    filepath=rel_path,
                    principle="Acyclic Dependencies Principle (ADP)",
                    observation=f"File is part of {len(file_cycles)} circular dependency loops.",
                    reason="Imports form a closed dependency loop, tightly coupling these modules together.",
                    consequences=[
                        "Modules cannot be tested, compiled, or reused in isolation.",
                        "Changes to any file in the cycle propagate unpredictably through the entire loop.",
                        "Breaks codebase dependency DAG predictability."
                    ],
                    severity=1
                ))

            # Fetch coupling info
            c_info = coupling_by_file.get(rel_path)
            if c_info:
                fi = c_info["fan_in"]
                fo = c_info["fan_out"]
                debt = c_info["coupling_debt"]
                instability = c_info["instability"]

                # Smell B: Stable Dependencies Principle (SDP)
                # Stable component (high fan-in, low instability) depends on other modules (fan-out > 0)
                if debt > 20 and instability < 0.3 and fo > 0:
                    file_cards.append(ReasoningCard(
                        filepath=rel_path,
                        principle="Stable Dependencies Principle (SDP)",
                        observation=f"Stable core module has outward dependencies (Fan-in: {fi}, Fan-out: {fo}, Instability: {instability}).",
                        reason="Stable components are highly imported and hard to change; depending on volatile components forces stable modules to change frequently.",
                        consequences=[
                            "Changes in volatile downstream modules will propagate upward and force modifications to this stable core abstraction.",
                            "Violates SDP: the stability of a module should be greater than the stability of the modules it depends on."
                        ],
                        severity=2
                    ))

                # Smell C: Dependency Inversion Principle (DIP)
                # High outward coupling
                if fo > 8:
                    file_cards.append(ReasoningCard(
                        filepath=rel_path,
                        principle="Dependency Inversion Principle (DIP)",
                        observation=f"Excessive outward coupling detected (Fan-out: {fo}).",
                        reason="Module directly imports and depends on too many concrete downstream modules instead of abstract interfaces.",
                        consequences=[
                            "Tightly bound to concrete details, reducing modularity and replaceability.",
                            "High fragility: changes in any of the imported concrete dependencies propagate back to this file."
                        ],
                        severity=3
                    ))

            # Smell D: Single Responsibility Principle (SRP - Abstraction Leak)
            if rel_path in leaks:
                file_leaks = leaks[rel_path]
                leak_details = []
                for leak in file_leaks:
                    leak_details.append(f"Function `{leak['function']}` (line {leak['lineno']}) calls {leak['responsibility_count']} distinct namespaces")
                
                file_cards.append(ReasoningCard(
                    filepath=rel_path,
                    principle="Single Responsibility Principle (SRP - Abstraction Leak)",
                    observation=f"Abstraction leaks detected in {len(file_leaks)} function(s). Details:\n" + "\n".join(f"    - {d}" for d in leak_details),
                    reason="Function calls into too many distinct external module namespaces directly, violating encapsulation boundaries.",
                    consequences=[
                        "Function is managing multiple external concerns (violating SRP).",
                        "Violates the Law of Demeter (LoD): tightly coupled to implementation details of multiple packages."
                    ],
                    severity=4
                ))

            # Smell E: Single Responsibility Principle (SRP - Hotspot / God Object)
            h_info = hotspot_by_file.get(rel_path)
            if h_info:
                score = h_info["hotspot_score"]
                complexity = h_info["complexity"]
                debt = h_info["coupling_debt"]

                if score > 0.6 and complexity > 40:
                    file_cards.append(ReasoningCard(
                        filepath=rel_path,
                        principle="Single Responsibility Principle (SRP - God Object Hotspot)",
                        observation=f"High composite hotspot score ({score:.4f}) with high cyclomatic complexity ({complexity}).",
                        reason="Module accumulates too much cyclomatic complexity alongside a heavy dependency footprint, acting as a God Object.",
                        consequences=[
                            "High risk of regression; small edits trigger side-effects across the codebase.",
                            "Difficult to maintain, read, or test in isolation due to high concentration of concern density."
                        ],
                        severity=5
                    ))

            if file_cards:
                # Sort file cards by severity (ADP=1 > SDP=2 > DIP=3 > SRP=4/5)
                file_cards.sort(key=lambda c: c.severity)
                cards_by_file[rel_path] = file_cards

        # Group and order files by severity of their highest violation
        ordered_files = []
        for f, cards in cards_by_file.items():
            min_severity = min(c.severity for c in cards)
            ordered_files.append((f, min_severity, cards))

        # Sort files by their minimum severity first, then alphabetically by file path
        ordered_files.sort(key=lambda x: (x[1], x[0]))

        final_cards = []
        for _, _, cards in ordered_files:
            final_cards.extend(cards)

        return final_cards
