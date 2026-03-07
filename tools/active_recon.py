"""
KALI OSINT Agent — Active Reconnaissance Tools
These tools send packets directly to the target. Use only on targets you have
explicit written authorisation to test.
"""

import json
import socket
import ssl
import subprocess
import urllib.parse
from datetime import datetime

import requests

from config import HTTP_TIMEOUT, NMAP_TIMEOUT, SOCKET_TIMEOUT

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = NMAP_TIMEOUT) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout)
        return (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return f"[{cmd[0]} not found — install it on Kali: apt install {cmd[0]}]"
    except subprocess.TimeoutExpired:
        return f"[command timed out after {timeout}s]"


def _safe_connect(host: str, port: int) -> tuple[socket.socket | None, str]:
    """Open a raw TCP socket to host:port; return (sock, error_msg)."""
    try:
        sock = socket.create_connection((host, port), timeout=SOCKET_TIMEOUT)
        return sock, ""
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return None, str(e)


# ─── Tool Implementations ─────────────────────────────────────────────────────

def nmap_scan(target: str, scan_type: str = "basic",
              ports: str = "1-1000") -> str:
    """
    Run an nmap scan against a target.
    scan_type:
      'basic'    — SYN scan top ports (-sS)
      'service'  — Service/version detection (-sV)
      'os'       — OS fingerprinting (-O)
      'aggressive'— -A (OS, version, scripts, traceroute) — noisiest
      'udp'      — UDP scan (-sU) top 100 ports — slow
      'vuln'     — NSE vulnerability scripts (--script vuln)
      'stealth'  — Slow ACK scan (-sA) to probe firewall rules
    """
    base = ["nmap", "-Pn", "--open", "-oN", "-"]

    type_flags = {
        "basic":      ["-sS", f"-p{ports}"],
        "service":    ["-sV", "--version-intensity", "5", f"-p{ports}"],
        "os":         ["-O", f"-p{ports}"],
        "aggressive": ["-A", f"-p{ports}"],
        "udp":        ["-sU", "--top-ports", "100"],
        "stealth":    ["-sA", f"-p{ports}"],
        "vuln":       ["-sV", "--script", "vuln", f"-p{ports}"],
    }

    flags = type_flags.get(scan_type, type_flags["basic"])
    cmd = base + flags + [target]
    return _run(cmd, timeout=NMAP_TIMEOUT)


def port_scan_quick(target: str) -> str:
    """
    Quick TCP connect scan on the 1000 most common ports using Python sockets
    (no nmap required). Returns JSON with open ports and response banners.
    """
    common_ports = [
        21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
        465, 587, 631, 993, 995, 1723, 3306, 3389, 5432, 5900, 6379,
        8080, 8443, 8888, 27017
    ]
    open_ports = []
    for port in common_ports:
        sock, err = _safe_connect(target, port)
        if sock:
            banner = ""
            try:
                sock.settimeout(2)
                sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                banner = sock.recv(1024).decode("utf-8", errors="replace")[:200]
            except Exception:
                try:
                    banner = sock.recv(1024).decode("utf-8", errors="replace")[:200]
                except Exception:
                    pass
            sock.close()
            open_ports.append({"port": port, "banner": banner.strip()})

    return json.dumps({"target": target, "open_ports": open_ports,
                       "scanned": len(common_ports)}, indent=2)


def banner_grab(target: str, port: int) -> str:
    """
    Grab the service banner from a specific TCP port.
    Sends protocol-appropriate probes for common services.
    """
    sock, err = _safe_connect(target, port)
    if not sock:
        return json.dumps({"target": target, "port": port,
                           "open": False, "error": err})

    probes = {
        21:  b"",           # FTP sends banner on connect
        22:  b"",           # SSH sends banner on connect
        25:  b"EHLO test\r\n",
        80:  b"HEAD / HTTP/1.0\r\nHost: " + target.encode() + b"\r\n\r\n",
        110: b"",           # POP3 banner on connect
        143: b"",           # IMAP banner on connect
        443: None,          # Handle TLS below
        3306: b"",          # MySQL sends banner
        5432: b"",          # PostgreSQL
        6379: b"INFO\r\n",  # Redis
    }

    banner = ""
    try:
        if port == 443:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            tls_sock = ctx.wrap_socket(sock, server_hostname=target)
            tls_sock.settimeout(SOCKET_TIMEOUT)
            tls_sock.send(
                b"HEAD / HTTP/1.0\r\nHost: " + target.encode() + b"\r\n\r\n")
            banner = tls_sock.recv(2048).decode("utf-8", errors="replace")
            tls_sock.close()
        else:
            probe = probes.get(port, b"")
            if probe:
                sock.send(probe)
            sock.settimeout(SOCKET_TIMEOUT)
            banner = sock.recv(2048).decode("utf-8", errors="replace")
            sock.close()
    except Exception as e:
        banner = f"[error reading banner: {e}]"

    return json.dumps({
        "target": target,
        "port": port,
        "open": True,
        "banner": banner.strip()[:500],
    }, indent=2)


def http_fingerprint(url: str) -> str:
    """
    Fingerprint a web server: headers, cookies, technology stack indicators,
    security headers audit, and robots.txt.
    """
    if not url.startswith("http"):
        url = "https://" + url

    results: dict = {"url": url}

    # ── Main page headers ──────────────────────────────────────────────────
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT, verify=False,
                         allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        results["status_code"] = r.status_code
        results["final_url"]   = r.url
        results["headers"]     = dict(r.headers)

        # Tech fingerprinting from headers
        tech = []
        server = r.headers.get("Server", "")
        x_powered = r.headers.get("X-Powered-By", "")
        if server:   tech.append(f"Server: {server}")
        if x_powered: tech.append(f"X-Powered-By: {x_powered}")
        results["detected_tech"] = tech

        # Security header audit
        sec_headers = [
            "Strict-Transport-Security", "Content-Security-Policy",
            "X-Frame-Options", "X-Content-Type-Options",
            "Referrer-Policy", "Permissions-Policy",
        ]
        results["security_headers"] = {
            h: r.headers.get(h, "MISSING") for h in sec_headers
        }

        # Cookies
        results["cookies"] = [
            {"name": c.name, "secure": c.secure,
             "httponly": c.has_nonstandard_attr("HttpOnly"),
             "samesite": c.get_nonstandard_attr("SameSite", "")}
            for c in r.cookies
        ]

    except requests.RequestException as e:
        results["error"] = str(e)

    # ── robots.txt ────────────────────────────────────────────────────────
    try:
        base = urllib.parse.urljoin(url, "/")
        rr = requests.get(base + "robots.txt", timeout=HTTP_TIMEOUT, verify=False)
        if rr.status_code == 200:
            results["robots_txt"] = rr.text[:2000]
    except Exception:
        pass

    # ── Common sensitive paths probe ──────────────────────────────────────
    probe_paths = [
        "/.git/HEAD", "/.env", "/admin", "/wp-login.php",
        "/.well-known/security.txt", "/sitemap.xml",
        "/crossdomain.xml", "/.htaccess",
    ]
    found_paths = {}
    for path in probe_paths:
        try:
            pr = requests.get(urllib.parse.urljoin(url, path),
                              timeout=5, verify=False, allow_redirects=False)
            if pr.status_code not in (404, 403):
                found_paths[path] = pr.status_code
        except Exception:
            pass
    results["interesting_paths"] = found_paths

    return json.dumps(results, indent=2, default=str)


def ssl_tls_analysis(host: str, port: int = 443) -> str:
    """
    Analyse the TLS certificate and configuration of a host:port.
    Returns cert details, validity, SANs, and cipher info.
    """
    results: dict = {"host": host, "port": port}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as tls:
                cert   = tls.getpeercert(binary_form=False)
                der    = tls.getpeercert(binary_form=True)
                cipher = tls.cipher()
                proto  = tls.version()

        subject = dict(x[0] for x in cert.get("subject", []))
        issuer  = dict(x[0] for x in cert.get("issuer",  []))
        sans    = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]

        not_before = cert.get("notBefore")
        not_after  = cert.get("notAfter")

        results.update({
            "subject":       subject,
            "issuer":        issuer,
            "sans":          sans,
            "not_before":    not_before,
            "not_after":     not_after,
            "serial":        cert.get("serialNumber"),
            "version":       cert.get("version"),
            "tls_version":   proto,
            "cipher_suite":  cipher[0] if cipher else None,
            "cipher_bits":   cipher[2] if cipher else None,
        })

    except Exception as e:
        results["error"] = str(e)

    return json.dumps(results, indent=2)


