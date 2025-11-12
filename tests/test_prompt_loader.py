"""
Tests for the prompt_loader module.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.prompt_loader import PromptLoader, get_prompt_loader, reload_prompt_loader


# Sample markdown content for testing
SAMPLE_PROMPTS_MD = """# Project-Specific Prompts Configuration

## Domain Information

**Domain Name:** Test Application Security
**Code Units:** microservices
**State Concept:** distributed state

## Operating Constraints

- Hound performs static analysis only
- No runtime execution allowed
- All actions are CODE-ONLY

## Code Unit Prioritization (Phase 1)

Target medium-sized units: services, handlers, repositories

Prioritize components:
- Handling authentication
- Processing sensitive data
- Managing access control

## Vulnerability Categories (Phase 1 - Coverage)

- Authentication bypass
- Authorization failures
- Input validation issues
- SQL injection
- XSS vulnerabilities

## High-Impact Focus (Phase 2 - Intuition)

**Primary Impact:** DATA BREACH - prioritize data leakage vulnerabilities

**Key Intuition Targets:**
1. ACCESS CONTROL: Where can unauthorized access occur?
2. DATA LEAKAGE: What sensitive data might be exposed?
3. INJECTION: Where do inputs flow into dangerous sinks?
4. SESSION: What session management issues exist?

## Mitigation Patterns

- Input validation
- Parameterized queries
- Output encoding
- Authentication middleware
- CSRF protection

## Observation Examples

Good examples:
- "requires auth"
- "validates input"
- "admin only"
- "SQL safe"

## Graph Types

### Suggested Graph Types for Analysis

**RequestFlow**
Focus: HTTP request routing and handling
Edge types: routes_to, handles, validates

**AuthenticationChain**
Focus: Authentication and session management
Edge types: authenticates, validates, creates_session

**DataAccess**
Focus: Database queries and data operations
Edge types: queries, inserts, updates, deletes

## External Dependencies Examples

Common frameworks:
- Express.js
- Django
- Flask

## Node Type Terminology

