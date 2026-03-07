#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║          KALI OSINT AGENT  —  Powered by Claude Opus 4.6                 ║
║          Intelligent Open-Source Intelligence Gathering System            ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Modes:                                                                   ║
║    passive  — No contact with target; third-party APIs & public data      ║
║    active   — Direct interaction with target (authorisation required)     ║
║    full     — All tools available; AI decides what to use and when        ║
╚═══════════════════════════════════════════════════════════════════════════╝

Usage:
    python3 osint_agent.py [--mode passive|active|full] [--target <target>]
                           [--task <task_description>] [--report]
"""

import argparse
import json
import os
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from config import (ACTIVE, ANTHROPIC_API_KEY, FULL, MAX_TOKENS,
                    MAX_TOOL_ITERS, MODEL, PASSIVE, REPORT_DIR)
from tools.passive_recon import PASSIVE_TOOLS, PASSIVE_DISPATCH
from tools.active_recon import ACTIVE_TOOLS, ACTIVE_DISPATCH

# ─── Console ─────────────────────────────────────────────────────────────────
console = Console()

# ─── System Prompts ──────────────────────────────────────────────────────────

SYSTEM_BASE = """You are an elite OSINT analyst and penetration testing assistant
running on Kali Linux. You have access to a comprehensive suite of reconnaissance
tools spanning both passive (no-touch) and active recon. Your mission is to
gather maximum intelligence on the given target and synthesise findings into
clear, actionable intelligence reports.

METHODOLOGY — always follow this OSINT workflow:
1. FOOTPRINT: Identify the attack surface (domains, IPs, ASNs, emails, tech stack)
2. ENUMERATE: Discover subdomains, open ports, services, certificates
3. CORRELATE: Link findings — IPs → reverse-DNS → hosting relationships → ASNs
4. ANALYSE: Assess exposure, misconfigurations, data leaks, vulnerabilities
5. REPORT: Summarise findings with severity ratings and recommendations

TOOL SELECTION RULES:
• Prefer passive tools first — they leave no trace and are always safe
• Use active tools only when specifically in active/full mode
• Chain tools intelligently: DNS → IPs → geolocation → Shodan → banners
• If one tool fails, try an alternative approach
• Interpret tool output critically — don't just repeat raw data

OUTPUT FORMAT:
• Lead with key findings as bullet points
• Include severity ratings: CRITICAL / HIGH / MEDIUM / LOW / INFO
• Always provide context and explain *why* a finding matters
• End responses with a "NEXT STEPS" recommendation
"""

SYSTEM_PASSIVE = SYSTEM_BASE + """
CURRENT MODE: PASSIVE RECONNAISSANCE
You MUST NOT use any active tools (nmap, port scanning, banner grabbing,
HTTP fingerprinting, directory enumeration). Only use passive tools that
query third-party services without contacting the target directly.
"""

SYSTEM_ACTIVE = SYSTEM_BASE + """
CURRENT MODE: ACTIVE RECONNAISSANCE
You may use all tools including those that send packets directly to the target.
The operator has confirmed they have explicit written authorisation to test
this target. Start with passive enumeration, then move to active scanning.
"""

SYSTEM_FULL = SYSTEM_BASE + """
CURRENT MODE: FULL INTELLIGENCE GATHERING
All tools are available. Conduct a comprehensive OSINT + recon campaign:
1. Start with passive: WHOIS, DNS, crt.sh, Shodan, reverse-IP
2. Map the full attack surface (subdomains, IPs, ASNs)
3. Move to active: port scan all discovered IPs, fingerprint services
4. Check for web exposure: HTTP headers, security config, sensitive paths
5. Correlate all findings and generate a complete threat surface map
"""

SYSTEM_MAP = {PASSIVE: SYSTEM_PASSIVE, ACTIVE: SYSTEM_ACTIVE, FULL: SYSTEM_FULL}


# ─── Tool Dispatch ────────────────────────────────────────────────────────────

ALL_DISPATCH = {**PASSIVE_DISPATCH, **ACTIVE_DISPATCH}

def get_tools(mode: str) -> list[dict]:
    """Return the tool schemas available for the selected mode."""
    if mode == PASSIVE:
        return PASSIVE_TOOLS
    if mode == ACTIVE:
        return ACTIVE_TOOLS
    return PASSIVE_TOOLS + ACTIVE_TOOLS   # FULL


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name and return its string output."""
    fn = ALL_DISPATCH.get(tool_name)
    if not fn:
        return f"Unknown tool: {tool_name}"
    try:
        result = fn(tool_input)
        return str(result) if result is not None else "Tool returned no output."
    except Exception as e:
        return f"Tool execution error [{tool_name}]: {type(e).__name__}: {e}"