def nikto_scan(target: str) -> str:
    """
    Run nikto web vulnerability scanner against a URL.
    Requires nikto to be installed (apt install nikto).
    ACTIVE — sends many HTTP requests to the target.
    """
    cmd = ["nikto", "-h", target, "-C", "all", "-nointeractive",
           "-maxtime", "120s"]
    return _run(cmd, timeout=150)


def dirb_scan(target: str, wordlist: str = "/usr/share/dirb/wordlists/common.txt") -> str:
    """
    Run dirb directory bruteforce against a URL. Requires dirb on the system.
    ACTIVE — sends HTTP requests to the target.
    """
    cmd = ["dirb", target, wordlist, "-r", "-S", "-z", "50"]
    return _run(cmd, timeout=300)


def gobuster_scan(target: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt",
                  extensions: str = "php,html,txt,js,json") -> str:
    """
    Run gobuster directory/file enumeration against a URL.
    Requires gobuster (apt install gobuster).
    ACTIVE — sends HTTP requests to the target.
    """
    cmd = ["gobuster", "dir", "-u", target, "-w", wordlist,
           "-x", extensions, "-t", "10", "--timeout", "5s", "-q"]
    return _run(cmd, timeout=300)


def subdomain_brute(domain: str,
                    wordlist: str = "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt") -> str:
    """
    Active subdomain bruteforce using gobuster DNS mode.
    Requires gobuster + wordlist (apt install gobuster seclists).
    ACTIVE — sends DNS queries for many potential subdomains.
    """
    cmd = ["gobuster", "dns", "-d", domain, "-w", wordlist,
           "-t", "10", "-q"]
    return _run(cmd, timeout=300)


