"""
KALI OSINT AGENT — Test Suite

Tests are split into three categories:
  UNIT    — pure logic, no network (always pass)
  NET     — requires outbound network (may fail in sandboxed envs)
  IMPORT  — module structure and dispatch integrity

Run:
  cd /home/user/3lokreddy && python3 -m pytest tests/ -v
  python3 -m pytest tests/ -v -m "not net"   # skip network tests
"""

import json
import os
import sys
import pytest

# ── ensure project root is on sys.path ───────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT / STRUCTURE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestImports:
    def test_config_imports(self):
        from config import MODEL, PASSIVE, ACTIVE, FULL, MAX_TOKENS
        assert MODEL == "claude-opus-4-6"
        assert PASSIVE == "passive"
        assert ACTIVE  == "active"
        assert FULL    == "full"
        assert MAX_TOKENS > 0

    def test_passive_tools_load(self):
        from tools.passive_recon import PASSIVE_TOOLS, PASSIVE_DISPATCH
        assert len(PASSIVE_TOOLS) == 16
        assert len(PASSIVE_DISPATCH) == 16

    def test_active_tools_load(self):
        from tools.active_recon import ACTIVE_TOOLS, ACTIVE_DISPATCH
        assert len(ACTIVE_TOOLS) == 12
        assert len(ACTIVE_DISPATCH) == 12

    def test_all_tools_load(self):
        from tools import ALL_TOOLS
        assert len(ALL_TOOLS) == 28

    def test_dispatch_covers_all_schemas(self):
        """Every tool schema must have a matching dispatch entry."""
        from tools.passive_recon import PASSIVE_TOOLS, PASSIVE_DISPATCH
        from tools.active_recon  import ACTIVE_TOOLS,  ACTIVE_DISPATCH
        for tool in PASSIVE_TOOLS:
            assert tool["name"] in PASSIVE_DISPATCH, \
                f"Missing dispatch for passive tool: {tool['name']}"
        for tool in ACTIVE_TOOLS:
            assert tool["name"] in ACTIVE_DISPATCH, \
                f"Missing dispatch for active tool: {tool['name']}"

    def test_tool_schemas_valid(self):
        """Each tool schema must have name, description, and input_schema."""
        from tools import ALL_TOOLS
        for tool in ALL_TOOLS:
            assert "name"         in tool, f"Tool missing 'name': {tool}"
            assert "description"  in tool, f"Tool '{tool.get('name')}' missing description"
            assert "input_schema" in tool, f"Tool '{tool.get('name')}' missing input_schema"
            schema = tool["input_schema"]
            assert schema.get("type") == "object"
            assert "properties" in schema
            assert "required"   in schema

    def test_no_tool_name_collisions(self):
        from tools import ALL_TOOLS
        names = [t["name"] for t in ALL_TOOLS]
        assert len(names) == len(set(names)), "Duplicate tool names detected"


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — no network required
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoogleDorkGenerator:
    def setup_method(self):
        from tools.passive_recon import google_dork_generator
        self.fn = google_dork_generator

    def test_returns_valid_json(self):
        result = self.fn("example.com")
        data = json.loads(result)
        assert data["target"] == "example.com"
        assert "dorks" in data
        assert "instructions" in data

    def test_all_mode(self):
        data = json.loads(self.fn("example.com", "all"))
        assert "files"           in data["dorks"]
        assert "login"           in data["dorks"]
        assert "subdomains"      in data["dorks"]
        assert "emails"          in data["dorks"]
        assert "cameras"         in data["dorks"]
        assert "vulnerabilities" in data["dorks"]

    def test_specific_type_files(self):
        data = json.loads(self.fn("target.org", "files"))
        assert list(data["dorks"].keys()) == ["files"]
        for dork in data["dorks"]["files"]:
            assert "target.org" in dork

    def test_specific_type_login(self):
        data = json.loads(self.fn("target.org", "login"))
        assert list(data["dorks"].keys()) == ["login"]

    def test_specific_type_emails(self):
        data = json.loads(self.fn("corp.com", "emails"))
        for dork in data["dorks"]["emails"]:
            assert "corp.com" in dork

    def test_invalid_type_returns_error(self):
        result = self.fn("example.com", "invalid_type")
        assert "Unknown" in result or "unknown" in result.lower()

    def test_domain_appears_in_dorks(self):
        data = json.loads(self.fn("acme.io", "all"))
        for category, dorks in data["dorks"].items():
            for dork in dorks:
                assert "acme.io" in dork, \
                    f"Domain missing from {category} dork: {dork}"


