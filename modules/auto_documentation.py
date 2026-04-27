"""
GP PRO AGENT - Auto Documentation Generator
Automatically documents PLC programs, creates user manuals,
generates API docs, and maintains living documentation.
"""
import re, json, time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

class DocumentationSection:
    def __init__(self, title: str, content: str,
                 level: int = 1):
        self.title   = title
        self.content = content
        self.level   = level
        self.subsections = []

class AutoDocumentation:
    """
    Automatically generates documentation from:
    - PLC programs (ST, Ladder descriptions)
    - Screen content
    - User interactions
    - System configurations
    """
    def __init__(self, brain_root: str,
                 llm_callback=None,
                 notify_callback=None):
        self._path    = Path(brain_root) / "auto_docs"
        self._path.mkdir(parents=True, exist_ok=True)
        self._llm     = llm_callback
        self._notify  = notify_callback or print
        self._docs    = {}

    def document_plc_program(self, program_name: str,
                              st_code: str,
                              variables: List[dict],
                              description: str = "") -> str:
        """Auto-document a PLC program."""
        doc = {
            "title":        f"PLC Program: {program_name}",
            "type":         "plc_program",
            "generated":    datetime.now().isoformat(),
            "sections":     [],
        }

        # Overview section
        doc["sections"].append({
            "title":   "Program Overview",
            "content": self._generate_overview(
                program_name, st_code, description),
        })

        # Variable documentation
        if variables:
            var_doc = self._document_variables(variables)
            doc["sections"].append({
                "title":   "Variable Declaration",
                "content": var_doc,
            })

        # Code analysis
        code_doc = self._analyze_code(st_code)
        doc["sections"].append({
            "title":   "Code Analysis",
            "content": code_doc,
        })

        # Safety notes
        safety = self._generate_safety_notes(st_code)
        doc["sections"].append({
            "title":   "Safety Considerations",
            "content": safety,
        })

        # Save documentation
        filename = f"{program_name}_{int(time.time())}.json"
        filepath = self._path / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)

        # Generate HTML version
        html_path = self._render_doc_html(doc, program_name)
        self._notify(f"[AUTO-DOC] Documentation generated: {html_path}")
        return html_path

    def _generate_overview(self, name: str, code: str,
                           description: str) -> str:
        lines_count = len(code.split("\n"))
        var_count   = code.count(":=")
        if_count    = code.lower().count("if ")
        timer_count = code.upper().count("TON(") + code.upper().count("TOF(")
        counter_count = code.upper().count("CTU(") + code.upper().count("CTD(")

        overview = f"""Program: {name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Author: GP PRO AGENT Auto-Documentation System

Description:
{description or 'Auto-generated PLC program'}

Code Metrics:
- Total lines:    {lines_count}
- Assignments:    {var_count}
- IF conditions:  {if_count}
- Timers:         {timer_count}
- Counters:       {counter_count}

Standard: IEC 61131-3 Structured Text"""
        return overview

    def _document_variables(self, variables: List[dict]) -> str:
        lines = ["Variable Reference:\n"]
        lines.append(f"{'Name':<25} {'Type':<10} {'Description'}")
        lines.append("-" * 60)
        for var in variables:
            lines.append(
                f"{var.get('name','?'):<25} "
                f"{var.get('type','BOOL'):<10} "
                f"{var.get('desc','')}")
        return "\n".join(lines)

    def _analyze_code(self, code: str) -> str:
        analysis = []
        code_l   = code.lower()
        # Detect patterns
        if "if" in code_l:
            analysis.append("- Contains conditional logic (IF/THEN/ELSE)")
        if "case" in code_l:
            analysis.append("- Contains CASE statement (state machine pattern)")
        if "ton(" in code_l or "tof(" in code_l:
            analysis.append("- Uses timer instructions (TON/TOF)")
        if "ctu(" in code_l or "ctd(" in code_l:
            analysis.append("- Uses counter instructions (CTU/CTD)")
        if "while" in code_l or "for" in code_l:
            analysis.append("- Contains loop structures")
        if "pid" in code_l:
            analysis.append("- Implements PID control algorithm")
        if "safety" in code_l or "estop" in code_l:
            analysis.append("- Includes safety logic")

        if not analysis:
            analysis.append("- Standard sequential logic program")

        return "Code Structure Analysis:\n" + "\n".join(analysis)

    def _generate_safety_notes(self, code: str) -> str:
        code_l = code.lower()
        notes  = ["Safety Review Notes:"]
        if "estop" in code_l or "e_stop" in code_l:
            notes.append("OK E-Stop logic detected in program")
        else:
            notes.append("!! E-Stop logic NOT detected - verify hardware safety")
        if "fault" in code_l:
            notes.append("OK Fault handling logic present")
        else:
            notes.append("!! No fault handling detected - add fault detection")
        if "watchdog" in code_l:
            notes.append("OK Watchdog timer present")
        notes.append("\nGeneral Safety Requirements:")
        notes.append("- Verify all safety interlocks before deployment")
        notes.append("- Test E-Stop circuit before going online")
        notes.append("- Follow LOTO procedure during maintenance")
        notes.append("- Ensure SIL rating matches risk assessment")
        notes.append("- Document all modifications with date and author")
        return "\n".join(notes)

    def _render_doc_html(self, doc: dict,
                         name: str) -> str:
        """Render documentation as HTML."""
        sections_html = ""
        for sec in doc["sections"]:
            content = sec["content"].replace("\n","<br>").replace(
                "OK", '<span style="color:#00ff88">OK</span>').replace(
                "!!", '<span style="color:#ff4444">!!</span>')
            sections_html += f"""
<div class="section">
  <h2>{sec['title']}</h2>
  <div class="content">{content}</div>
</div>"""

        html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>{doc['title']}</title>