def traceroute(target: str) -> str:
    """
    Trace the network path to a target host. Shows hops and latency.
    Uses system traceroute/tracepath.
    """
    for tool in (["traceroute", "-n", "-m", "20", target],
                 ["tracepath",  "-n", target]):
        out = _run(tool, timeout=40)
        if not out.startswith("["):
            return out
    return "traceroute/tracepath not available."


def ping_sweep(network: str) -> str:
    """
    ICMP ping sweep a network range using nmap -sn.
    Example: network='192.168.1.0/24'
    ACTIVE — sends ICMP packets.
    """
    cmd = ["nmap", "-sn", "-n", "--open", network]
    return _run(cmd, timeout=120)


def web_screenshot_metadata(url: str) -> str:
    """
    Fetch HTTP response and extract metadata: title, meta tags, open graph,
    inline script count, external links. Lightweight alternative to a full
    headless browser screenshot.
    """
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT, verify=False,
                         headers={"User-Agent": "Mozilla/5.0"})
        text = r.text

        # Crude HTML parsing without extra dependencies
        def between(tag: str, t: str) -> list[str]:
            import re
            return re.findall(rf'<{tag}[^>]*>(.*?)</{tag}>', t, re.IGNORECASE | re.DOTALL)

        import re
        title_m = re.search(r'<title[^>]*>(.*?)</title>', text, re.IGNORECASE | re.DOTALL)
        title = title_m.group(1).strip() if title_m else ""

        metas = {}
        for m in re.finditer(r'<meta\s+([^>]+)>', text, re.IGNORECASE):
            attrs = dict(re.findall(r'(\w[\w-]*)=["\']([^"\']+)["\']', m.group(1)))
            name = attrs.get("name") or attrs.get("property") or attrs.get("http-equiv")
            if name and "content" in attrs:
                metas[name] = attrs["content"]

        scripts = len(re.findall(r'<script', text, re.IGNORECASE))
        ext_links = list(set(re.findall(
            r'href=["\']https?://([^/"\'#]+)[^"\']*["\']', text)))[:30]

        return json.dumps({
            "url": url,
            "title": title,
            "meta_tags": metas,
            "external_domains": ext_links,
            "inline_scripts": scripts,
            "response_size_bytes": len(text),
        }, indent=2)
    except Exception as e:
        return json.dumps({"url": url, "error": str(e)}, indent=2)


# ─── Tool Schema Definitions ─────────────────────────────────────────────────