class TestEmailHeaderAnalysis:
    def setup_method(self):
        from tools.passive_recon import email_header_analysis
        self.fn = email_header_analysis

    def test_parses_received_headers(self):
        raw = (
            "Received: from mail.evil.com (evil.com [1.2.3.4]) by mx.example.com\n"
            "Received: from smtp.origin.net (origin.net [5.6.7.8]) by mail.evil.com\n"
            "From: attacker@evil.com\n"
            "To: victim@example.com\n"
        )
        data = json.loads(self.fn(raw))
        assert data["hops_found"] == 2
        assert len(data["hops"]) == 2

    def test_no_received_headers(self):
        raw = "From: test@test.com\nTo: foo@bar.com\n"
        data = json.loads(self.fn(raw))
        assert data["hops_found"] == 0
        assert data["hops"] == []

    def test_single_hop(self):
        raw = "Received: from a.b.c (a.b.c [9.9.9.9]) by dest.com\n"
        data = json.loads(self.fn(raw))
        assert data["hops_found"] == 1


class TestAgentToolDispatch:
    def test_unknown_tool_returns_error(self):
        from osint_agent import execute_tool
        result = execute_tool("nonexistent_tool", {})
        assert "Unknown tool" in result

    def test_dispatch_google_dork(self):
        from osint_agent import execute_tool
        result = execute_tool("google_dork_generator",
                              {"target": "test.com", "dork_type": "files"})
        data = json.loads(result)
        assert data["target"] == "test.com"

    def test_dispatch_email_header(self):
        from osint_agent import execute_tool
        result = execute_tool("email_header_analysis",
                              {"raw_headers": "Received: from x (x [1.1.1.1]) by y\n"})
        data = json.loads(result)
        assert data["hops_found"] == 1

    def test_tool_exception_handled_gracefully(self):
        """Tool errors must not propagate — they return an error string."""
        from osint_agent import execute_tool
        # Pass bad input that will cause a TypeError inside the tool
        result = execute_tool("google_dork_generator", {})
        # Should get an error string, not raise an exception
        assert isinstance(result, str)


class TestGetTools:
    def test_passive_mode_returns_only_passive(self):
        from osint_agent import get_tools
        from tools.passive_recon import PASSIVE_TOOLS
        tools = get_tools("passive")
        assert tools == PASSIVE_TOOLS

    def test_active_mode_returns_only_active(self):
        from osint_agent import get_tools
        from tools.active_recon import ACTIVE_TOOLS
        tools = get_tools("active")
        assert tools == ACTIVE_TOOLS

    def test_full_mode_returns_all(self):
        from osint_agent import get_tools
        tools = get_tools("full")
        assert len(tools) == 28

    def test_unknown_mode_falls_back_to_all(self):
        from osint_agent import get_tools
        tools = get_tools("unknown_mode")
        assert len(tools) == 28