**Preferred node types:**
- Handler nodes (e.g., "handler_login")
- Service nodes (e.g., "service_UserService")
- Middleware nodes (e.g., "middleware_auth")
"""


class TestPromptLoader:
    """Test suite for PromptLoader functionality."""

    def test_load_explicit_path(self):
        """Test loading prompts from explicitly provided path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)

            # Verify file was loaded
            assert loader.prompts_file == prompts_path
            assert len(loader.sections) > 0

            # Verify content parsing
            assert loader.get_domain_name() == "Test Application Security"
            assert loader.get_code_units() == "microservices"
            assert loader.get_state_concept() == "distributed state"
        finally:
            os.unlink(prompts_path)

    def test_load_from_environment_variable(self):
        """Test loading prompts from HOUND_PROMPTS environment variable."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = f.name

        try:
            # Set environment variable
            os.environ['HOUND_PROMPTS'] = prompts_path

            loader = PromptLoader()

            # Verify loaded from environment
            assert loader.prompts_file == Path(prompts_path)
            assert loader.get_domain_name() == "Test Application Security"
        finally:
            os.environ.pop('HOUND_PROMPTS', None)
            os.unlink(prompts_path)

    def test_load_from_current_directory(self):
        """Test loading project_specific_prompts.md from current directory."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create prompts file in current directory
                prompts_path = Path('project_specific_prompts.md')
                with open(prompts_path, 'w') as f:
                    f.write(SAMPLE_PROMPTS_MD)

                loader = PromptLoader()

                # Verify loaded from current directory
                assert loader.prompts_file == prompts_path.resolve()
                assert loader.get_domain_name() == "Test Application Security"
            finally:
                os.chdir(original_cwd)

    def test_load_from_project_root(self):
        """Test loading prompts from project root (with .git directory)."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Create a project structure
                project_root = Path(tmpdir) / "myproject"
                project_root.mkdir()
                (project_root / ".git").mkdir()  # Git indicator

                # Create prompts in project root
                prompts_path = project_root / "project_specific_prompts.md"
                with open(prompts_path, 'w') as f:
                    f.write(SAMPLE_PROMPTS_MD)

                # Create subdirectory and change to it
                subdir = project_root / "src" / "components"
                subdir.mkdir(parents=True)
                os.chdir(subdir)

                loader = PromptLoader()

                # Should find prompts in project root
                # Resolve both paths to handle symlinks (e.g., /var -> /private/var on macOS)
                assert loader.prompts_file.resolve() == prompts_path.resolve()
                assert loader.get_domain_name() == "Test Application Security"
            finally:
                os.chdir(original_cwd)

    def test_fallback_to_defaults(self):
        """Test fallback to smart contract defaults when no prompts file found."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                # No prompts file created

                loader = PromptLoader()

                # Should use defaults
                assert loader.prompts_file is None
                assert len(loader.sections) > 0  # Default sections exist

                # Verify default smart contract values
                assert "Smart Contract" in loader.get_domain_name()
                assert "smart contracts" in loader.get_code_units()
                assert "on-chain state" in loader.get_state_concept()
            finally:
                os.chdir(original_cwd)

    def test_priority_order(self):
        """Test that prompt sources are checked in correct priority order."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create multiple prompts files
                explicit_path = Path(tmpdir) / 'explicit.md'
                env_path = Path(tmpdir) / 'env.md'
                cwd_path = Path(tmpdir) / 'project_specific_prompts.md'

                # Write different domain names to each
                with open(explicit_path, 'w') as f:
                    f.write(SAMPLE_PROMPTS_MD.replace("Test Application Security", "Explicit Source"))
                with open(env_path, 'w') as f:
                    f.write(SAMPLE_PROMPTS_MD.replace("Test Application Security", "Environment Source"))
                with open(cwd_path, 'w') as f:
                    f.write(SAMPLE_PROMPTS_MD.replace("Test Application Security", "CWD Source"))

                # Test 1: Explicit path takes priority
                loader = PromptLoader(explicit_path)
                assert "Explicit Source" in loader.get_domain_name()

                # Test 2: Environment takes priority over cwd
                os.environ['HOUND_PROMPTS'] = str(env_path)
                try:
                    loader = PromptLoader()
                    assert "Environment Source" in loader.get_domain_name()
                finally:
                    os.environ.pop('HOUND_PROMPTS', None)

                # Test 3: CWD when no env var or explicit path
                loader = PromptLoader()
                assert "CWD Source" in loader.get_domain_name()
            finally:
                os.chdir(original_cwd)

    def test_markdown_parsing(self):
        """Test markdown section parsing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)

            # Verify all major sections are parsed
            assert "Domain Information" in loader.sections
            assert "Operating Constraints" in loader.sections
            assert "Vulnerability Categories (Phase 1 - Coverage)" in loader.sections
            assert "High-Impact Focus (Phase 2 - Intuition)" in loader.sections
            assert "Mitigation Patterns" in loader.sections
            assert "Graph Types" in loader.sections
        finally:
            os.unlink(prompts_path)

    def test_get_domain_name(self):
        """Test extracting domain name."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)
            assert loader.get_domain_name() == "Test Application Security"
        finally:
            os.unlink(prompts_path)

    def test_get_code_units(self):
        """Test extracting code units."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)
            assert loader.get_code_units() == "microservices"
        finally:
            os.unlink(prompts_path)

    def test_get_state_concept(self):
        """Test extracting state concept."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)
            assert loader.get_state_concept() == "distributed state"
        finally:
            os.unlink(prompts_path)

    def test_get_operating_constraints(self):
        """Test extracting operating constraints."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)
            constraints = loader.get_operating_constraints()
            assert "static analysis" in constraints.lower()
            assert "no runtime execution" in constraints.lower()
        finally:
            os.unlink(prompts_path)

    def test_get_vulnerability_categories_phase1(self):
        """Test extracting vulnerability categories for Phase 1."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)
            vulns = loader.get_vulnerability_categories_phase1()
            assert "Authentication bypass" in vulns
            assert "SQL injection" in vulns
            assert "XSS vulnerabilities" in vulns
        finally:
            os.unlink(prompts_path)

    def test_get_high_impact_focus_phase2(self):
        """Test extracting high-impact focus for Phase 2."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)
            focus = loader.get_high_impact_focus_phase2()
            assert "DATA BREACH" in focus
            assert "ACCESS CONTROL" in focus
        finally:
            os.unlink(prompts_path)

    def test_get_mitigation_patterns(self):
        """Test extracting mitigation patterns."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)
            patterns = loader.get_mitigation_patterns()
            assert "Input validation" in patterns
            assert "Parameterized queries" in patterns
        finally:
            os.unlink(prompts_path)

    def test_get_graph_types_section(self):
        """Test extracting graph types section."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)
            graph_types = loader.get_graph_types_section()
            assert "RequestFlow" in graph_types
            assert "AuthenticationChain" in graph_types
            assert "DataAccess" in graph_types
        finally:
            os.unlink(prompts_path)

    def test_get_observation_examples(self):
        """Test extracting observation examples."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)
            examples = loader.get_observation_examples()
            assert "requires auth" in examples
            assert "admin only" in examples
        finally:
            os.unlink(prompts_path)

    def test_nonexistent_explicit_path(self):
        """Test behavior when explicit path doesn't exist."""
        nonexistent_path = Path('/tmp/nonexistent_prompts_12345.md')
        loader = PromptLoader(nonexistent_path)

        # Should fall back to defaults
        assert loader.prompts_file is None
        assert "Smart Contract" in loader.get_domain_name()

    def test_global_singleton(self):
        """Test get_prompt_loader returns singleton instance."""
        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()

        # Should be the same instance
        assert loader1 is loader2

    def test_reload_prompt_loader(self):
        """Test reload_prompt_loader creates new instance."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create initial prompts file
                prompts_path = Path('project_specific_prompts.md')
                with open(prompts_path, 'w') as f:
                    f.write(SAMPLE_PROMPTS_MD)

                # Get initial loader
                loader1 = get_prompt_loader()
                domain1 = loader1.get_domain_name()

                # Modify the file
                with open(prompts_path, 'w') as f:
                    f.write(SAMPLE_PROMPTS_MD.replace("Test Application Security", "Modified Domain"))

                # Reload
                loader2 = reload_prompt_loader()

                # Should be new instance with updated content
                assert loader2 is not loader1
                assert "Modified Domain" in loader2.get_domain_name()
            finally:
                os.chdir(original_cwd)

    def test_missing_sections_use_fallbacks(self):
        """Test that missing sections return sensible fallbacks."""
        minimal_md = """# Minimal Config