<style>
body{{font-family:Consolas,monospace;background:#0a0f1a;
     color:#d0e8ff;margin:0;padding:20px}}
h1{{color:#00e5ff;border-bottom:2px solid #1a3a5c;padding:16px;
    margin:0 -20px 20px;background:#0d1526}}
h2{{color:#00ff88;margin-top:24px;padding-left:8px;
    border-left:3px solid #00ff88}}
.section{{background:#0d1526;border:1px solid #1a3a5c;
          border-radius:4px;padding:16px;margin:12px 0}}
.content{{line-height:1.8;font-size:13px}}
.meta{{color:#3a5a7a;font-size:11px;padding:8px 0}}
pre{{background:#071020;padding:12px;border-radius:4px;
     overflow-x:auto;font-size:12px}}
</style></head><body>
<h1>{doc['title']}</h1>
<div class="meta">Generated: {doc['generated'][:19]} | By GP PRO AGENT</div>
{sections_html}
</body></html>"""

        filename = f"{name.replace(' ','_')}_docs.html"
        filepath = self._path / filename
        filepath.write_text(html, encoding="utf-8")
        return str(filepath)

    def document_session(self, queries: List[dict]) -> str:
        """Document a user session automatically."""
        doc = {
            "title":     "Session Documentation",
            "type":      "session",
            "generated": datetime.now().isoformat(),
            "queries":   queries,
        }
        content = f"Session Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        content += f"Total queries: {len(queries)}\n\n"
        for i, q in enumerate(queries, 1):
            content += f"{i}. [{q.get('brain','?').upper()}] {q.get('query','?')}\n"
        filepath = self._path / f"session_{int(time.time())}.txt"
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def list_documents(self) -> List[dict]:
        docs = []
        for f in sorted(self._path.glob("*"),
                        key=lambda x: x.stat().st_mtime,
                        reverse=True)[:20]:
            docs.append({
                "name":     f.name,
                "path":     str(f),
                "size":     f.stat().st_size,
                "modified": datetime.fromtimestamp(
                    f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
        return docs

    def open_document(self, filepath: str):
        """Open document in default browser/viewer."""
        try:
            import subprocess
            subprocess.Popen(f'start "" "{filepath}"', shell=True)
            return True
        except Exception:
            return False
