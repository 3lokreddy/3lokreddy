# KALI OSINT AGENT ⚡

> **Intelligent Open-Source Intelligence Gathering System powered by Claude Opus 4.6**

An AI-driven OSINT framework that chains 28 reconnaissance tools together autonomously — deciding which tools to use, correlating findings, and generating professional intelligence reports. Operates in passive (no-touch) or active (authorised) reconnaissance modes.

---

## Architecture

```
osint_agent.py          ← Claude Opus 4.6 agentic loop + CLI
config.py               ← API keys, model settings, timeouts
tools/
  passive_recon.py      ← 16 passive tools (no target contact)
  active_recon.py       ← 12 active tools (direct interaction)
  __init__.py
reports/                ← Auto-generated Markdown reports
requirements.txt
```

---

## Tools (28 Total)

### Passive Recon (16) — No target contact
| Tool | Description |
|------|-------------|
| `whois_lookup` | Domain/IP WHOIS registration data |
| `dns_enumeration` | A, AAAA, MX, NS, TXT, SOA, CNAME, CAA + zone transfer |
| `reverse_dns_lookup` | PTR record lookup for IPs |
| `cert_transparency_search` | crt.sh — subdomain discovery from TLS certs |
| `sublist3r_passive` | Subdomain enum via crt.sh + HackerTarget |
| `ip_geolocation` | Country, city, ISP, ASN, lat/lon via ip-api.com |
| `shodan_host_info` | Open ports, banners, CVEs, OS fingerprints |
| `shodan_search` | Search internet-wide Shodan database |
| `virustotal_domain` | Domain reputation + passive DNS history |
| `virustotal_ip` | IP reputation + passive DNS |
| `hackertarget_reverse_ip` | Other domains on same IP |
| `hackertarget_asn_lookup` | ASN ownership info |
| `hackertarget_zone_transfer` | DNS zone transfer attempt |
| `google_dork_generator` | Google dork queries (files, logins, emails, cameras) |
| `pastebin_search` | Leaked data on paste sites |
| `email_header_analysis` | Trace email routing and detect spoofing |

### Active Recon (12) — Authorised targets only
| Tool | Description |
|------|-------------|
| `nmap_scan` | Network scan (basic/service/os/aggressive/udp/vuln/stealth) |
| `port_scan_quick` | Fast Python-socket TCP connect scan |
| `banner_grab` | Service banner on specific TCP port |
| `http_fingerprint` | Headers, cookies, security headers, sensitive paths |
| `ssl_tls_analysis` | TLS cert details, cipher suite, protocol version |
| `web_screenshot_metadata` | Page title, meta tags, external domains |
| `nikto_scan` | Web vulnerability scanner |
| `dirb_scan` | Directory brute-force with dirb |
| `gobuster_scan` | Fast directory/file enumeration |
| `subdomain_brute` | Active DNS subdomain brute-force |
| `traceroute` | Network path tracing |
| `ping_sweep` | ICMP host discovery on network range |

---

## Installation

```bash
# Clone and install dependencies
pip3 install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# Optional: for Shodan and VirusTotal
export SHODAN_API_KEY=...
export VIRUSTOTAL_API_KEY=...
```

**Kali Linux tools** (optional, for active mode):
```bash
apt install nmap nikto dirb gobuster seclists whois traceroute
```

---

## Usage

```bash
# Passive recon — safe, no target contact
python3 osint_agent.py --target example.com --mode passive

# Full OSINT campaign with Markdown report
python3 osint_agent.py --target example.com --mode full --report

# Active scan (requires authorisation confirmation)
python3 osint_agent.py --target 1.2.3.4 --mode active \
  --task "Find all open ports and fingerprint the web server"

# Custom task + interactive follow-up Q&A
python3 osint_agent.py --target target.com --mode passive \
  --task "Find all employee email addresses and exposed subdomains" \
  --interactive

# IP intelligence
python3 osint_agent.py --target 8.8.8.8 --mode passive \
  --task "Full IP intel: geolocation, ASN, reverse DNS, Shodan"

# List all 28 tools
python3 osint_agent.py --list-tools
```

### Options
```
--target / -t    Target domain, IP, or organisation name
--mode   / -m    passive | active | full  (default: passive)
--task   / -T    Specific intelligence task (natural language)
--report / -r    Save Markdown report to reports/
--interactive    Interactive Q&A follow-up after initial recon
--list-tools     Print all available tools and exit
```

---

## How It Works

1. **Claude Opus 4.6** acts as the orchestrator with **adaptive thinking** enabled
2. Given the target and mode, it autonomously selects tools in optimal sequence
3. Findings from each tool inform the next tool call (chain reasoning)
4. The agent correlates across sources: DNS → IPs → Shodan → banners → certs
5. After all recon completes, it synthesises a structured intelligence summary
6. Optionally, interactive mode lets you ask follow-up questions

### Intelligence Workflow
```
FOOTPRINT  →  ENUMERATE  →  CORRELATE  →  ANALYSE  →  REPORT
  WHOIS        subdomains    IP→ASN         vulns       severity
  DNS          ports         hosting        leaks       next steps
  crt.sh       banners       relationships  config
```

---

## Ethical & Legal Notice

> **This tool is for authorised security assessments, CTF competitions, and OSINT research only.**
>
> - Passive mode queries only third-party databases — no target contact
> - Active mode requires **explicit written authorisation** from the target owner
> - Unauthorised network scanning is illegal in most jurisdictions
> - The operator is solely responsible for ensuring lawful use

---

*Powered by [Claude Opus 4.6](https://www.anthropic.com) — Anthropic's most capable model*