# ─── Pretty Printers ──────────────────────────────────────────────────────────

TOOL_COLOURS = {
    "whois_lookup":              "bright_blue",
    "dns_enumeration":           "bright_cyan",
    "cert_transparency_search":  "cyan",
    "sublist3r_passive":         "green",
    "ip_geolocation":            "yellow",
    "shodan_host_info":          "magenta",
    "shodan_search":             "magenta",
    "virustotal_domain":         "red",
    "virustotal_ip":             "red",
    "hackertarget_reverse_ip":   "bright_green",
    "hackertarget_asn_lookup":   "bright_green",
    "hackertarget_zone_transfer":"bright_yellow",
    "google_dork_generator":     "bright_white",
    "pastebin_search":           "orange3",
    "email_header_analysis":     "gold1",
    "reverse_dns_lookup":        "steel_blue1",
    "nmap_scan":                 "bright_red",
    "port_scan_quick":           "red",
    "banner_grab":               "dark_orange",
    "http_fingerprint":          "orange1",
    "ssl_tls_analysis":          "green3",
    "web_screenshot_metadata":   "cornflower_blue",
    "nikto_scan":                "bright_red",
    "dirb_scan":                 "red3",
    "gobuster_scan":             "red3",
    "subdomain_brute":           "dark_red",
    "traceroute":                "grey74",
    "ping_sweep":                "grey70",
}

def print_tool_call(name: str, inp: dict) -> None:
    colour = TOOL_COLOURS.get(name, "white")
    inp_str = json.dumps(inp, indent=2)
    console.print(Panel(
        Syntax(inp_str, "json", theme="monokai", word_wrap=True),
        title=f"[bold {colour}]⚙  TOOL: {name}[/]",
        border_style=colour,
        expand=False,
    ))


def print_tool_result(name: str, result: str) -> None:
    colour = TOOL_COLOURS.get(name, "white")
    preview = result[:3000] + ("…[truncated]" if len(result) > 3000 else "")
    # Try to pretty-print JSON
    try:
        parsed = json.loads(result)
        preview = json.dumps(parsed, indent=2)[:3000]
        syntax = Syntax(preview, "json", theme="monokai", word_wrap=True)
        console.print(Panel(syntax,
                            title=f"[dim {colour}]↩  RESULT: {name}[/]",
                            border_style=f"dim {colour}", expand=False))
    except (json.JSONDecodeError, ValueError):
        console.print(Panel(preview,
                            title=f"[dim {colour}]↩  RESULT: {name}[/]",
                            border_style=f"dim {colour}", expand=False))


def print_assistant_message(text: str) -> None:
    console.print(Panel(Markdown(text),
                        title="[bold green]🤖  OSINT AGENT[/]",
                        border_style="green"))


# ─── Report Generator ─────────────────────────────────────────────────────────

