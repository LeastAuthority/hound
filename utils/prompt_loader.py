"""
Utility for loading project-specific prompt customizations.

This module provides the PromptLoader class which allows Hound to be customized
for different project types (smart contracts, web applications, APIs, etc.) by
reading a single markdown configuration file.
"""

from pathlib import Path
from typing import Any
import re
import os


class PromptLoader:
    """
    Loads and parses project-specific prompt customizations from markdown.

    The PromptLoader searches for a project_specific_prompts.md file in multiple
    locations (with priority order) and parses it to extract domain-specific
    information that gets injected into AI prompts throughout the system.

    If no customization file is found, defaults to smart contract mode for
    backwards compatibility.
    """

    def __init__(self, prompts_file: Path | None = None):
        """
        Initialize the prompt loader.

        Priority order for finding prompts file:
        1. Explicitly provided prompts_file path
        2. HOUND_PROMPTS environment variable
        3. project_specific_prompts.md in current directory
        4. project_specific_prompts.md in project root (walks up to find .git, pyproject.toml, etc.)
        5. Smart contract defaults (backwards compatible)

        Args:
            prompts_file: Optional explicit path to prompts file
        """
        self.prompts_file = self._find_prompts_file(prompts_file)
        self.sections = self._parse_markdown() if self.prompts_file else self._get_defaults()

    def _find_prompts_file(self, explicit_path: Path | None) -> Path | None:
        """
        Find the prompts file using priority order.

        Args:
            explicit_path: Explicitly provided path (highest priority)

        Returns:
            Path to prompts file if found, None otherwise (will use defaults)
        """
        # 1. Explicit path
        if explicit_path:
            if explicit_path.exists():
                return explicit_path
            else:
                print(f"Warning: Specified prompts file not found: {explicit_path}")
                return None

        # 2. Environment variable
        env_path_str = os.environ.get('HOUND_PROMPTS')
        if env_path_str:
            env_path = Path(env_path_str)
            if env_path.exists():
                return env_path
            else:
                print(f"Warning: HOUND_PROMPTS env var points to non-existent file: {env_path}")

        # 3. Current directory
        cwd_prompts = Path.cwd() / "project_specific_prompts.md"
        if cwd_prompts.exists():
            return cwd_prompts

        # 4. Project root (try to find it)
        # Walk up to find project root indicators (.git, pyproject.toml, etc.)
        current = Path.cwd()
        for _ in range(5):  # Only look up 5 levels
            for indicator in ['.git', 'pyproject.toml', 'setup.py', 'package.json']:
                if (current / indicator).exists():
                    prompts = current / "project_specific_prompts.md"
                    if prompts.exists():
                        return prompts

            # Stop if we've reached root
            parent = current.parent
            if parent == current:
                break
            current = parent

        # Not found - will use defaults
        return None

    def _parse_markdown(self) -> dict[str, str]:
        """
        Parse markdown file into sections.

        Extracts all level-2 headers (## Section Name) and their content
        into a dictionary for easy lookup.

        Returns:
            Dictionary mapping section names to their content
        """
        if not self.prompts_file:
            return {}

        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Failed to read prompts file {self.prompts_file}: {e}")
            return {}

        sections = {}

        # Extract major sections (## headers)
        # Match: ## Section Name\ncontent...\n## Next Section or end of file
        pattern = r'^## (.+?)$\n(.*?)(?=^## |\Z)'
        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)

        for match in matches:
            section_name = match.group(1).strip()
            section_content = match.group(2).strip()
            sections[section_name] = section_content

        return sections

    def _get_defaults(self) -> dict[str, str]:
        """
        Return smart contract defaults for backwards compatibility.

        These defaults match the original hardcoded prompts in Hound,
        ensuring existing smart contract projects continue to work without
        any configuration.

        Returns:
            Dictionary of default sections for smart contract auditing
        """
        return {
            "Domain Information": """**Domain Name:** Smart Contract Auditing
**Code Units:** smart contracts
**State Concept:** on-chain state""",

            "Operating Constraints": """- Hound cannot run code, connect to RPC, fork a chain, deploy contracts, or query on-chain state.
- Do NOT propose or assume live on-chain probing (e.g., calling initialize on proxies, running fork-based tests, deploying mocks).
- All actions here are CODE-ONLY: loading/reading nodes, updating observations, and calling deep_think for analysis.""",

            "Code Unit Prioritization (Phase 1)": """Target medium-sized units: contracts, modules, classes, services

Prioritize components:
- Handling critical state or permissions
- With complex logic
- Interacting with external systems""",

            "Vulnerability Categories (Phase 1 - Coverage)": """Look for these vulnerability types during systematic analysis:
- Missing validation
- Access control issues
- Integer overflow/underflow
- Reentrancy vulnerabilities
- Logic errors
- Oracle manipulation
- Front-running risks""",

            "High-Impact Focus (Phase 2 - Intuition)": """**Primary Impact:** MONETARY IMPACT - prioritize vulnerabilities that lead to financial loss

**Key Intuition Targets:**
1. VALUE AT RISK: Where can money be stolen or locked?
2. CONTRADICTIONS: What doesn't match between docs and code?
3. AUTH BYPASSES: Where might permission checks fail?
4. STATE CORRUPTION: What could break critical invariants?""",

            "Mitigation Patterns": """Common security patterns to verify:
- guards/require statements
- reentrancy protections
- access control modifiers
- input validation
- permission checks""",

            "Observation Examples": """Good examples for graph annotations (2-4 words each):
- "only owner"
- "checks balance"
- "emits Transfer"
- "immutable"
- "reentrancy guard"
- "external call"
- "nonReentrant"
- "onlyRole(Role)" """,

            "Graph Types": """### Suggested Graph Types for Analysis

**AuthorizationMap**
Focus: who grants/assumes/authorizes which roles/actions
Edge types: creates, grants, assumes, authorizes, guarded_by

**PermissionChecks**
Focus: coverage of access modifiers and require checks per function
Edge types: guarded_by, unchecked, requires_role

**AssetFlow**
Focus: mint/burn/transfer/deposit/withdraw across contracts and accounts
Edge types: mints, burns, transfers, deposits, withdraws

**StateMutation**
Focus: storage variables and the functions that read/write them
Edge types: written_by, read_by, derived_from

**UpgradeLifecycle**
Focus: deployment/initialization/upgrade relationships
Edge types: deploys, initializes, upgrades, migrates_from

**ExternalDeps**
Focus: external/oracle/library dependencies and trust boundaries
Edge types: reads_from, depends_on, trusts, verifies

**Reentrancy/ExternalCalls**
Focus: external call graph with entrypoints and reentrant paths
Edge types: calls_external, reentrant_path, invokes_untrusted

**InvariantsMap**
Focus: key invariants/assumptions and where they're enforced
Edge types: enforced_by, broken_by, relies_on

**MathAlgorithm**
Focus: break down core formulas/AMM math into steps/variables
Edge types: computes, uses_param, normalizes, clamps

**EventMap**
Focus: which events are emitted by which functions and with what state
Edge types: emitted_by, indexes, correlates_with

**TimeWindows/RateLimits**
Focus: time-based gates and limits
Edge types: gates, bounded_by, cooldown""",

            "External Dependencies Examples": """Common external libraries/frameworks to exclude from node creation:
- OpenZeppelin (smart contract library)
- Chainlink (oracle network)
- SafeMath (arithmetic library)""",

            "Node Type Terminology": """**Preferred node types:**
- Function-level nodes (e.g., "func_transfer", "func_mint")
- Storage-level nodes (e.g., "storage_balances", "storage_owner")
- Contract-level nodes (only when necessary)"""
        }

    # ========== Accessor Methods ==========
    # These methods extract specific information from the parsed sections

    def get_domain_name(self) -> str:
        """
        Get the domain name (e.g., 'Smart Contract Auditing', 'Web Application Security').

        Returns:
            Domain name string, or generic fallback if not found
        """
        domain_info = self.sections.get("Domain Information", "")
        match = re.search(r'\*\*Domain Name:\*\*\s*(.+?)(?:\n|$)', domain_info)
        return match.group(1).strip() if match else "the codebase"

    def get_code_units(self) -> str:
        """
        Get code unit terminology (e.g., 'smart contracts', 'modules', 'services').

        Returns:
            Code units string, or generic fallback if not found
        """
        domain_info = self.sections.get("Domain Information", "")
        match = re.search(r'\*\*Code Units:\*\*\s*(.+?)(?:\n|$)', domain_info)
        return match.group(1).strip() if match else "components"

    def get_state_concept(self) -> str:
        """
        Get state concept terminology (e.g., 'on-chain state', 'application state').

        Returns:
            State concept string, or generic fallback if not found
        """
        domain_info = self.sections.get("Domain Information", "")
        match = re.search(r'\*\*State Concept:\*\*\s*(.+?)(?:\n|$)', domain_info)
        return match.group(1).strip() if match else "state"

    def get_operating_constraints(self) -> str:
        """
        Get the operating constraints section.

        Returns:
            Operating constraints text
        """
        return self.sections.get("Operating Constraints", "Static analysis only - no runtime execution.")

    def get_code_unit_prioritization(self) -> str:
        """
        Get code unit prioritization guidance for Phase 1.

        Returns:
            Prioritization guidance text
        """
        return self.sections.get("Code Unit Prioritization (Phase 1)", "")

    def get_vulnerability_categories_phase1(self) -> str:
        """
        Get vulnerability categories for Phase 1 coverage mode.

        This extracts the vulnerability list and formats it as a comma-separated
        string suitable for prompt injection.

        Returns:
            Comma-separated vulnerability categories
        """
        content = self.sections.get("Vulnerability Categories (Phase 1 - Coverage)", "")

        # Extract just the vulnerability list part
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]

        # Look for bullet points
        if any(line.startswith('-') for line in lines):
            # Bullet list - extract items
            vulnerabilities = [line.lstrip('- ').strip() for line in lines if line.startswith('-')]
            return ', '.join(vulnerabilities)
        else:
            # Assume it's already formatted as comma-separated or paragraph
            return content.strip()

    def get_high_impact_focus_phase2(self) -> str:
        """
        Get high-impact focus areas for Phase 2 intuition mode.

        Returns:
            High-impact focus text with key targets
        """
        return self.sections.get("High-Impact Focus (Phase 2 - Intuition)",
                                  "Focus on high-impact vulnerabilities")

    def get_mitigation_patterns(self) -> str:
        """
        Get mitigation pattern terminology.

        This extracts security patterns that should be checked during analysis.

        Returns:
            Comma-separated or formatted mitigation patterns
        """
        content = self.sections.get("Mitigation Patterns", "validation checks and security controls")

        # Extract patterns from bullet list if present
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if any(line.startswith('-') for line in lines):
            patterns = [line.lstrip('- ').strip() for line in lines if line.startswith('-')]
            return ', '.join(patterns) if patterns else content

        return content.strip()

    def get_graph_types_section(self) -> str:
        """
        Get the complete graph types section for injection into graph discovery prompt.

        Returns:
            Full graph types section with all suggested graphs
        """
        return self.sections.get("Graph Types", "")

    def get_observation_examples(self) -> str:
        """
        Get observation examples for graph annotations.

        Returns:
            Comma-separated observation examples
        """
        content = self.sections.get("Observation Examples", "")
        if content:
            # Extract examples from bullet lists
            examples = []
            for line in content.split('\n'):
                if line.strip().startswith('-'):
                    # Extract quoted text
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        examples.append(f'"{match.group(1)}"')

            if examples:
                return ', '.join(examples)

        # Fallback examples
        return '"checks balance", "only owner", "external call"'

    def get_external_dependencies_examples(self) -> str:
        """
        Get external dependencies examples.

        Returns:
            External dependencies text
        """
        return self.sections.get("External Dependencies Examples",
                                  "Common external libraries and frameworks")

    def get_node_type_terminology(self) -> str:
        """
        Get node type terminology guidance.

        Returns:
            Node type terminology text
        """
        return self.sections.get("Node Type Terminology", "")