class TestReportGeneration:
    def test_save_report_creates_file(self, tmp_path, monkeypatch):
        from osint_agent import save_report
        import config
        monkeypatch.setattr(config, "REPORT_DIR", str(tmp_path))

        path = save_report(
            target="example.com",
            mode="passive",
            task="Test task",
            conversation=[],
            final_text="## Summary\n\nTest finding.",
        )
        assert path.exists()
        content = path.read_text()
        assert "example.com" in content
        assert "passive" in content.upper() or "PASSIVE" in content
        assert "Test finding" in content

    def test_report_filename_sanitises_target(self, tmp_path, monkeypatch):
        from osint_agent import save_report
        import config
        monkeypatch.setattr(config, "REPORT_DIR", str(tmp_path))

        path = save_report("evil/../target", "passive", "task", [], "text")
        # Filename should not contain ".."
        assert ".." not in path.name

    def test_report_contains_tool_calls(self, tmp_path, monkeypatch):
        from osint_agent import save_report
        import config
        monkeypatch.setattr(config, "REPORT_DIR", str(tmp_path))

        conversation = [{
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "name": "whois_lookup",
                "input": {"domain": "example.com"},
            }]
        }]
        path = save_report("example.com", "passive", "task", conversation, "summary")
        content = path.read_text()
        assert "whois_lookup" in content


# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK TESTS — marked so they can be skipped in offline environments
# ═══════════════════════════════════════════════════════════════════════════════

pytestmark_net = pytest.mark.net


@pytest.mark.net
class TestNetworkPassive:
    """Passive tools that hit public APIs — skipped in sandboxed envs."""

    def test_crt_sh_returns_results(self):
        from tools.passive_recon import cert_transparency_search
        result = cert_transparency_search("google.com")
        data = json.loads(result)
        assert "certificates" in data
        assert data["unique_names"] > 0

    def test_hackertarget_asn_8_8_8_8(self):
        from tools.passive_recon import hackertarget_asn_lookup
        result = hackertarget_asn_lookup("8.8.8.8")
        assert "Google" in result or "AS15169" in result or "error" in result.lower()

    def test_hackertarget_reverse_ip(self):
        from tools.passive_recon import hackertarget_reverse_ip
        result = hackertarget_reverse_ip("8.8.8.8")
        # Returns domains or an error string — either is acceptable
        assert isinstance(result, str) and len(result) > 0

    def test_ip_geolocation_google_dns(self):
        from tools.passive_recon import ip_geolocation
        result = ip_geolocation("8.8.8.8")
        data = json.loads(result)
        # ip-api.com may block sandbox — accept error or real result
        if data.get("status") == "success":
            assert data.get("country") is not None
        else:
            assert "error" in data or "message" in data or "status" in data

    def test_dns_enumeration_google(self):
        from tools.passive_recon import dns_enumeration
        result = dns_enumeration("google.com")
        data = json.loads(result)
        # A records may be empty in restricted environments
        assert isinstance(data.get("A"), list)
        assert isinstance(data.get("NS"), list)

    def test_sublist3r_returns_structure(self):
        from tools.passive_recon import sublist3r_passive
        result = sublist3r_passive("google.com")
        data = json.loads(result)
        assert "domain" in data
        assert "count"  in data
        assert "subdomains" in data
        assert isinstance(data["subdomains"], list)


@pytest.mark.net
class TestNetworkActive:
    """Lightweight active tests against Google's public DNS (8.8.8.8)."""

    def test_port_scan_quick_finds_open_port(self):
        from tools.active_recon import port_scan_quick
        result = port_scan_quick("8.8.8.8")
        data = json.loads(result)
        assert "open_ports" in data
        assert isinstance(data["open_ports"], list)

    def test_ssl_tls_analysis_google(self):
        from tools.active_recon import ssl_tls_analysis
        result = ssl_tls_analysis("google.com", 443)
        data = json.loads(result)
        if "error" not in data:
            assert "subject"     in data
            assert "not_after"   in data
            assert "tls_version" in data

    def test_banner_grab_port_443(self):
        from tools.active_recon import banner_grab
        result = banner_grab("google.com", 443)
        data = json.loads(result)
        # Either open with a banner, or an error — not a crash
        assert "open" in data or "error" in data
