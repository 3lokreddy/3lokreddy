#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║          KALI OSINT AGENT  —  Multi-Provider AI Backend                  ║
║          Intelligent Open-Source Intelligence Gathering System            ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Providers:                                                               ║
║    anthropic — Claude Opus 4.6  (default)                                ║
║    openai    — GPT-4o                                                     ║
║                                                                           ║
║  Modes:                                                                   ║
║    passive  — No contact with target; third-party APIs & public data      ║
║    active   — Direct interaction with target (authorisation required)     ║
║    full     — All tools available; AI decides what to use and when        ║
╚═══════════════════════════════════════════════════════════════════════════╝

Usage:
    python3 osint_agent.py [--provider anthropic|openai]
                           [--mode passive|active|full] [--target <target>]
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

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from config import (ACTIVE, ANTHROPIC_API_KEY, FULL, MAX_TOKENS,
                    MAX_TOOL_ITERS, MODEL, OPENAI_API_KEY, OPENAI_MODEL,
                    PASSIVE, REPORT_DIR)
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
    """Return the Claude-format tool schemas available for the selected mode."""
    if mode == PASSIVE:
        return PASSIVE_TOOLS
    if mode == ACTIVE:
        return ACTIVE_TOOLS
    return PASSIVE_TOOLS + ACTIVE_TOOLS   # FULL


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    """Convert Claude input_schema format → OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema",
                                    {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


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
                tool_runs: list[dict], final_text: str,
                model_label: str) -> Path:
    """Write a Markdown report to the reports/ directory."""
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe    = "".join(c if c.isalnum() or c in "-_" else "_" for c in target)
    fname   = Path(REPORT_DIR) / f"osint_{safe}_{mode}_{ts}.md"

    md_lines = [
        f"# OSINT Report — {target}",
        f"",
        f"| Field   | Value |",
        f"|---------|-------|",
        f"| Target  | `{target}` |",
        f"| Mode    | **{mode.upper()}** |",
        f"| Task    | {task} |",
        f"| Date    | {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} |",
        f"| Model   | {model_label} |",
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
        f"*Generated by KALI OSINT AGENT — {model_label}*",
    ]

    fname.write_text("\n".join(md_lines), encoding="utf-8")
    return fname


# ─── Anthropic Agent Loop ─────────────────────────────────────────────────────

def _run_anthropic(target: str, mode: str, task: str,
                   save: bool, interactive: bool) -> str:
    import anthropic as _anthropic

    if not ANTHROPIC_API_KEY:
        console.print("[bold red]ERROR:[/] ANTHROPIC_API_KEY is not set.\n"
                      "Export it: [cyan]export ANTHROPIC_API_KEY=sk-ant-...[/]")
        sys.exit(1)

    client    = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    tools     = get_tools(mode)
    system    = SYSTEM_MAP.get(mode, SYSTEM_FULL)
    model_lbl = MODEL

    _print_banner(target, mode, task, len(tools), model_lbl)

    initial_prompt = _build_prompt(target, mode, task)
    messages: list[dict] = [{"role": "user", "content": initial_prompt}]
    iteration  = 0
    final_text = ""
    tool_runs: list[dict] = []

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

        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        thinking_blocks = [b for b in assistant_content if b.type == "thinking"]
        if thinking_blocks:
            console.print(f"[dim]💭 Extended thinking: "
                          f"{len(thinking_blocks[0].thinking)} chars[/]")

        for tb in [b for b in assistant_content if b.type == "text"]:
            print_assistant_message(tb.text)
            final_text = tb.text

        if response.stop_reason == "end_turn":
            console.print("[bold green]✓ Agent completed analysis.[/]")
            break

        if response.stop_reason == "pause_turn":
            messages = [
                {"role": "user", "content": initial_prompt},
                {"role": "assistant", "content": assistant_content},
            ]
            continue

        tool_use_blocks = [b for b in assistant_content if b.type == "tool_use"]
        if not tool_use_blocks:
            console.print("[yellow]No tool calls and not end_turn — breaking.[/]")
            break

        tool_results = []
        for tb in tool_use_blocks:
            print_tool_call(tb.name, tb.input)
            start = time.time()
            with Progress(SpinnerColumn(),
                          TextColumn(f"[yellow]Running {tb.name}…"),
                          console=console, transient=True) as p:
                p.add_task("", total=None)
                result_str = execute_tool(tb.name, tb.input)
            console.print(f"[dim]  ⏱  {time.time() - start:.1f}s[/]")
            print_tool_result(tb.name, result_str)
            tool_runs.append({"tool": tb.name, "input": tb.input})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tb.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})

    else:
        console.print(f"[yellow]⚠ Max iterations ({MAX_TOOL_ITERS}) reached.[/]")

    if interactive:
        _interactive_loop_anthropic(client, tools, system, messages)

    if save and final_text:
        path = save_report(target, mode, task, tool_runs, final_text, model_lbl)
        console.print(f"\n[bold green]📄 Report saved:[/] {path}")

    return final_text


def _interactive_loop_anthropic(client, tools, system, messages) -> None:
    """Follow-up Q&A using Anthropic Claude."""
    import anthropic as _anthropic

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
            model=MODEL, max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=system, tools=tools, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

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
                model=MODEL, max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                system=system, tools=tools, messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

        for b in response.content:
            if b.type == "text" and b.text:
                print_assistant_message(b.text)


# ─── OpenAI Agent Loop ────────────────────────────────────────────────────────

def _run_openai(target: str, mode: str, task: str,
                save: bool, interactive: bool) -> str:
    from openai import OpenAI

    if not OPENAI_API_KEY:
        console.print("[bold red]ERROR:[/] OPENAI_API_KEY is not set.\n"
                      "Export it: [cyan]export OPENAI_API_KEY=sk-...[/]")
        sys.exit(1)

    client    = OpenAI(api_key=OPENAI_API_KEY)
    tools     = get_tools(mode)
    oai_tools = _to_openai_tools(tools)
    system    = SYSTEM_MAP.get(mode, SYSTEM_FULL)
    model_lbl = OPENAI_MODEL

    _print_banner(target, mode, task, len(tools), model_lbl)

    initial_prompt = _build_prompt(target, mode, task)
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user",   "content": initial_prompt},
    ]
    iteration  = 0
    final_text = ""
    tool_runs: list[dict] = []

    while iteration < MAX_TOOL_ITERS:
        iteration += 1
        console.rule(f"[dim]Iteration {iteration}/{MAX_TOOL_ITERS}[/]")

        with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"),
                      console=console, transient=True) as progress:
            progress.add_task("GPT-4o is thinking…", total=None)
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                max_tokens=MAX_TOKENS,
                tools=oai_tools,
                tool_choice="auto",
                messages=messages,
            )

        choice = response.choices[0]
        msg    = choice.message

        # Append assistant turn as a plain dict (serialisable)
        assistant_dict: dict = {"role": "assistant"}
        if msg.content:
            assistant_dict["content"] = msg.content
        if msg.tool_calls:
            assistant_dict["tool_calls"] = [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_dict)

        if msg.content:
            print_assistant_message(msg.content)
            final_text = msg.content

        if choice.finish_reason == "stop":
            console.print("[bold green]✓ Agent completed analysis.[/]")
            break

        if choice.finish_reason != "tool_calls" or not msg.tool_calls:
            console.print("[yellow]Unexpected finish_reason — breaking.[/]")
            break

        # Execute tool calls
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                inp = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                inp = {}

            print_tool_call(name, inp)
            start = time.time()
            with Progress(SpinnerColumn(),
                          TextColumn(f"[yellow]Running {name}…"),
                          console=console, transient=True) as p:
                p.add_task("", total=None)
                result_str = execute_tool(name, inp)
            console.print(f"[dim]  ⏱  {time.time() - start:.1f}s[/]")
            print_tool_result(name, result_str)
            tool_runs.append({"tool": name, "input": inp})

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      result_str,
            })

    else:
        console.print(f"[yellow]⚠ Max iterations ({MAX_TOOL_ITERS}) reached.[/]")

    if interactive:
        _interactive_loop_openai(client, oai_tools, messages)

    if save and final_text:
        path = save_report(target, mode, task, tool_runs, final_text, model_lbl)
        console.print(f"\n[bold green]📄 Report saved:[/] {path}")

    return final_text


def _interactive_loop_openai(client, oai_tools, messages) -> None:
    """Follow-up Q&A using OpenAI GPT-4o."""
    from openai import OpenAI

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

        while True:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                max_tokens=MAX_TOKENS,
                tools=oai_tools,
                tool_choice="auto",
                messages=messages,
            )
            choice = response.choices[0]
            msg    = choice.message

            assistant_dict: dict = {"role": "assistant"}
            if msg.content:
                assistant_dict["content"] = msg.content
            if msg.tool_calls:
                assistant_dict["tool_calls"] = [
                    {
                        "id": tc.id, "type": "function",
                        "function": {"name": tc.function.name,
                                     "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ]
            messages.append(assistant_dict)

            if msg.content:
                print_assistant_message(msg.content)

            if choice.finish_reason == "stop":
                break

            if choice.finish_reason == "tool_calls" and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        inp = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        inp = {}
                    print_tool_call(name, inp)
                    result_str = execute_tool(name, inp)
                    print_tool_result(name, result_str)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })
            else:
                break


# ─── Shared Helpers ───────────────────────────────────────────────────────────

def _build_prompt(target: str, mode: str, task: str) -> str:
    return (
        f"TARGET: {target}\n"
        f"TASK: {task}\n\n"
        f"Begin comprehensive OSINT reconnaissance in {mode.upper()} mode. "
        f"Use all available tools systematically to gather maximum intelligence "
        f"on the target. Chain findings together — if you find an IP, geolocate it "
        f"and look up its ASN; if you find subdomains, resolve their IPs; "
        f"if you find open ports, grab their banners. "
        f"Think step-by-step and explain your reasoning between tool calls."
    )


def _print_banner(target: str, mode: str, task: str,
                  tool_count: int, model_lbl: str) -> None:
    console.print(Panel.fit(
        f"[bold bright_red]KALI OSINT AGENT[/]\n"
        f"[yellow]Target:[/] {target}\n"
        f"[yellow]Mode:[/]   {mode.upper()}\n"
        f"[yellow]Task:[/]   {task}\n"
        f"[yellow]Tools:[/]  {tool_count} available\n"
        f"[yellow]Model:[/]  {model_lbl}",
        title="[bold]⚡ OSINT AGENT INITIALISING[/]",
        border_style="bright_red",
    ))


# ─── Public Entry Point ───────────────────────────────────────────────────────

def run_agent(target: str, mode: str, task: str,
              provider: str = "anthropic",
              save: bool = False, interactive: bool = False) -> str:
    """
    Main entry point. Dispatches to the Anthropic or OpenAI backend.
    Returns the final text response from the model.
    """
    if provider == "openai":
        return _run_openai(target, mode, task, save, interactive)
    return _run_anthropic(target, mode, task, save, interactive)


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="KALI OSINT AGENT — Intelligent Reconnaissance System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Passive recon with Claude (default)
          python3 osint_agent.py --target example.com --mode passive

          # Passive recon with GPT-4o
          python3 osint_agent.py --target example.com --mode passive --provider openai

          # Full OSINT campaign with report (OpenAI)
          python3 osint_agent.py --target example.com --mode full --report --provider openai

          # Active port scan + web fingerprint (Claude)
          python3 osint_agent.py --target 1.2.3.4 --mode active --task "Find all open ports"

          # Interactive follow-up (GPT-4o)
          python3 osint_agent.py --target company.com --mode passive --interactive --provider openai
        """),
    )
    parser.add_argument("--target", "-t", required=False,
                        help="Target domain, IP, or organisation name")
    parser.add_argument("--mode", "-m",
                        choices=[PASSIVE, ACTIVE, FULL],
                        default=PASSIVE,
                        help="Recon mode (default: passive)")
    parser.add_argument("--provider", "-p",
                        choices=["anthropic", "openai"],
                        default="anthropic",
                        help="AI provider: anthropic (Claude) or openai (GPT-4o). "
                             "Default: anthropic")
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
        provider=args.provider,
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

    for i, tool in enumerate(ALL_TOOLS, 1):
        mode_tag = ("[green]PASSIVE[/]" if tool["name"] in passive_names
                    else "[red]ACTIVE[/]")
        desc = tool.get("description", "")[:80]
        table.add_row(str(i), tool["name"], mode_tag, desc)

    console.print(table)


if __name__ == "__main__":
    main()