# ========== Global Instance ==========
# Lazily initialized singleton for convenient access throughout the application

_prompt_loader: PromptLoader | None = None


def get_prompt_loader() -> PromptLoader:
    """
    Get the global PromptLoader instance.

    This function implements a singleton pattern for the PromptLoader.
    The instance is created on first access and reused for subsequent calls.

    Returns:
        Global PromptLoader instance
    """
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


def reload_prompt_loader(prompts_file: Path | None = None) -> PromptLoader:
    """
    Reload the global PromptLoader with a new file.

    This is useful for testing or when the prompts file changes during runtime.

    Args:
        prompts_file: Optional path to prompts file

    Returns:
        Newly created PromptLoader instance
    """
    global _prompt_loader
    _prompt_loader = PromptLoader(prompts_file)
    return _prompt_loader


# ========== Testing/Debug Utilities ==========

def print_loaded_config(loader: PromptLoader | None = None):
    """
    Print the currently loaded configuration for debugging.

    Args:
        loader: PromptLoader instance to print, or None to use global instance
    """
    if loader is None:
        loader = get_prompt_loader()

    print("=" * 80)
    print("HOUND PROMPT CONFIGURATION")
    print("=" * 80)
    print(f"Prompts file: {loader.prompts_file or 'Using defaults (Smart Contract mode)'}")
    print()
    print(f"Domain Name: {loader.get_domain_name()}")
    print(f"Code Units: {loader.get_code_units()}")
    print(f"State Concept: {loader.get_state_concept()}")
    print()
    print("Available sections:")
    for section_name in loader.sections.keys():
        print(f"  - {section_name}")
    print("=" * 80)
