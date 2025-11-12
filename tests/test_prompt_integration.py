"""
Integration tests for prompt customization across the analysis pipeline.

These tests verify that custom prompts are correctly loaded and injected
into the various components of the Hound analysis system.
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.prompt_loader import PromptLoader, get_prompt_loader, reload_prompt_loader


# Sample markdown for different domains
SMART_CONTRACT_PROMPTS = """# Project-Specific Prompts Configuration

## Domain Information

**Domain Name:** Smart Contract Auditing
**Code Units:** smart contracts
**State Concept:** on-chain state

## Operating Constraints

- Hound cannot run code, connect to RPC, fork a chain, deploy contracts, or query on-chain state.
- Do NOT propose or assume live on-chain probing (e.g., calling initialize on proxies, running fork-based tests, deploying mocks).
- All actions here are CODE-ONLY: loading/reading nodes, updating observations, and calling deep_think for analysis.

## Vulnerability Categories (Phase 1 - Coverage)

- Missing validation
- Access control issues
- Integer overflow/underflow
- Reentrancy vulnerabilities
- Logic errors

## High-Impact Focus (Phase 2 - Intuition)

**Primary Impact:** MONETARY IMPACT - prioritize vulnerabilities that lead to financial loss

**Key Intuition Targets:**
1. VALUE AT RISK: Where can money be stolen or locked?
2. CONTRADICTIONS: What doesn't match between docs and code?
3. AUTH BYPASSES: Where might permission checks fail?
4. STATE CORRUPTION: What could break critical invariants?

## Mitigation Patterns

guards/require/reentrancy/permissions

## Observation Examples

- "only owner"
- "reentrancy guard"
- "external call"

## Graph Types

**AuthorizationMap**
Focus: who grants/assumes/authorizes which roles/actions
Edge types: creates, grants, assumes, authorizes, guarded_by

**AssetFlow**
Focus: mint/burn/transfer/deposit/withdraw across contracts
Edge types: mints, burns, transfers, deposits, withdraws
"""

WEB_APP_PROMPTS = """# Project-Specific Prompts Configuration

## Domain Information

**Domain Name:** Web Application Security
**Code Units:** route handlers and services
**State Concept:** session and database state

## Operating Constraints

- Hound performs static analysis only - it cannot execute code or start the web server.
- Do NOT propose or assume runtime testing (e.g., starting the server, making HTTP requests, accessing databases).
- All actions here are CODE-ONLY: loading/reading files, mapping flows, and performing static analysis.

## Vulnerability Categories (Phase 1 - Coverage)

- Input validation failures
- SQL injection vulnerabilities
- Cross-Site Scripting (XSS)
- Cross-Site Request Forgery (CSRF)
- Authentication bypasses

## High-Impact Focus (Phase 2 - Intuition)

**Primary Impact:** DATA BREACH RISK - prioritize vulnerabilities that lead to unauthorized access or data leakage

**Key Intuition Targets:**
1. DATA AT RISK: Where can sensitive data be accessed, leaked, or modified without authorization?
2. CONTRADICTIONS: What doesn't match between authentication claims and actual checks?
3. AUTH BYPASSES: Where might authentication or session checks be missing or bypassable?
4. INJECTION VECTORS: What user inputs flow into dangerous sinks (SQL, shell, eval)?

## Mitigation Patterns

input validation and sanitization, parameterized queries, authentication middleware

## Observation Examples

- "requires auth"
- "validates input"
- "XSS vulnerable"

## Graph Types

**RequestFlow**
Focus: HTTP routing, middleware chain, and endpoint handlers
Edge types: routes_to, protected_by, validates, handles

**DataValidation**
Focus: Input validation, sanitization, and encoding
Edge types: validates, sanitizes, encodes, filters
"""

API_SERVICE_PROMPTS = """# Project-Specific Prompts Configuration

## Domain Information

**Domain Name:** API Service Security
**Code Units:** API endpoints and services
**State Concept:** application state and data stores

## Operating Constraints

