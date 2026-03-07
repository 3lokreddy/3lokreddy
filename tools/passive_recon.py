"""
KALI OSINT Agent — Passive Reconnaissance Tools
No direct packets are sent to the target; all data comes from third-party
services, public databases, and DNS resolution.
"""

import json
import socket
import subprocess
import urllib.parse
from datetime import datetime

import dns.resolver
import dns.reversename
import requests

from config import DNS_TIMEOUT, HTTP_TIMEOUT, VIRUSTOTAL_KEY

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get(url: str, params: dict | None = None, headers: dict | None = None,
         timeout: int = HTTP_TIMEOUT) -> dict:
    """Safe GET wrapper — returns {'ok': bool, 'data': ..., 'error': str}"""
    try:
        r = requests.get(url, params=params, headers=headers,
                         timeout=timeout, verify=True)
        try:
            return {"ok": True, "data": r.json(), "status": r.status_code}
        except Exception:
            return {"ok": True, "data": r.text, "status": r.status_code}
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}


def _run(cmd: list[str], timeout: int = 15) -> str:
    """Run a shell command safely and return stdout."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout)
        return (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return f"[tool not found: {cmd[0]}]"
    except subprocess.TimeoutExpired:
        return "[command timed out]"


# ─── Tool Implementations ─────────────────────────────────────────────────────

def whois_lookup(domain: str) -> str:
    """WHOIS registry information for a domain or IP address."""
    result = _run(["whois", domain], timeout=20)
    if result.startswith("[tool not found"):
        # Fallback: ARIN REST API for IPs
        r = _get(f"https://rdap.arin.net/registry/ip/{domain}")
        if r["ok"]:
            return json.dumps(r["data"], indent=2)
    return result or "No WHOIS data returned."


def dns_enumeration(domain: str) -> str:
    """Enumerate common DNS record types for a domain."""
    record_types = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME", "CAA"]
    results = {}
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]
    resolver.timeout = DNS_TIMEOUT
    resolver.lifetime = DNS_TIMEOUT

    for rtype in record_types:
        try:
            answers = resolver.resolve(domain, rtype)
            results[rtype] = [str(r) for r in answers]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
                dns.resolver.NoNameservers, dns.exception.DNSException):
            results[rtype] = []

    # Also try zone transfer (AXFR) — passive attempt
    axfr_result = []
    for ns_record in results.get("NS", []):
        ns = ns_record.rstrip(".")
        try:
            z = dns.zone.from_xfr(dns.query.xfr(ns, domain, timeout=DNS_TIMEOUT))  # type: ignore
            axfr_result = [str(n) for n in z.nodes.keys()]
            break
        except Exception:
            pass
    if axfr_result:
        results["AXFR (zone transfer)"] = axfr_result

    return json.dumps(results, indent=2)


def reverse_dns_lookup(ip: str) -> str:
    """Reverse DNS lookup for an IP address."""
    try:
        rev_name = dns.reversename.from_address(ip)
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
        resolver.timeout = DNS_TIMEOUT
        answers = resolver.resolve(rev_name, "PTR")
        hostnames = [str(r) for r in answers]
        return json.dumps({"ip": ip, "hostnames": hostnames}, indent=2)
    except Exception as e:
        return json.dumps({"ip": ip, "hostnames": [], "error": str(e)}, indent=2)


def cert_transparency_search(domain: str) -> str:
    """
    Search Certificate Transparency logs via crt.sh to find subdomains
    and issued TLS certificates. Completely passive — no contact with target.
    """
    r = _get("https://crt.sh/", params={"q": f"%.{domain}", "output": "json"})
    if not r["ok"]:
        return f"crt.sh query failed: {r.get('error')}"

    entries = r.get("data", [])
    if not isinstance(entries, list):
        return "Unexpected crt.sh response format."

    seen = set()
    certs = []
    for entry in entries:
        names = entry.get("name_value", "").split("\n")
        for name in names:
            name = name.strip().lstrip("*.")
            if name and name not in seen:
                seen.add(name)
                certs.append({
                    "name": name,
                    "issuer": entry.get("issuer_name", ""),
                    "logged_at": entry.get("entry_timestamp", ""),
                })

    certs.sort(key=lambda x: x["name"])
    return json.dumps({
        "domain": domain,
        "unique_names": len(seen),
        "certificates": certs[:200],   # cap output
    }, indent=2)


def ip_geolocation(ip: str) -> str:
    """Geolocate an IP address using ip-api.com (no key required, free tier)."""
    r = _get(f"http://ip-api.com/json/{ip}",
             params={"fields": "status,message,country,regionName,city,zip,"
                               "lat,lon,timezone,isp,org,as,query"})
    if not r["ok"]:
        return f"Geolocation failed: {r.get('error')}"
    return json.dumps(r["data"], indent=2)


def shodan_host_info(ip: str) -> str:
    """
    Query Shodan for open ports, services, and banners on an IP.
    Requires SHODAN_API_KEY environment variable.
    """
    from config import SHODAN_API_KEY
    if not SHODAN_API_KEY:
        return ("Shodan API key not set. "
                "Export SHODAN_API_KEY=<your_key> to enable this tool.")
    r = _get(f"https://api.shodan.io/shodan/host/{ip}",
             params={"key": SHODAN_API_KEY})
    if not r["ok"]:
        return f"Shodan query failed: {r.get('error')}"
    data = r["data"]
    if isinstance(data, dict) and "error" in data:
        return f"Shodan error: {data['error']}"
    return json.dumps(data, indent=2)


def shodan_search(query: str, max_results: int = 20) -> str:
    """
    Search Shodan for hosts matching a query string (e.g. 'org:\"Tesla\"').
    Requires SHODAN_API_KEY.
    """
    from config import SHODAN_API_KEY
    if not SHODAN_API_KEY:
        return "Shodan API key not set. Export SHODAN_API_KEY=<your_key>."
    r = _get("https://api.shodan.io/shodan/host/search",
             params={"key": SHODAN_API_KEY, "query": query,
                     "minify": True})
    if not r["ok"]:
        return f"Shodan search failed: {r.get('error')}"
    data = r["data"]
    if isinstance(data, dict) and "error" in data:
        return f"Shodan error: {data['error']}"
    # Slim down huge responses
    matches = data.get("matches", [])[:max_results]
    return json.dumps({
        "total": data.get("total"),
        "returned": len(matches),
        "matches": matches,
    }, indent=2)


def virustotal_domain(domain: str) -> str:
    """Query VirusTotal for domain reputation, passive DNS, etc."""
    if not VIRUSTOTAL_KEY:
        return "VirusTotal API key not set. Export VIRUSTOTAL_API_KEY=<key>."
    headers = {"x-apikey": VIRUSTOTAL_KEY}
    r = _get(f"https://www.virustotal.com/api/v3/domains/{domain}",
             headers=headers)
    if not r["ok"]:
        return f"VirusTotal error: {r.get('error')}"
    return json.dumps(r["data"], indent=2)


def virustotal_ip(ip: str) -> str:
    """Query VirusTotal for IP reputation and passive DNS."""
    if not VIRUSTOTAL_KEY:
        return "VirusTotal API key not set. Export VIRUSTOTAL_API_KEY=<key>."
    headers = {"x-apikey": VIRUSTOTAL_KEY}
    r = _get(f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
             headers=headers)
    if not r["ok"]:
        return f"VirusTotal error: {r.get('error')}"
    return json.dumps(r["data"], indent=2)


def hackertarget_reverse_ip(ip: str) -> str:
    """Find domains hosted on the same IP via HackerTarget (free, passive)."""
    r = _get("https://api.hackertarget.com/reverseiplookup/",
             params={"q": ip})
    if not r["ok"]:
        return f"Reverse-IP lookup failed: {r.get('error')}"
    return str(r["data"]).strip()


def hackertarget_asn_lookup(query: str) -> str:
    """ASN information for an IP or ASN number via HackerTarget."""
    r = _get("https://api.hackertarget.com/aslookup/",
             params={"q": query})
    if not r["ok"]:
        return f"ASN lookup failed: {r.get('error')}"
    return str(r["data"]).strip()


def hackertarget_zone_transfer(domain: str) -> str:
    """Attempt DNS zone transfer via HackerTarget."""
    r = _get("https://api.hackertarget.com/zonetransfer/",
             params={"q": domain})
    if not r["ok"]:
        return f"Zone transfer failed: {r.get('error')}"
    return str(r["data"]).strip()


def email_header_analysis(raw_headers: str) -> str:
    """
    Parse raw email headers to trace routing hops and identify mail servers.
    Paste full 'Received:' header block as input.
    """
    lines = raw_headers.splitlines()
    hops = []
    for i, line in enumerate(lines):
        if line.lower().startswith("received:"):
            hops.append({"hop": len(hops) + 1, "raw": line})
    return json.dumps({"hops_found": len(hops), "hops": hops}, indent=2)


def google_dork_generator(target: str, dork_type: str = "all") -> str:
    """
    Generate Google dork search queries for a target domain or organisation.
    dork_type: 'files', 'login', 'subdomains', 'emails', 'cameras', 'all'
    Returns queries to paste into a search engine — no automated searching.
    """
    dorks = {
        "files": [
            f'site:{target} ext:pdf OR ext:docx OR ext:xlsx OR ext:pptx',
            f'site:{target} ext:sql OR ext:db OR ext:bak OR ext:log',
            f'site:{target} ext:env OR ext:config OR ext:xml OR ext:json',
        ],
        "login": [
            f'site:{target} inurl:login OR inurl:admin OR inurl:portal',
            f'site:{target} intitle:"index of" inurl:admin',
            f'site:{target} inurl:wp-admin OR inurl:phpmyadmin',
        ],
        "subdomains": [
            f'site:*.{target} -site:www.{target}',
            f'site:{target} -www',
        ],
        "emails": [
            f'site:{target} "@{target}"',
            f'"@{target}" filetype:txt OR filetype:csv',
        ],
        "cameras": [
            f'site:{target} inurl:"/view/index.shtml"',
            f'site:{target} intitle:"Live View / - AXIS"',
        ],
        "vulnerabilities": [
            f'site:{target} inurl:".php?id=" OR inurl:".asp?id="',
            f'site:{target} intitle:"error" OR intitle:"exception" OR intitle:"warning"',
            f'site:{target} inurl:"/.git/" OR inurl:"/.svn/"',
        ],
    }

    if dork_type == "all":
        selected = {k: v for k, v in dorks.items()}
    elif dork_type in dorks:
        selected = {dork_type: dorks[dork_type]}
    else:
        return f"Unknown dork_type '{dork_type}'. Choose from: {', '.join(dorks)}"

    output = {"target": target, "instructions":
              "Paste these queries into Google (or Bing, DuckDuckGo).",
              "dorks": selected}
    return json.dumps(output, indent=2)


def pastebin_search(keyword: str) -> str:
    """
    Search PasteHunter / Paste sites for leaked data mentioning a keyword.
    Uses psbdmp.ws (a public Pastebin search index).
    """
    r = _get("https://psbdmp.ws/api/v3/search/",
             params={"q": keyword})
    if not r["ok"]:
        return f"Pastebin search failed: {r.get('error')}"
    data = r.get("data", {})
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2)


def sublist3r_passive(domain: str) -> str:
    """
    Passive subdomain enumeration via crt.sh + HackerTarget without sending
    packets to the target. Aggregates results from both services.
    """
    found = set()

    # crt.sh
    r = _get("https://crt.sh/", params={"q": f"%.{domain}", "output": "json"})
    if r["ok"] and isinstance(r["data"], list):
        for entry in r["data"]:
            for name in entry.get("name_value", "").split("\n"):
                name = name.strip().lstrip("*.")
                if name.endswith(f".{domain}") or name == domain:
                    found.add(name)

    # HackerTarget
    r2 = _get("https://api.hackertarget.com/hostsearch/",
              params={"q": domain})
    if r2["ok"]:
        for line in str(r2["data"]).splitlines():
            if "," in line:
                found.add(line.split(",")[0].strip())

    subdomains = sorted(found)
    return json.dumps({"domain": domain, "count": len(subdomains),
                       "subdomains": subdomains}, indent=2)


# ─── Tool Schema Definitions ─────────────────────────────────────────────────

PASSIVE_TOOLS = [
    {
        "name": "whois_lookup",
        "description": ("Retrieve WHOIS registration data for a domain name or IP "
                        "address. Shows registrar, registrant, creation/expiry dates, "
                        "nameservers, and contact info. Purely passive."),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string",
                           "description": "Domain name or IP address to look up"}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "dns_enumeration",
        "description": ("Enumerate DNS records (A, AAAA, MX, NS, TXT, SOA, CNAME, "
                        "CAA) for a domain and attempt zone transfer. Passive — uses "
                        "public DNS resolvers only."),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Target domain name"}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "reverse_dns_lookup",
        "description": "Perform reverse DNS (PTR record) lookup for an IP address.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IPv4 or IPv6 address"}
            },
            "required": ["ip"]
        }
    },
    {
        "name": "cert_transparency_search",
        "description": ("Search Certificate Transparency logs (crt.sh) to discover "
                        "subdomains, wildcard certs, and historical TLS issuance. "
                        "Completely passive."),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Base domain to search"}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "sublist3r_passive",
        "description": ("Passive subdomain enumeration using crt.sh + HackerTarget "
                        "APIs. No packets sent to the target."),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Target domain"}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "ip_geolocation",
        "description": ("Geolocate an IP address — country, region, city, ISP, "
                        "ASN, lat/lon. Uses ip-api.com."),
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IPv4 address"}
            },
            "required": ["ip"]
        }
    },
    {
        "name": "shodan_host_info",
        "description": ("Query Shodan for open ports, running services, banners, "
                        "CVEs, and OS fingerprints on a specific IP. "
                        "Requires SHODAN_API_KEY env var."),
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IPv4 address to query"}
            },
            "required": ["ip"]
        }
    },
    {
        "name": "shodan_search",
        "description": ("Search Shodan with a query string (e.g. 'org:\"Google\" "
                        "port:22') to find exposed services across the internet. "
                        "Requires SHODAN_API_KEY env var."),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "Shodan search query string"},
                "max_results": {"type": "integer", "default": 20,
                                "description": "Maximum results (1-100)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "virustotal_domain",
        "description": ("Query VirusTotal for domain reputation, WHOIS history, "
                        "passive DNS, detected URLs. Requires VIRUSTOTAL_API_KEY."),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to query"}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "virustotal_ip",
        "description": ("Query VirusTotal for IP reputation and passive DNS history. "
                        "Requires VIRUSTOTAL_API_KEY env var."),
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP address to query"}
            },
            "required": ["ip"]
        }
    },
    {
        "name": "hackertarget_reverse_ip",
        "description": ("Discover all domains hosted on an IP address via "
                        "HackerTarget reverse-IP lookup."),
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IPv4 address"}
            },
            "required": ["ip"]
        }
    },
    {
        "name": "hackertarget_asn_lookup",
        "description": ("Get ASN information (organization, prefix, country) for "
                        "an IP address or ASN number via HackerTarget."),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "IP address or ASN (e.g. 'AS15169')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "hackertarget_zone_transfer",
        "description": ("Attempt DNS zone transfer for a domain via HackerTarget. "
                        "Reveals all subdomains if the nameserver is misconfigured."),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Target domain"}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "google_dork_generator",
        "description": ("Generate targeted Google dork search queries for a domain "
                        "or organisation to find exposed files, admin panels, login "
                        "pages, emails, cameras, and vulnerabilities."),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string",
                           "description": "Domain or organisation name"},
                "dork_type": {
                    "type": "string",
                    "enum": ["files", "login", "subdomains", "emails",
                             "cameras", "vulnerabilities", "all"],
                    "default": "all",
                    "description": "Category of dorks to generate"
                }
            },
            "required": ["target"]
        }
    },
    {
        "name": "pastebin_search",
        "description": ("Search public paste sites for mentions of an email, domain, "
                        "or keyword to find leaked credentials or sensitive data."),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string",
                            "description": "Search term (email, domain, username, etc.)"}
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "email_header_analysis",
        "description": ("Parse raw email headers to trace routing hops, identify "
                        "originating mail servers, and detect spoofing indicators."),
        "input_schema": {
            "type": "object",
            "properties": {
                "raw_headers": {"type": "string",
                                "description": "Raw email header text to analyse"}
            },
            "required": ["raw_headers"]
        }
    },
]

# ─── Dispatch Map ─────────────────────────────────────────────────────────────

PASSIVE_DISPATCH: dict[str, callable] = {
    "whois_lookup":              lambda a: whois_lookup(**a),
    "dns_enumeration":           lambda a: dns_enumeration(**a),
    "reverse_dns_lookup":        lambda a: reverse_dns_lookup(**a),
    "cert_transparency_search":  lambda a: cert_transparency_search(**a),
    "sublist3r_passive":         lambda a: sublist3r_passive(**a),
    "ip_geolocation":            lambda a: ip_geolocation(**a),
    "shodan_host_info":          lambda a: shodan_host_info(**a),
    "shodan_search":             lambda a: shodan_search(**a),
    "virustotal_domain":         lambda a: virustotal_domain(**a),
    "virustotal_ip":             lambda a: virustotal_ip(**a),
    "hackertarget_reverse_ip":   lambda a: hackertarget_reverse_ip(**a),
    "hackertarget_asn_lookup":   lambda a: hackertarget_asn_lookup(**a),
    "hackertarget_zone_transfer":lambda a: hackertarget_zone_transfer(**a),
    "google_dork_generator":     lambda a: google_dork_generator(**a),
    "pastebin_search":           lambda a: pastebin_search(**a),
    "email_header_analysis":     lambda a: email_header_analysis(**a),
}
