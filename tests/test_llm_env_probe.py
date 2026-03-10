"""Full test suite: probe_llm_env + LM Studio + Ollama."""
from __future__ import annotations
import json, os, socket, sys, types
from unittest.mock import MagicMock, patch
import pytest

# ── Stub for relative import inside llm_env_probe ────────────────
from pydantic import BaseModel

class LLMEndpoint(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    temperature: float = 0.3
    max_tokens: int = 4096
    rate_limit_delay: float = 2.0
    @property
    def api_key(self): return os.getenv(self.api_key_env, "")

_src = types.ModuleType("src")
_cfg = types.ModuleType("src.config")
_cfg.LLMEndpoint = LLMEndpoint
sys.modules["src"] = _src
sys.modules["src.config"] = _cfg

import importlib.util
spec = importlib.util.spec_from_file_location("llm_env_probe_t", "/home/claude/llm_env_probe_new.py")
_mod = importlib.util.module_from_spec(spec)
_mod.__package__ = "src"
sys.modules["llm_env_probe_t"] = _mod
spec.loader.exec_module(_mod)

probe_llm_env          = _mod.probe_llm_env
apply_env_override     = _mod.apply_env_override
format_setup_guidance  = _mod.format_setup_guidance
check_lm_studio_available = _mod.check_lm_studio_available
check_ollama_available    = _mod.check_ollama_available
DetectedEndpoint          = _mod.DetectedEndpoint


# ── Helpers ───────────────────────────────────────────────────────
def ep(**kw):
    return LLMEndpoint(**{"api_key_env": "NONEXISTENT_XYZ", **kw})

def mk_resp(body: str):
    r = MagicMock()
    r.read.return_value = body.encode()
    r.__enter__ = lambda s: r
    r.__exit__ = MagicMock(return_value=False)
    return r

MODELS_JSON = '{"data": [{"id": "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF"}]}'
EMPTY_JSON  = '{"data": []}'


# ═══════════════════════════════════════════════════════════════════
# 1. config.yaml priority
# ═══════════════════════════════════════════════════════════════════
class TestConfigYaml:
    def test_valid_key_first(self):
        with patch.dict(os.environ, {"MY_KEY": "real-key"}, clear=True):
            r, src = probe_llm_env(ep(api_key_env="MY_KEY"))
        assert r.api_key == "real-key" and "config.yaml" in src

    def test_beats_openclaw(self):
        env = {"MY_KEY": "cfg", "OPENCLAW_API_KEY": "oc",
               "OPENCLAW_BASE_URL": "https://x/v1", "OPENCLAW_MODEL": "m"}
        with patch.dict(os.environ, env, clear=True):
            r, _ = probe_llm_env(ep(api_key_env="MY_KEY"))
        assert r.api_key == "cfg"

    @pytest.mark.parametrize("p", ["REPLACE_ME", "your-key-here", ""])
    def test_placeholder_skipped(self, p):
        env = {"MY_KEY": p, "ZAI_API_KEY": "zai"}
        with patch.dict(os.environ, env, clear=True):
            r, _ = probe_llm_env(ep(api_key_env="MY_KEY"))
        assert r and r.api_key == "zai"

    def test_empty_base_url_falls_through(self):
        e = LLMEndpoint(api_key_env="MY_KEY", provider="x", base_url="", model="m")
        with patch.dict(os.environ, {"MY_KEY": "k", "OPENAI_API_KEY": "fb"}, clear=True):
            r, _ = probe_llm_env(e)
        assert r.api_key == "fb"

    def test_empty_model_falls_through(self):
        e = LLMEndpoint(api_key_env="MY_KEY", provider="x",
                        base_url="https://x/v1", model="")
        with patch.dict(os.environ, {"MY_KEY": "k", "DEEPSEEK_API_KEY": "ds"}, clear=True):
            r, _ = probe_llm_env(e)
        assert r.api_key == "ds"


# ═══════════════════════════════════════════════════════════════════
# 2. Agent frameworks
# ═══════════════════════════════════════════════════════════════════
class TestOpenClaw:
    def test_full(self):
        env = {"OPENCLAW_API_KEY": "oc",
               "OPENCLAW_BASE_URL": "https://x/v1", "OPENCLAW_MODEL": "m"}
        with patch.dict(os.environ, env, clear=True):
            r, src = probe_llm_env(ep())
        assert r.api_key == "oc" and "OpenClaw" in src

    def test_no_base_url_skipped(self):
        env = {"OPENCLAW_API_KEY": "oc", "OPENCLAW_MODEL": "m", "ZAI_API_KEY": "zai"}
        with patch.dict(os.environ, env, clear=True):
            r, _ = probe_llm_env(ep())
        assert r.api_key == "zai"

    def test_no_model_skipped(self):
        env = {"OPENCLAW_API_KEY": "oc", "OPENCLAW_BASE_URL": "https://x/v1",
               "OPENAI_API_KEY": "oai"}
        with patch.dict(os.environ, env, clear=True):
            r, _ = probe_llm_env(ep())
        assert r.api_key == "oai"


class TestOpencode:
    def test_full(self):
        env = {"OPENCODE_API_KEY": "oc2",
               "OPENCODE_BASE_URL": "https://x/v1", "OPENCODE_MODEL": "m"}
        with patch.dict(os.environ, env, clear=True):
            r, src = probe_llm_env(ep())
        assert r.api_key == "oc2" and "Opencode" in src

    def test_no_base_url_skipped(self):
        env = {"OPENCODE_API_KEY": "oc2", "OPENCODE_MODEL": "m",
               "DEEPSEEK_API_KEY": "ds"}
        with patch.dict(os.environ, env, clear=True):
            r, _ = probe_llm_env(ep())
        assert r.api_key == "ds"


class TestClaudeCode:
    def test_detected(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant"}, clear=True):
            r, src = probe_llm_env(ep())
        assert r.api_key == "sk-ant" and r.provider == "anthropic"

    def test_default_base_url(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk"}, clear=True):
            r, _ = probe_llm_env(ep())
        assert "anthropic.com" in r.base_url

    def test_custom_model(self):
        with patch.dict(os.environ,
                        {"ANTHROPIC_API_KEY": "sk", "ANTHROPIC_MODEL": "claude-opus-4-6"},
                        clear=True):
            r, _ = probe_llm_env(ep())
        assert r.model == "claude-opus-4-6"

    def test_custom_base_url(self):
        with patch.dict(os.environ,
                        {"ANTHROPIC_API_KEY": "sk", "ANTHROPIC_BASE_URL": "https://proxy/v1"},
                        clear=True):
            r, _ = probe_llm_env(ep())
        assert r.base_url == "https://proxy/v1"


# ═══════════════════════════════════════════════════════════════════
# 3. Generic providers
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("env_var,provider", [
    ("ZAI_API_KEY", "zai"),
    ("OPENAI_API_KEY", "openai"),
    ("DEEPSEEK_API_KEY", "deepseek"),
    ("ARK_API_KEY", "volcengine"),
    ("OPENROUTER_API_KEY", "openrouter"),
])
def test_generic_provider(env_var, provider):
    with patch.dict(os.environ, {env_var: "key"}, clear=True):
        r, _ = probe_llm_env(ep())
    assert r and r.provider == provider

def test_custom_model_via_env():
    with patch.dict(os.environ,
                    {"OPENAI_API_KEY": "sk", "OPENAI_MODEL": "gpt-4-turbo"},
                    clear=True):
        r, _ = probe_llm_env(ep())
    assert r.model == "gpt-4-turbo"


# ═══════════════════════════════════════════════════════════════════
# 4. Priority order
# ═══════════════════════════════════════════════════════════════════
class TestPriority:
    def test_openclaw_beats_anthropic(self):
        env = {"OPENCLAW_API_KEY": "oc", "OPENCLAW_BASE_URL": "https://x/v1",
               "OPENCLAW_MODEL": "m", "ANTHROPIC_API_KEY": "ant"}
        with patch.dict(os.environ, env, clear=True):
            r, _ = probe_llm_env(ep())
        assert r.api_key == "oc"

    def test_anthropic_beats_openai(self):
        with patch.dict(os.environ,
                        {"ANTHROPIC_API_KEY": "ant", "OPENAI_API_KEY": "oai"},
                        clear=True):
            r, _ = probe_llm_env(ep())
        assert r.api_key == "ant"

    def test_zai_beats_openai(self):
        with patch.dict(os.environ,
                        {"ZAI_API_KEY": "zai", "OPENAI_API_KEY": "oai"},
                        clear=True):
            r, _ = probe_llm_env(ep())
        assert r.api_key == "zai"

    def test_cloud_key_beats_lm_studio(self):
        """A cloud API key must take priority over a local LM Studio server."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-cloud"}, clear=True):
            # Even if LM Studio would be reachable, cloud key wins
            with patch.object(_mod, "check_lm_studio_available",
                               return_value=DetectedEndpoint(
                                   "lm_studio", "lm-studio",
                                   "http://localhost:1234/v1", "llama",
                                   "LM Studio (local)", "")):
                r, src = probe_llm_env(ep())
        assert r.api_key == "sk-cloud"  # cloud wins
        assert "LM Studio" not in src

    def test_lm_studio_beats_ollama(self):
        """LM Studio is checked before Ollama."""
        lms = DetectedEndpoint("lm_studio", "lm-studio",
                               "http://localhost:1234/v1", "llama",
                               "LM Studio (local)", "")
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(_mod, "check_lm_studio_available", return_value=lms):
                with patch.object(_mod, "check_ollama_available",
                                  return_value=DetectedEndpoint(
                                      "ollama", "no-key",
                                      "http://localhost:11434/v1", "llama3.1",
                                      "Ollama (local)", "")):
                    r, src = probe_llm_env(ep())
        assert r.provider == "lm_studio"


# ═══════════════════════════════════════════════════════════════════
# 5. No key found
# ═══════════════════════════════════════════════════════════════════
def test_no_key_returns_none():
    with patch.dict(os.environ, {}, clear=True):
        with patch.object(_mod, "check_lm_studio_available", return_value=None):
            with patch.object(_mod, "check_ollama_available", return_value=None):
                r, reason = probe_llm_env(ep())
    assert r is None and "No LLM API key found" in reason

def test_reason_lists_env_vars():
    with patch.dict(os.environ, {}, clear=True):
        with patch.object(_mod, "check_lm_studio_available", return_value=None):
            with patch.object(_mod, "check_ollama_available", return_value=None):
                _, reason = probe_llm_env(ep())
    assert "OPENAI_API_KEY" in reason and "ARK_API_KEY" in reason

def test_none_endpoint_arg():
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "ds"}, clear=True):
        r, _ = probe_llm_env(None)
    assert r and r.api_key == "ds"


# ═══════════════════════════════════════════════════════════════════
# 6. LM Studio
# ═══════════════════════════════════════════════════════════════════
class TestLMStudio:
    def test_detected_with_model(self):
        with patch("urllib.request.urlopen", return_value=mk_resp(MODELS_JSON)):
            r = check_lm_studio_available()
        assert r is not None
        assert r.provider == "lm_studio"
        assert r.base_url == "http://localhost:1234/v1"
        assert r.api_key == "lm-studio"
        assert "Meta-Llama" in r.model
        assert "LM Studio" in r.source

    def test_model_from_env_overrides_api(self):
        with patch.dict(os.environ, {"LM_STUDIO_MODEL": "my-model"}):
            with patch("urllib.request.urlopen", return_value=mk_resp(MODELS_JSON)):
                r = check_lm_studio_available()
        assert r.model == "my-model"

    def test_fallback_model_when_empty_list(self):
        env = {k: v for k, v in os.environ.items() if k != "LM_STUDIO_MODEL"}
        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.urlopen", return_value=mk_resp(EMPTY_JSON)):
                r = check_lm_studio_available()
        assert r is not None and r.model == "lm-studio-loaded-model"

    def test_none_when_server_down(self):
        with patch("urllib.request.urlopen", side_effect=OSError("refused")):
            assert check_lm_studio_available() is None

    def test_none_on_timeout(self):
        with patch("urllib.request.urlopen", side_effect=socket.timeout()):
            assert check_lm_studio_available() is None

    def test_custom_base_url(self):
        custom = "http://192.168.1.5:1234/v1"
        with patch.dict(os.environ, {"LM_STUDIO_BASE_URL": custom}):
            with patch("urllib.request.urlopen", return_value=mk_resp(MODELS_JSON)):
                r = check_lm_studio_available()
        assert r.base_url == custom

    def test_malformed_json_uses_fallback(self):
        env = {k: v for k, v in os.environ.items() if k != "LM_STUDIO_MODEL"}
        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.urlopen", return_value=mk_resp("not-json")):
                r = check_lm_studio_available()
        assert r is not None and r.model == "lm-studio-loaded-model"

    def test_no_api_key_env_field(self):
        with patch("urllib.request.urlopen", return_value=mk_resp(MODELS_JSON)):
            r = check_lm_studio_available()
        assert r.api_key_env == ""

    def test_trailing_slash_stripped(self):
        with patch.dict(os.environ, {"LM_STUDIO_BASE_URL": "http://localhost:1234/v1/"}):
            with patch("urllib.request.urlopen", return_value=mk_resp(MODELS_JSON)) as m:
                check_lm_studio_available()
        called_url = m.call_args[0][0]
        assert not called_url.endswith("//models"), f"double slash in {called_url}"


# ═══════════════════════════════════════════════════════════════════
# 7. Ollama
# ═══════════════════════════════════════════════════════════════════
class TestOllama:
    def test_detected(self):
        with patch("urllib.request.urlopen", return_value=MagicMock()):
            r = check_ollama_available()
        assert r and r.provider == "ollama"
        assert "11434" in r.base_url

    def test_model_from_env(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "mistral"}):
            with patch("urllib.request.urlopen", return_value=MagicMock()):
                r = check_ollama_available()
        assert r.model == "mistral"

    def test_default_model(self):
        env = {k: v for k, v in os.environ.items() if k != "OLLAMA_MODEL"}
        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.urlopen", return_value=MagicMock()):
                r = check_ollama_available()
        assert r.model == "llama3.1"

    def test_none_when_down(self):
        with patch("urllib.request.urlopen", side_effect=OSError()):
            assert check_ollama_available() is None

    def test_custom_base_url(self):
        custom = "http://remote:11434/v1"
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": custom}):
            with patch("urllib.request.urlopen", return_value=MagicMock()):
                r = check_ollama_available()
        assert r.base_url == custom


# ═══════════════════════════════════════════════════════════════════
# 8. apply_env_override
# ═══════════════════════════════════════════════════════════════════
class TestApplyOverride:
    def test_overrides_no_config_key(self):
        cfg = MagicMock(); cfg.llm.text = ep()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "oai"}, clear=True):
            ok, _ = apply_env_override(cfg)
        assert ok and cfg.llm.text.api_key_env == "OPENAI_API_KEY"

    def test_preserves_tuning_params(self):
        orig = LLMEndpoint(api_key_env="NONEXISTENT_XYZ",
                           temperature=0.7, max_tokens=8192, rate_limit_delay=1.5)
        cfg = MagicMock(); cfg.llm.text = orig
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "ds"}, clear=True):
            apply_env_override(cfg)
        assert cfg.llm.text.temperature == 0.7
        assert cfg.llm.text.max_tokens == 8192
        assert cfg.llm.text.rate_limit_delay == 1.5

    def test_returns_false_no_key(self):
        cfg = MagicMock(); cfg.llm.text = ep()
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(_mod, "check_lm_studio_available", return_value=None):
                with patch.object(_mod, "check_ollama_available", return_value=None):
                    ok, reason = apply_env_override(cfg)
        assert not ok and "No LLM API key found" in reason


# ═══════════════════════════════════════════════════════════════════
# 9. format_setup_guidance
# ═══════════════════════════════════════════════════════════════════
class TestGuidance:
    def test_has_setup_command(self):
        assert "jobhunter --setup" in format_setup_guidance()

    def test_mentions_lm_studio(self):
        assert "LM Studio" in format_setup_guidance()

    def test_mentions_lm_studio_url(self):
        assert "lmstudio.ai" in format_setup_guidance()

    def test_mentions_ollama(self):
        assert "Ollama" in format_setup_guidance() or "ollama" in format_setup_guidance()

    def test_mentions_key_env_vars(self):
        msg = format_setup_guidance()
        for v in ("ZAI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"):
            assert v in msg

    def test_mentions_agent_frameworks(self):
        msg = format_setup_guidance()
        assert "OpenClaw" in msg and "Opencode" in msg

    def test_mentions_lm_studio_model_override(self):
        assert "LM_STUDIO_MODEL" in format_setup_guidance()

    def test_mentions_ollama_model_override(self):
        assert "OLLAMA_MODEL" in format_setup_guidance()