- Hound performs static analysis only - it cannot execute code or make API calls.
- Do NOT propose or assume runtime testing (e.g., calling endpoints, accessing databases, invoking external APIs).
- All actions here are CODE-ONLY: loading/reading files, mapping flows, and performing static analysis.

## Vulnerability Categories (Phase 1 - Coverage)

- Broken authentication
- Excessive data exposure
- Mass assignment
- Security misconfiguration
- Injection flaws

## High-Impact Focus (Phase 2 - Intuition)

**Primary Impact:** UNAUTHORIZED ACCESS - prioritize vulnerabilities that bypass authentication or authorization

**Key Intuition Targets:**
1. ACCESS CONTROL: Where can users access data or functions beyond their permissions?
2. DATA LEAKAGE: What sensitive information is exposed through API responses?
3. INJECTION POINTS: Where do user inputs flow into dangerous operations?
4. RATE LIMITING: What endpoints lack proper throttling and could be abused?

## Mitigation Patterns

authentication middleware, authorization checks, rate limiting

## Observation Examples

- "requires JWT"
- "admin scope"
- "rate limited"

## Graph Types

**EndpointMap**
Focus: API endpoints, their methods, and authentication requirements
Edge types: requires_auth, has_scope, rate_limited, public
"""


class TestPromptIntegration:
    """Integration tests for prompt customization across components."""

    def setup_method(self):
        """Reset global prompt loader before each test."""
        # Clear the global loader
        reload_prompt_loader(None)

    def test_smart_contract_default_behavior(self):
        """Test that Hound defaults to smart contract mode without prompts file."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                # Don't create any prompts file

                # Reload to pick up empty directory
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Should use smart contract defaults
                assert "Smart Contract" in loader.get_domain_name()
                assert "smart contracts" in loader.get_code_units()
                assert "on-chain state" in loader.get_state_concept()

                # Check vulnerability categories
                vulns = loader.get_vulnerability_categories_phase1()
                assert "reentrancy" in vulns.lower()

            finally:
                os.chdir(original_cwd)

    def test_web_application_integration(self):
        """Test integration with web application prompts."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create web app prompts
                prompts_path = Path('project_specific_prompts.md')
                with open(prompts_path, 'w') as f:
                    f.write(WEB_APP_PROMPTS)

                # Reload to pick up new prompts
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Verify web app specific values
                assert loader.get_domain_name() == "Web Application Security"
                assert loader.get_code_units() == "route handlers and services"
                assert loader.get_state_concept() == "session and database state"

                # Check vulnerability categories
                vulns = loader.get_vulnerability_categories_phase1()
                assert "SQL injection" in vulns
                assert "XSS" in vulns or "Cross-Site Scripting" in vulns

                # Check high-impact focus
                focus = loader.get_high_impact_focus_phase2()
                assert "DATA BREACH RISK" in focus
                assert "DATA AT RISK" in focus

                # Check graph types
                graphs = loader.get_graph_types_section()
                assert "RequestFlow" in graphs
                assert "DataValidation" in graphs

            finally:
                os.chdir(original_cwd)

    def test_api_service_integration(self):
        """Test integration with API service prompts."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create API service prompts
                prompts_path = Path('project_specific_prompts.md')
                with open(prompts_path, 'w') as f:
                    f.write(API_SERVICE_PROMPTS)

                # Reload to pick up new prompts
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Verify API service specific values
                assert loader.get_domain_name() == "API Service Security"
                assert loader.get_code_units() == "API endpoints and services"

                # Check vulnerability categories
                vulns = loader.get_vulnerability_categories_phase1()
                assert "Broken authentication" in vulns
                assert "Mass assignment" in vulns

                # Check high-impact focus
                focus = loader.get_high_impact_focus_phase2()
                assert "UNAUTHORIZED ACCESS" in focus
                assert "ACCESS CONTROL" in focus

                # Check graph types
                graphs = loader.get_graph_types_section()
                assert "EndpointMap" in graphs

            finally:
                os.chdir(original_cwd)

    def test_backwards_compatibility(self):
        """Verify that existing smart contract projects work without changes."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Simulate existing project with no prompts file
                # Clear any environment variables
                os.environ.pop('HOUND_PROMPTS', None)

                # Reload with no file
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Should behave exactly like before
                assert loader.prompts_file is None
                assert "Smart Contract" in loader.get_domain_name()

                # All default methods should work
                assert loader.get_operating_constraints()
                assert loader.get_vulnerability_categories_phase1()
                assert loader.get_high_impact_focus_phase2()
                assert loader.get_mitigation_patterns()
                assert loader.get_graph_types_section()
                assert loader.get_observation_examples()

            finally:
                os.chdir(original_cwd)

    def test_environment_variable_override(self):
        """Test that HOUND_PROMPTS environment variable works correctly."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Create prompts in a specific location
                prompts_path = Path(tmpdir) / 'custom_prompts.md'
                with open(prompts_path, 'w') as f:
                    f.write(WEB_APP_PROMPTS)

                # Set environment variable
                os.environ['HOUND_PROMPTS'] = str(prompts_path)

                # Change to different directory
                os.chdir(Path.home())

                # Reload to pick up environment variable
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Should load from environment variable path
                assert loader.prompts_file.resolve() == prompts_path.resolve()
                assert loader.get_domain_name() == "Web Application Security"

            finally:
                os.environ.pop('HOUND_PROMPTS', None)
                os.chdir(original_cwd)

    def test_environment_variable_priority(self):
        """Test that environment variable takes priority over current directory."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create prompts in current directory
                local_prompts = Path('project_specific_prompts.md')
                with open(local_prompts, 'w') as f:
                    f.write(API_SERVICE_PROMPTS)  # API service

                # Create prompts in another location
                env_prompts = Path(tmpdir) / 'env_prompts.md'
                with open(env_prompts, 'w') as f:
                    f.write(WEB_APP_PROMPTS)  # Web app

                # Set environment variable
                os.environ['HOUND_PROMPTS'] = str(env_prompts)

                # Reload
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Should load from environment variable (not local file)
                assert loader.get_domain_name() == "Web Application Security"
                assert loader.prompts_file.resolve() == env_prompts.resolve()

            finally:
                os.environ.pop('HOUND_PROMPTS', None)
                os.chdir(original_cwd)

    def test_performance_no_slowdown(self):
        """Verify that prompt loading doesn't cause performance issues."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create a reasonably large prompts file
                large_prompts = SMART_CONTRACT_PROMPTS * 10  # Repeat content
                prompts_path = Path('project_specific_prompts.md')
                with open(prompts_path, 'w') as f:
                    f.write(large_prompts)

                # Time the first load (includes parsing)
                reload_prompt_loader()
                start = time.perf_counter()
                loader = get_prompt_loader()
                first_load_time = time.perf_counter() - start

                # Should be very fast (< 100ms)
                assert first_load_time < 0.1, f"First load took {first_load_time:.3f}s"

                # Time subsequent accesses (should be cached)
                start = time.perf_counter()
                for _ in range(100):
                    loader.get_domain_name()
                    loader.get_code_units()
                    loader.get_vulnerability_categories_phase1()
                access_time = time.perf_counter() - start

                # 100 accesses should be nearly instant
                assert access_time < 0.01, f"100 accesses took {access_time:.3f}s"

            finally:
                os.chdir(original_cwd)

    def test_prompt_injection_agent_core(self):
        """Test that prompts are correctly injected into agent_core."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create web app prompts
                prompts_path = Path('project_specific_prompts.md')
                with open(prompts_path, 'w') as f:
                    f.write(WEB_APP_PROMPTS)

                # Reload
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Simulate what agent_core does
                domain_name = loader.get_domain_name()
                constraints = loader.get_operating_constraints()
                observation_examples = loader.get_observation_examples()

                # Verify values are correct for injection
                assert domain_name == "Web Application Security"
                assert "static analysis" in constraints.lower()
                assert "requires auth" in observation_examples

                # Simulate building a prompt
                system_prompt = f"""You are analyzing {domain_name}.

