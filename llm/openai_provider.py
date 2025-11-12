"""OpenAI provider implementation."""
from __future__ import annotations

import os
import random
import time
from typing import Any, TypeVar

import requests
from openai import OpenAI
from pydantic import BaseModel

from .base_provider import BaseLLMProvider

T = TypeVar('T', bound=BaseModel)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider implementation."""
    
    def __init__(
        self, 
        config: dict[str, Any], 
        model_name: str,
        timeout: int = 120,
        retries: int = 3,
        backoff_min: float = 2.0,
        backoff_max: float = 8.0,
        reasoning_effort: str | None = None,
        text_verbosity: str | None = None,
        verbose: bool | None = None,
        **kwargs
    ):
        """Initialize OpenAI provider."""
        self.config = config
        self.model_name = model_name
        self.timeout = timeout
        self.retries = retries
        self.backoff_min = backoff_min
        self.backoff_max = backoff_max
        self.reasoning_effort = reasoning_effort
        self.text_verbosity = text_verbosity
        # Verbose logging toggle (suppress request logs by default)
        logging_cfg = config.get("logging", {}) if isinstance(config, dict) else {}
        env_verbose = os.environ.get("HOUND_LLM_VERBOSE", "").lower() in {"1","true","yes","on"}
        if verbose is None:
            self.verbose = bool(logging_cfg.get("llm_verbose", False) or env_verbose)
        else:
            self.verbose = bool(verbose)
        self._last_token_usage = None
        
        # Get API key from environment
        api_key_env = config.get("openai", {}).get("api_key_env", "OPENAI_API_KEY")
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"API key not found in environment variable: {api_key_env}")
        self.api_key = api_key
        
        # Allow custom base URL via environment variable; default to public OpenAI endpoint
        # IMPORTANT: OpenAI Python SDK expects base_url to include the "/v1" path.
        # Normalize input so both "https://api.openai.com" and "https://api.openai.com/v1" work.
        raw_base_url = os.environ.get("OPENAI_BASE_URL") or config.get("openai", {}).get("base_url")
        base_url = (raw_base_url or "https://api.openai.com/v1").rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = base_url + "/v1"
        self.base_url = base_url
        self._responses_endpoint_base = f"{self.base_url}/responses"
        
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self._log_verbose(f"[OpenAI Provider] Using base_url: {base_url}")
        # Prefer Responses API for GPT-5 family unless overridden
        mdl = (self.model_name or "").lower()
        env_force_resp = os.environ.get("HOUND_OPENAI_USE_RESPONSES", "").lower() in {"1","true","yes","on"}
        self.use_responses = bool(env_force_resp or mdl.startswith("gpt-5"))
    
    def parse(self, *, system: str, user: str, schema: type[T], reasoning_effort: str | None = None) -> T:
        """Make a structured call. Uses Responses API for GPT-5; otherwise Chat Completions parse."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        
        # Log request details
        request_chars = len(system) + len(user)
        if self.verbose:
            print("\n[OpenAI Request]")
            print(f"  Model: {self.model_name}")
            print(f"  Schema: {schema.__name__}")
            print(f"  Total prompt: {request_chars:,} chars (~{request_chars//4:,} tokens)")
        self._log_verbose(f"  Path: {'Responses API' if self.use_responses else 'Chat Completions'}")
        
        last_err = None
        
        for attempt in range(self.retries):
            try:
                time.time()
                if self.verbose:
                    print(f"  Attempt {attempt + 1}/{self.retries}...")
                if self.use_responses:
                    # Responses API without server-side schema; we instruct strict JSON and validate locally
                    text_params: dict[str, Any] = {}
                    if self.text_verbosity:
                        text_params['verbosity'] = self.text_verbosity
                    # Embed schema hint in instructions to increase compliance
                    try:
                        json_schema = schema.model_json_schema()
                    except Exception:
                        try:
                            json_schema = schema.schema()
                        except Exception:
                            json_schema = None
                    schema_hint = ""
                    if isinstance(json_schema, dict):
                        import json as _json
                        schema_hint = "\nFollow this JSON schema exactly (no extra keys, all required):\n" + _json.dumps(json_schema)
                    strict_instr = "\nReturn ONLY valid JSON. No markdown. No prose."
                    instructions = (system or '') + schema_hint + strict_instr
                    payload: dict[str, Any] = {
                        'model': self.model_name,
                        'input': user,
                        'instructions': instructions,
                        'background': bool(self._openai_setting('responses_background', True)),
                        'store': bool(self._openai_setting('responses_store', True)),
                    }
                    if text_params:
                        payload['text'] = text_params
                    eff = reasoning_effort or self.reasoning_effort
                    if eff:
                        payload['reasoning'] = {'effort': eff}
                    self._log_api_invocation(api_path="Responses API (parse)", attempt=attempt + 1)
                    result = self._run_responses_job(payload)
                    usage = result.get('usage')
                    if isinstance(usage, dict):
                        self._last_token_usage = {
                            'input_tokens': usage.get('input_tokens', 0) or 0,
                            'output_tokens': usage.get('output_tokens', 0) or 0,
                            'total_tokens': usage.get('total_tokens', 0) or 0,
                        }
                    output_text = self._extract_output_text(result)
                    if not output_text:
                        raise RuntimeError("No output text in response payload")
                    return schema.model_validate_json(output_text)
                else:
                    # Chat Completions structured output path
                    self._log_api_invocation(api_path="Chat Completions parse", attempt=attempt + 1)
                    completion = self.client.beta.chat.completions.parse(
                        model=self.model_name,
                        messages=messages,
                        response_format=schema,
                        timeout=self.timeout
                    )
                    if hasattr(completion, 'usage') and completion.usage:
                        self._last_token_usage = {
                            'input_tokens': completion.usage.prompt_tokens or 0,
                            'output_tokens': completion.usage.completion_tokens or 0,
                            'total_tokens': completion.usage.total_tokens or 0
                        }
                    if completion.choices[0].message.parsed:
                        return completion.choices[0].message.parsed
                    elif completion.choices[0].message.refusal:
                        raise RuntimeError(f"Model refused: {completion.choices[0].message.refusal}")
                    else:
                        json_str = completion.choices[0].message.content
                        return schema.model_validate_json(json_str)
                    
            except Exception as e:
                last_err = e
                if self.verbose:
                    print(f"  Error: {e}")
                if attempt < self.retries - 1:
                    sleep_time = random.uniform(self.backoff_min, self.backoff_max)
                    if self.verbose:
                        print(f"  Retrying after {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
        
        raise RuntimeError(f"OpenAI call failed after {self.retries} attempts: {last_err}")
    
    def raw(self, *, system: str, user: str, reasoning_effort: str | None = None) -> str:
        """Make a plain text call."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        
        last_err = None
        for attempt in range(self.retries):
            try:
                if self.verbose:
                    try:
                        print(f"[OpenAI raw] Attempt {attempt + 1}/{self.retries} ({'Responses' if self.use_responses else 'Chat Completions'})")
                    except Exception:
                        pass
                if self.use_responses:
                    # Favor JSON output only when caller explicitly asks for strict JSON in the system message.
                    # This keeps deep_think and other free-text prompts working as normal text.
                    text_params: dict[str, Any] = {}
                    if self.text_verbosity:
                        text_params['verbosity'] = self.text_verbosity
                    payload: dict[str, Any] = {
                        'model': self.model_name,
                        'input': user,
                        'instructions': system or '',
                        'background': bool(self._openai_setting('responses_background', True)),
                        'store': bool(self._openai_setting('responses_store', True)),
                    }
                    # Heuristic: if system asks for "valid JSON", request json_object formatting.
                    try:
                        if isinstance(system, str) and 'valid json' in system.lower():
                            text_params['format'] = {'type': 'json_object'}
                    except Exception:
                        pass
                    if text_params:
                        payload['text'] = text_params
                    eff = reasoning_effort or self.reasoning_effort
                    if eff:
                        payload['reasoning'] = {'effort': eff}
                    self._log_api_invocation(api_path="Responses API (raw)", attempt=attempt + 1)
                    result = self._run_responses_job(payload)
                    usage = result.get('usage')
                    if isinstance(usage, dict):
                        self._last_token_usage = {
                            'input_tokens': usage.get('input_tokens', 0) or 0,
                            'output_tokens': usage.get('output_tokens', 0) or 0,
                            'total_tokens': usage.get('total_tokens', 0) or 0,
                        }
                    out = self._extract_output_text(result)
                    if out:
                        return out
                    return ""
                else:
                    self._log_api_invocation(api_path="Chat Completions raw", attempt=attempt + 1)
                    completion = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        timeout=self.timeout
                    )
                    # Store token usage
                    if hasattr(completion, 'usage') and completion.usage:
                        self._last_token_usage = {
                            'input_tokens': completion.usage.prompt_tokens or 0,
                            'output_tokens': completion.usage.completion_tokens or 0,
                            'total_tokens': completion.usage.total_tokens or 0
                        }
                    return completion.choices[0].message.content
            except Exception as e:
                last_err = e
                if attempt < self.retries - 1:
                    sleep_time = random.uniform(self.backoff_min, self.backoff_max)
                    time.sleep(sleep_time)
        
        raise RuntimeError(f"OpenAI raw call failed after {self.retries} attempts: {last_err}")

    def _log_verbose(self, message: str) -> None:
        """Print verbose logs while tolerating stdout failures."""
        if self.verbose:
            try:
                print(message)
            except Exception:
                pass

    def _log_api_invocation(self, *, api_path: str, attempt: int) -> None:
        """Emit a debug log right before an API call when verbose mode is enabled."""
        if not self.verbose:
            return
        total = self.retries if self.retries else attempt
        self._log_verbose(
            f"[OpenAI Provider] Attempt {attempt}/{total}: calling {api_path} (model={self.model_name})"
        )

    def _responses_endpoint(self, suffix: str | None = None) -> str:
        """Build a full /responses endpoint URL with optional suffix."""
        if suffix:
            suffix = suffix.lstrip("/")
            return f"{self._responses_endpoint_base.rstrip('/')}/{suffix}"
        return self._responses_endpoint_base

    def _build_request_headers(self) -> dict[str, str]:
        """Construct Authorization + Content-Type headers for direct HTTP calls."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _openai_setting(self, key: str, default: Any) -> Any:
        """Fetch a key from config['openai'] with a default fallback."""
        if isinstance(self.config, dict):
            openai_cfg = self.config.get("openai", {})
            if isinstance(openai_cfg, dict):
                return openai_cfg.get(key, default)
        return default

    def _responses_transient_log_interval(self) -> float:
        """Return seconds between verbose transient-status updates."""
        raw_interval = self._openai_setting("responses_transient_status_log_interval_sec", 300.0)
        try:
            interval = float(raw_interval)
        except (TypeError, ValueError):
            interval = 300.0
        if interval <= 0:
            interval = 300.0
        return interval

    def _safe_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Thin wrapper around requests.request with consistent headers + error handling."""
        headers = kwargs.pop("headers", None) or self._build_request_headers()
        timeout = kwargs.pop("timeout", self.timeout)
        try:
            response = requests.request(method=method, url=url, headers=headers, timeout=timeout, **kwargs)
        except requests.RequestException as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc
        if response.status_code != 200:
            self._handle_http_error(response)
        return response

    def _handle_http_error(self, response: requests.Response) -> None:
        """Raise a descriptive RuntimeError using API payload when available."""
        detail: str | None = None
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                detail = err.get("message") or err.get("type")
        msg = detail or f"{response.status_code} {response.reason}"
        raise RuntimeError(f"OpenAI HTTP error: {msg}")

    @staticmethod
    def _extract_output_text(response_json: dict[str, Any]) -> str:
        """Mirror gpt-5 helper to reconstruct text output from Responses payloads."""
        output = response_json.get("output")
        if not isinstance(output, list):
            return ""
        texts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                # Prefer explicit output_text type, but fall back to plain text entries.
                if part.get("type") == "output_text":
                    text_value = part.get("text")
                    if isinstance(text_value, str):
                        texts.append(text_value)
                elif part.get("type") == "text":
                    text_obj = part.get("text")
                    if isinstance(text_obj, str):
                        texts.append(text_obj)
                    elif isinstance(text_obj, dict):
                        value = text_obj.get("value")
                        if isinstance(value, str):
                            texts.append(value)
        return "\n".join(t.strip() for t in texts if t).strip()

    def _run_responses_job(
        self,
        payload: dict[str, Any],
        *,
        poll_interval: float | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Start a Responses job and poll until it reaches a terminal status."""
        default_interval = self._openai_setting("responses_poll_interval_sec", 4.0)
        try:
            interval = float(poll_interval if poll_interval is not None else default_interval)
        except (TypeError, ValueError):
            interval = 4.0
        if interval <= 0:
            interval = 4.0
        
        total_timeout = timeout if timeout is not None else self.timeout
        deadline: float | None = None
        try:
            total_timeout_float = float(total_timeout)
            if total_timeout_float > 0:
                deadline = time.monotonic() + total_timeout_float
        except (TypeError, ValueError):
            deadline = None
        
        def _parse_json(resp: requests.Response, ctx: str) -> dict[str, Any]:
            try:
                data = resp.json()
            except ValueError as exc:
                raise RuntimeError(f"Invalid JSON from OpenAI {ctx}") from exc
            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected payload from OpenAI {ctx}")
            return data
        
        current = _parse_json(self._safe_request("POST", self._responses_endpoint(), json=payload), "responses POST")
        resp_id = current.get("id")
        if not isinstance(resp_id, str):
            raise RuntimeError("OpenAI responses payload missing id")
        
        terminal_statuses = {"completed", "failed", "cancelled", "incomplete"}
        transient_statuses = {"queued", "in_progress"}
        first_transient_ts: float | None = None
        last_transient_notice: float | None = None
        transient_notice_interval = self._responses_transient_log_interval()
        
        while True:
            status_raw = current.get("status")
            status = status_raw.lower() if isinstance(status_raw, str) else "unknown"
            self._log_verbose(f"    Responses status: {status}")
            if status in transient_statuses:
                now = time.monotonic()
                if first_transient_ts is None:
                    first_transient_ts = now
                    last_transient_notice = now
                elif last_transient_notice is None:
                    last_transient_notice = now
                elif self.verbose and (now - last_transient_notice) >= transient_notice_interval:
                    elapsed_minutes = (now - (first_transient_ts or now)) / 60
                    self._log_verbose(
                        f"[OpenAI Provider] Responses job '{resp_id}' still {status} for model {self.model_name} "
                        f"after {elapsed_minutes:.1f} minutes"
                    )
                    last_transient_notice = now
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError("Timed out while polling OpenAI responses job")
                sleep_for = interval
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("Timed out while polling OpenAI responses job")
                    sleep_for = min(interval, remaining)
                time.sleep(sleep_for)
                current = _parse_json(
                    self._safe_request("GET", self._responses_endpoint(resp_id)),
                    "responses GET",
                )
                continue
            
            if status not in terminal_statuses:
                raise RuntimeError(f"Unknown OpenAI responses status: {status}")
            
            if status == "completed":
                return current
            
            if status == "failed":
                err = current.get("error")
                detail = None
                if isinstance(err, dict):
                    detail = err.get("message") or err.get("code") or err.get("type")
                raise RuntimeError(f"OpenAI responses job failed: {detail or 'failed'}")
            
            if status == "cancelled":
                raise RuntimeError("OpenAI responses job cancelled")
            
            if status == "incomplete":
                inc = current.get("incomplete_details")
                detail = None
                if isinstance(inc, dict):
                    detail = inc.get("message") or inc.get("reason")
                raise RuntimeError(f"OpenAI responses job incomplete: {detail or 'unknown reason'}")

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "OpenAI"
    
    @property
    def supports_thinking(self) -> bool:
        """OpenAI models may support reasoning effort but not explicit thinking mode."""
        return False
    
    def get_last_token_usage(self) -> dict[str, int] | None:
        """Return token usage from the last call if available."""
        return self._last_token_usage