ACTIVE_TOOLS = [
    {
        "name": "nmap_scan",
        "description": ("Run an nmap network scan against a target IP or hostname. "
                        "ACTIVE — sends packets to the target. Choose scan_type: "
                        "'basic', 'service', 'os', 'aggressive', 'udp', 'vuln', 'stealth'."),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string",
                           "description": "IP, hostname, or CIDR range"},
                "scan_type": {
                    "type": "string",
                    "enum": ["basic", "service", "os", "aggressive", "udp",
                             "vuln", "stealth"],
                    "default": "basic"
                },
                "ports": {"type": "string", "default": "1-1000",
                          "description": "Port range e.g. '1-65535' or '80,443,8080'"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "port_scan_quick",
        "description": ("Quick TCP connect scan of common ports using Python sockets "
                        "(no nmap). Returns open ports and banners. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string",
                           "description": "IP address or hostname"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "banner_grab",
        "description": ("Connect to a specific TCP port and grab the service banner "
                        "to identify the software and version. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "port": {"type": "integer", "description": "TCP port number"}
            },
            "required": ["target", "port"]
        }
    },
    {
        "name": "http_fingerprint",
        "description": ("Actively fingerprint a web server: analyse HTTP headers, "
                        "cookies, security header gaps, robots.txt, and probe for "
                        "common sensitive paths (.git, .env, /admin, etc.). ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string",
                        "description": "Full URL or just the hostname (https:// added automatically)"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "ssl_tls_analysis",
        "description": ("Connect to a host and analyse its TLS certificate: "
                        "subject, issuer, SANs, validity dates, cipher suite, "
                        "TLS protocol version. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "default": 443}
            },
            "required": ["host"]
        }
    },
    {
        "name": "web_screenshot_metadata",
        "description": ("Fetch a web page and extract: title, meta tags, Open Graph "
                        "data, external domains, script count. Lightweight web recon. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "nikto_scan",
        "description": ("Run nikto web vulnerability scanner. Detects outdated software, "
                        "dangerous files, misconfigurations. Requires: apt install nikto. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string",
                           "description": "URL e.g. http://example.com"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "dirb_scan",
        "description": ("Directory bruteforce with dirb. Requires: apt install dirb. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string",
                           "description": "Base URL e.g. http://example.com"},
                "wordlist": {"type": "string",
                             "default": "/usr/share/dirb/wordlists/common.txt"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "gobuster_scan",
        "description": ("Fast directory/file enumeration with gobuster. "
                        "Requires: apt install gobuster. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "wordlist": {"type": "string",
                             "default": "/usr/share/wordlists/dirb/common.txt"},
                "extensions": {"type": "string", "default": "php,html,txt,js,json"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "subdomain_brute",
        "description": ("Active subdomain bruteforce via DNS with gobuster. "
                        "Requires: apt install gobuster seclists. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "wordlist": {
                    "type": "string",
                    "default": "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt"
                }
            },
            "required": ["domain"]
        }
    },
    {
        "name": "traceroute",
        "description": ("Trace the network path to a host showing each hop. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "ping_sweep",
        "description": ("ICMP ping sweep of a network range to discover live hosts. "
                        "Example: '192.168.1.0/24'. Uses nmap -sn. ACTIVE."),
        "input_schema": {
            "type": "object",
            "properties": {
                "network": {"type": "string",
                            "description": "CIDR range e.g. 10.0.0.0/24"}
            },
            "required": ["network"]
        }
    },
]

# ─── Dispatch Map ─────────────────────────────────────────────────────────────

ACTIVE_DISPATCH: dict[str, callable] = {
    "nmap_scan":              lambda a: nmap_scan(**a),
    "port_scan_quick":        lambda a: port_scan_quick(**a),
    "banner_grab":            lambda a: banner_grab(**a),
    "http_fingerprint":       lambda a: http_fingerprint(**a),
    "ssl_tls_analysis":       lambda a: ssl_tls_analysis(**a),
    "web_screenshot_metadata":lambda a: web_screenshot_metadata(**a),
    "nikto_scan":             lambda a: nikto_scan(**a),
    "dirb_scan":              lambda a: dirb_scan(**a),
    "gobuster_scan":          lambda a: gobuster_scan(**a),
    "subdomain_brute":        lambda a: subdomain_brute(**a),
    "traceroute":             lambda a: traceroute(**a),
    "ping_sweep":             lambda a: ping_sweep(**a),
}