OPERATING CONSTRAINTS:
{constraints}

Example observations: {observation_examples}
"""
                # Verify injection worked
                assert "Web Application Security" in system_prompt
                assert "static analysis" in system_prompt.lower()
                assert "requires auth" in system_prompt

            finally:
                os.chdir(original_cwd)

    def test_prompt_injection_strategist(self):
        """Test that prompts are correctly injected into strategist."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create API service prompts
                prompts_path = Path('project_specific_prompts.md')
                with open(prompts_path, 'w') as f:
                    f.write(API_SERVICE_PROMPTS)

                # Reload
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Phase 1 prompt components
                code_units = loader.get_code_units()
                vuln_categories = loader.get_vulnerability_categories_phase1()

                assert code_units == "API endpoints and services"
                assert "Broken authentication" in vuln_categories
                assert "Mass assignment" in vuln_categories

                # Phase 2 prompt components
                high_impact_focus = loader.get_high_impact_focus_phase2()

                assert "UNAUTHORIZED ACCESS" in high_impact_focus
                assert "ACCESS CONTROL" in high_impact_focus

                # Mitigation patterns
                mitigation_patterns = loader.get_mitigation_patterns()
                assert "authentication middleware" in mitigation_patterns

            finally:
                os.chdir(original_cwd)

    def test_prompt_injection_graph_builder(self):
        """Test that prompts are correctly injected into graph_builder."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create web app prompts
                prompts_path = Path('project_specific_prompts.md')
                with open(prompts_path, 'w') as f:
                    f.write(WEB_APP_PROMPTS)

                # Reload
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Graph types for graph discovery
                graph_types_section = loader.get_graph_types_section()

                assert "RequestFlow" in graph_types_section
                assert "DataValidation" in graph_types_section
                assert "HTTP routing" in graph_types_section

                # Simulate building graph discovery prompt
                prompt = f"""Design graphs for this codebase.