def save_report(target: str, mode: str, task: str,
                conversation: list[dict], final_text: str) -> Path:
    """Write a Markdown report to the reports/ directory."""
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe    = "".join(c if c.isalnum() or c in ".-_" else "_" for c in target)
    fname   = Path(REPORT_DIR) / f"osint_{safe}_{mode}_{ts}.md"

    tool_runs = []
    for msg in conversation:
        if msg.get("role") == "assistant":
            for block in (msg.get("content") if isinstance(msg["content"], list)
                          else []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_runs.append({
                        "tool": block["name"],
                        "input": block.get("input", {}),
                    })

    md_lines = [
        f"# OSINT Report — {target}",
        f"",
        f"| Field   | Value |",
        f"|---------|-------|",
        f"| Target  | `{target}` |",
        f"| Mode    | **{mode.upper()}** |",
        f"| Task    | {task} |",
        f"| Date    | {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} |",
        f"| Model   | {MODEL} |",
        f"",
        f"## Tools Executed ({len(tool_runs)})",
        "",
    ]
    for i, tr in enumerate(tool_runs, 1):
        inp_str = json.dumps(tr["input"])
        md_lines.append(f"{i}. **{tr['tool']}** — `{inp_str}`")

    md_lines += [
        "",
        "## Intelligence Summary",
        "",
        final_text,
        "",
        "---",
        f"*Generated by KALI OSINT AGENT — {MODEL}*",
    ]

    fname.write_text("\n".join(md_lines), encoding="utf-8")
    return fname


# ─── Core Agent Loop ──────────────────────────────────────────────────────────

def run_agent(target: str, mode: str, task: str,
              save: bool = False, interactive: bool = False) -> str:
    """
    Main agentic loop.
    Returns the final text response from the model.
    """
    if not ANTHROPIC_API_KEY:
        console.print("[bold red]ERROR:[/] ANTHROPIC_API_KEY is not set.\n"
                      "Export it: [cyan]export ANTHROPIC_API_KEY=sk-ant-...[/]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    tools  = get_tools(mode)
    system = SYSTEM_MAP.get(mode, SYSTEM_FULL)

    # ── Banner ────────────────────────────────────────────────────────────────
    console.print(Panel.fit(
        f"[bold bright_red]KALI OSINT AGENT[/]\n"
        f"[yellow]Target:[/] {target}\n"
        f"[yellow]Mode:[/]   {mode.upper()}\n"
        f"[yellow]Task:[/]   {task}\n"
        f"[yellow]Tools:[/]  {len(tools)} available\n"
        f"[yellow]Model:[/]  {MODEL}",
        title="[bold]⚡ OSINT AGENT INITIALISING[/]",
        border_style="bright_red",
    ))

    # Build initial prompt
    initial_prompt = (
        f"TARGET: {target}\n"
        f"TASK: {task}\n\n"
        f"Begin comprehensive OSINT reconnaissance in {mode.upper()} mode. "
        f"Use all available tools systematically to gather maximum intelligence "
        f"on the target. Chain findings together — if you find an IP, geolocate it "
        f"and look up its ASN; if you find subdomains, resolve their IPs; "
        f"if you find open ports, grab their banners. "
        f"Think step-by-step and explain your reasoning between tool calls."
    )

    messages: list[dict] = [{"role": "user", "content": initial_prompt}]
    iteration       = 0
    final_text      = ""
    conversation    = []

    while iteration < MAX_TOOL_ITERS:
        iteration += 1
        console.rule(f"[dim]Iteration {iteration}/{MAX_TOOL_ITERS}[/]")

        with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"),
                      console=console, transient=True) as progress:
            progress.add_task("Claude is thinking…", total=None)
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                system=system,
                tools=tools,
                messages=messages,
            )

        # ── Process response content ──────────────────────────────────────
        assistant_content = response.content
        conversation.append({"role": "assistant", "content": [
            b.model_dump() if hasattr(b, "model_dump") else b
            for b in assistant_content
        ]})
        messages.append({"role": "assistant", "content": assistant_content})

        # Print any text blocks
        text_blocks = [b for b in assistant_content if b.type == "text"]
        thinking_blocks = [b for b in assistant_content if b.type == "thinking"]

        if thinking_blocks:
            console.print(f"[dim]💭 Extended thinking: {len(thinking_blocks[0].thinking)} chars[/]")

        for tb in text_blocks:
            print_assistant_message(tb.text)
            final_text = tb.text   # keep latest

        # ── Done? ─────────────────────────────────────────────────────────
        if response.stop_reason == "end_turn":
            console.print("[bold green]✓ Agent completed analysis.[/]")
            break

        if response.stop_reason == "pause_turn":
            # Server-side tool loop hit limit — re-send to continue
            messages = [
                {"role": "user", "content": initial_prompt},
                {"role": "assistant", "content": assistant_content},
            ]
            continue

        # ── Execute tool calls ────────────────────────────────────────────
        tool_use_blocks = [b for b in assistant_content if b.type == "tool_use"]
        if not tool_use_blocks:
            console.print("[yellow]No tool calls and not end_turn — breaking.[/]")
            break

        tool_results = []
        for tool_block in tool_use_blocks:
            print_tool_call(tool_block.name, tool_block.input)

            start = time.time()
            with Progress(SpinnerColumn(),
                          TextColumn(f"[yellow]Running {tool_block.name}…"),
                          console=console, transient=True) as p:
                p.add_task("", total=None)
                result_str = execute_tool(tool_block.name, tool_block.input)
            elapsed = time.time() - start

            console.print(f"[dim]  ⏱  {elapsed:.1f}s[/]")
            print_tool_result(tool_block.name, result_str)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})

    else:
        console.print(f"[yellow]⚠ Max iterations ({MAX_TOOL_ITERS}) reached.[/]")

    # ── Interactive follow-up ─────────────────────────────────────────────
    if interactive:
        _interactive_loop(client, tools, system, messages, conversation)

    # ── Save report ───────────────────────────────────────────────────────
    if save and final_text:
        report_path = save_report(target, mode, task, conversation, final_text)
        console.print(f"\n[bold green]📄 Report saved:[/] {report_path}")

    return final_text