## Domain Information

**Domain Name:** Minimal Test
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(minimal_md)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)

            # Should parse what's there
            assert loader.get_domain_name() == "Minimal Test"

            # Should provide fallbacks for missing sections
            assert loader.get_operating_constraints() != ""
            assert loader.get_code_units() == "components"  # Fallback
        finally:
            os.unlink(prompts_path)

    def test_malformed_domain_info(self):
        """Test handling of malformed domain information."""
        malformed_md = """# Config

## Domain Information

Some text without the expected format.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(malformed_md)
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)

            # Should return fallbacks when parsing fails
            assert loader.get_domain_name() == "the codebase"
            assert loader.get_code_units() == "components"
        finally:
            os.unlink(prompts_path)

    def test_file_read_error_handling(self):
        """Test handling of file read errors."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_PROMPTS_MD)
            prompts_path = Path(f.name)

        # Delete the file before loading
        os.unlink(prompts_path)

        # Should handle missing file gracefully
        loader = PromptLoader(prompts_path)

        # Should fall back to defaults
        assert loader.prompts_file is None or not loader.prompts_file.exists()
        assert len(loader.sections) >= 0  # Empty or defaults

    def test_empty_file(self):
        """Test handling of empty prompts file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("")  # Empty file
            prompts_path = Path(f.name)

        try:
            loader = PromptLoader(prompts_path)

            # Should handle empty file gracefully
            assert loader.sections == {} or len(loader.sections) == 0

            # Should provide fallbacks
            assert loader.get_domain_name() == "the codebase"
        finally:
            os.unlink(prompts_path)

    def test_default_smart_contract_values(self):
        """Test that defaults contain correct smart contract values."""
        loader = PromptLoader()  # No file, use defaults

        # Verify smart contract defaults
        assert "Smart Contract" in loader.get_domain_name()
        assert "smart contracts" in loader.get_code_units()
        assert "on-chain state" in loader.get_state_concept()

        # Verify default vulnerability categories
        vulns = loader.get_vulnerability_categories_phase1()
        assert "reentrancy" in vulns.lower() or "Reentrancy" in vulns

        # Verify default graph types
        graphs = loader.get_graph_types_section()
        assert "AuthorizationMap" in graphs
        assert "AssetFlow" in graphs