Ideas for strong, analysis-friendly graphs:
{graph_types_section}
"""
                assert "RequestFlow" in prompt
                assert "DataValidation" in prompt

            finally:
                os.chdir(original_cwd)

    def test_multiple_sequential_loads(self):
        """Test switching between different prompts files."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Test 1: Smart contracts
                smart_contract_path = Path('smart_contract_prompts.md')
                with open(smart_contract_path, 'w') as f:
                    f.write(SMART_CONTRACT_PROMPTS)

                os.environ['HOUND_PROMPTS'] = str(smart_contract_path)
                reload_prompt_loader()
                loader = get_prompt_loader()
                assert "Smart Contract Auditing" in loader.get_domain_name()

                # Test 2: Web app
                web_app_path = Path('web_app_prompts.md')
                with open(web_app_path, 'w') as f:
                    f.write(WEB_APP_PROMPTS)

                os.environ['HOUND_PROMPTS'] = str(web_app_path)
                reload_prompt_loader()
                loader = get_prompt_loader()
                assert "Web Application Security" in loader.get_domain_name()

                # Test 3: API service
                api_path = Path('api_prompts.md')
                with open(api_path, 'w') as f:
                    f.write(API_SERVICE_PROMPTS)

                os.environ['HOUND_PROMPTS'] = str(api_path)
                reload_prompt_loader()
                loader = get_prompt_loader()
                assert "API Service Security" in loader.get_domain_name()

            finally:
                os.environ.pop('HOUND_PROMPTS', None)
                os.chdir(original_cwd)

    def test_graceful_degradation_on_parse_error(self):
        """Test that system handles malformed prompts gracefully."""
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)

                # Create malformed prompts file
                malformed_prompts = """This is not properly formatted
No headers or sections
Just random text
"""
                prompts_path = Path('project_specific_prompts.md')
                with open(prompts_path, 'w') as f:
                    f.write(malformed_prompts)

                # Should not crash
                reload_prompt_loader()
                loader = get_prompt_loader()

                # Should fall back to safe defaults
                domain = loader.get_domain_name()
                code_units = loader.get_code_units()

                # Should return something (fallbacks)
                assert domain
                assert code_units

            finally:
                os.chdir(original_cwd)