def _interactive_loop(client: anthropic.Anthropic, tools: list,
                      system: str, messages: list, conversation: list) -> None:
    """Follow-up Q&A mode after initial recon completes."""
    console.print(Panel(
        "[bold]Interactive mode — ask follow-up questions or request specific tools.\n"
        "Type [red]exit[/] or [red]quit[/] to finish.[/]",
        title="[bold cyan]💬 Interactive Follow-Up[/]",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.lower() in ("exit", "quit", "q"):
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=system,
            tools=tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})
        conversation.append({"role": "assistant", "content": [
            b.model_dump() if hasattr(b, "model_dump") else b
            for b in response.content
        ]})

        # Handle tool calls in interactive mode
        while response.stop_reason == "tool_use":
            tool_results = []
            for b in response.content:
                if b.type == "tool_use":
                    print_tool_call(b.name, b.input)
                    result_str = execute_tool(b.name, b.input)
                    print_tool_result(b.name, result_str)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": b.id,
                        "content": result_str,
                    })
                elif b.type == "text" and b.text:
                    print_assistant_message(b.text)

            messages.append({"role": "user", "content": tool_results})
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                system=system,
                tools=tools,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

        for b in response.content:
            if b.type == "text" and b.text:
                print_assistant_message(b.text)


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="KALI OSINT AGENT — Intelligent Reconnaissance System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Passive recon on a domain
          python3 osint_agent.py --target example.com --mode passive

          # Full OSINT campaign with report
          python3 osint_agent.py --target example.com --mode full --report

          # Active port scan + web fingerprint
          python3 osint_agent.py --target 1.2.3.4 --mode active --task "Find all open ports and fingerprint the web server"

          # Custom task with interactive follow-up
          python3 osint_agent.py --target company.com --mode passive --task "Find all email addresses and subdomains" --interactive

          # IP intelligence
          python3 osint_agent.py --target 8.8.8.8 --mode passive --task "Full IP intelligence: geolocation, ASN, reverse DNS, Shodan"
        """),
    )
    parser.add_argument("--target", "-t", required=False,
                        help="Target domain, IP, or organisation name")
    parser.add_argument("--mode", "-m",
                        choices=[PASSIVE, ACTIVE, FULL],
                        default=PASSIVE,
                        help="Recon mode (default: passive)")
    parser.add_argument("--task", "-T",
                        default="Perform comprehensive OSINT reconnaissance and map the full attack surface.",
                        help="Specific intelligence task or question")
    parser.add_argument("--report", "-r", action="store_true",
                        help="Save a Markdown report to reports/")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Enter interactive follow-up mode after initial recon")
    parser.add_argument("--list-tools", action="store_true",
                        help="List all available tools and exit")

    args = parser.parse_args()

    if args.list_tools:
        _print_tool_list()
        return

    if not args.target:
        parser.print_help()
        console.print("\n[red]Error: --target is required.[/]")
        sys.exit(1)

    # Warn on active mode
    if args.mode in (ACTIVE, FULL):
        console.print(Panel(
            "[bold yellow]⚠  WARNING — ACTIVE RECONNAISSANCE[/]\n\n"
            "Active mode sends packets directly to the target.\n"
            "[bold red]Only proceed if you have explicit written authorisation[/]\n"
            "to perform security testing on this target.\n\n"
            "Unauthorised scanning may be illegal in your jurisdiction.",
            border_style="yellow",
        ))
        try:
            confirm = console.input(
                "[yellow]Type [bold]YES[/] to confirm authorisation: [/]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\nAborted.")
            sys.exit(0)

        if confirm != "YES":
            console.print("[red]Aborted — authorisation not confirmed.[/]")
            sys.exit(0)

    run_agent(
        target=args.target,
        mode=args.mode,
        task=args.task,
        save=args.report,
        interactive=args.interactive,
    )


def _print_tool_list() -> None:
    from tools import ALL_TOOLS
    table = Table(title="KALI OSINT AGENT — Available Tools",
                  show_lines=True, border_style="bright_blue")
    table.add_column("#",    style="dim", width=4)
    table.add_column("Tool", style="bold cyan", min_width=30)
    table.add_column("Mode", style="yellow", width=8)
    table.add_column("Description", style="white")

    passive_names = {t["name"] for t in PASSIVE_TOOLS}
    active_names  = {t["name"] for t in ACTIVE_TOOLS}

    for i, tool in enumerate(ALL_TOOLS, 1):
        mode_tag = ("[green]PASSIVE[/]" if tool["name"] in passive_names
                    else "[red]ACTIVE[/]")
        desc = tool.get("description", "")[:80]
        table.add_row(str(i), tool["name"], mode_tag, desc)

    console.print(table)


if __name__ == "__main__":
    main()
