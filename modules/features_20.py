"""
GP PRO AGENT - 20 Additional Features
All use REAL Ollama AI - no fake answers.
"""
from typing import Optional, List, Dict, Any, Callable
import json, time, os, re, subprocess, threading
from pathlib import Path
from datetime import datetime


class Feature:
    """Base class for GP PRO AGENT features."""
    def __init__(self, name: str, ai_callback: Callable):
        self.name = name
        self.ai   = ai_callback

    def handle(self, query: str) -> str:
        raise NotImplementedError


class FeatureHub:
    """
    Hub for all 20 additional features.
    All features use real Ollama AI.
    """
    def __init__(self, brain_root: str,
                 ai_callback: Callable,
                 notify: Callable):
        self._root   = Path(brain_root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._ai     = ai_callback
        self._notify = notify
        self._history: List[dict] = []

    def route(self, query: str) -> Optional[str]:
        """Check if query matches any feature."""
        q = query.lower()
        routes = {
            self._f01_explain:      ["explain","what is","how does","define","describe"],
            self._f02_compare:      ["compare","difference between","vs","versus","which is better"],
            self._f03_troubleshoot: ["troubleshoot","diagnose","why is","not working","fix this error","debug"],
            self._f04_translate:    ["translate to","convert from","in siemens","in allen bradley","equivalent in"],
            self._f05_checklist:    ["checklist for","steps to","procedure for","how to safely"],
            self._f06_summarize:    ["summarize","summary of","brief overview","tldr","key points of"],
            self._f07_quiz:         ["quiz me","test me","question about","exam on"],
            self._f08_optimize:     ["optimize","improve","make faster","make better","refactor"],
            self._f09_convert_units:["convert","psi to bar","celsius to","mA to","bar to psi","fahrenheit"],
            self._f10_alarm_help:   ["alarm","alarm message","alarm code","fault code","error code"],
            self._f11_wiring_help:  ["wiring","wire","connect","terminal","cable","connection diagram"],
            self._f12_tag_name:     ["suggest tag name","name this tag","tag naming","variable name"],
            self._f13_comment_code: ["add comments","comment this","document this code","explain this code"],
            self._f14_test_plan:    ["test plan","test procedure","how to test","testing steps"],
            self._f15_risk_assess:  ["risk assessment","hazard analysis","what could go wrong","risk of"],
            self._f16_plc_migrate:  ["migrate from","upgrade from","convert from rslogix","port to"],
            self._f17_energy_calc:  ["energy","power consumption","kw","kwh","electricity cost"],
            self._f18_io_list:      ["io list","input list","output list","io table","create io"],
            self._f19_hmi_design:   ["hmi screen","hmi design","scada screen","operator interface"],
            self._f20_training:     ["train me","teach me","learning path","how do i learn","beginner guide"],
        }
        for handler, keywords in routes.items():
            if any(k in q for k in keywords):
                return handler(query)
        return None

    def _log(self, feature: str, query: str, result: str):
        self._history.append({
            "feature": feature,
            "query":   query[:100],
            "time":    datetime.now().isoformat(),
        })

    # ── FEATURE 01: Deep Explanation ────────────────────────────
    def _f01_explain(self, query: str) -> str:
        """Explain any technical topic deeply using AI."""
        return self._ai("master", query)

    # ── FEATURE 02: Compare Technologies ────────────────────────
    def _f02_compare(self, query: str) -> str:
        """Compare PLC brands, protocols, methods."""
        prompt = (
            f"{query}\n\n"
            "Provide a structured comparison with:\n"
            "- Key differences\n"
            "- Pros and cons of each\n"
            "- When to use which\n"
            "- Real-world recommendation")
        return self._ai("master", prompt)

    # ── FEATURE 03: Troubleshooting Assistant ────────────────────
    def _f03_troubleshoot(self, query: str) -> str:
        """AI-powered troubleshooting."""
        prompt = (
            f"Troubleshoot this problem: {query}\n\n"
            "Provide:\n"
            "1. Most likely causes (ranked)\n"
            "2. Step-by-step diagnostic procedure\n"
            "3. Tools needed\n"
            "4. Fix for each cause\n"
            "5. Prevention tips")
        return self._ai("plc", prompt)

    # ── FEATURE 04: PLC Brand Translator ────────────────────────
    def _f04_translate(self, query: str) -> str:
        """Translate PLC code/concepts between brands."""
        prompt = (
            f"{query}\n\n"
            "Show the equivalent for each major PLC brand:\n"
            "- Allen Bradley (Studio 5000)\n"
            "- Siemens (TIA Portal)\n"
            "- Schneider (Unity Pro)\n"
            "- Mitsubishi (GX Works)\n"
            "Include syntax differences and gotchas.")
        return self._ai("plc", prompt)

    # ── FEATURE 05: Safety Checklist Generator ──────────────────
    def _f05_checklist(self, query: str) -> str:
        """Generate professional safety/operational checklists."""
        prompt = (
            f"Create a detailed professional checklist for: {query}\n\n"
            "Format as numbered checklist.\n"
            "Include: safety checks, tools needed, verification steps.\n"
            "Reference relevant standards (IEC, ISO, OSHA).")
        return self._ai("safety", prompt)

    # ── FEATURE 06: Smart Summarizer ────────────────────────────
    def _f06_summarize(self, query: str) -> str:
        """Summarize any technical content."""
        prompt = (
            f"{query}\n\n"
            "Provide:\n"
            "- Executive summary (2-3 sentences)\n"
            "- Key points (bullet list)\n"
            "- Action items\n"
            "- Important numbers/specs")
        return self._ai("docs", prompt)

    # ── FEATURE 07: Knowledge Quiz ──────────────────────────────
    def _f07_quiz(self, query: str) -> str:
        """Generate quiz questions on any topic."""
        prompt = (
            f"Create 5 quiz questions about: {query}\n\n"
            "Format:\n"
            "Q1: [Question]\n"
            "A) [Wrong] B) [Correct] C) [Wrong] D) [Wrong]\n"
            "Answer: B\n"
            "Explanation: [Why B is correct]\n\n"
            "Cover different difficulty levels.")
        return self._ai("master", prompt)

    # ── FEATURE 08: Code Optimizer ──────────────────────────────
    def _f08_optimize(self, query: str) -> str:
        """Optimize and improve code or logic."""
        prompt = (
            f"Optimize and improve this: {query}\n\n"
            "Provide:\n"
            "1. Issues with current approach\n"
            "2. Optimized version with explanation\n"
            "3. Performance improvements\n"
            "4. Best practices applied")
        return self._ai("coder", prompt)

    # ── FEATURE 09: Unit Converter ──────────────────────────────
    def _f09_convert_units(self, query: str) -> str:
        """Convert engineering units with formulas."""
        # Try direct calculation first
        conversions = {
            ("psi","bar"):    lambda x: x * 0.0689476,
            ("bar","psi"):    lambda x: x * 14.5038,
            ("celsius","fahrenheit"): lambda x: x*9/5+32,
            ("fahrenheit","celsius"): lambda x: (x-32)*5/9,
            ("kpa","psi"):    lambda x: x * 0.14504,
            ("psi","kpa"):    lambda x: x * 6.89476,
            ("4-20ma","%"):   lambda x: (x-4)/16*100,
            ("%","4-20ma"):   lambda x: x/100*16+4,
        }
        q = query.lower()
        num = re.search(r'(\d+\.?\d*)', query)
        val = float(num.group(1)) if num else None

        for (from_u, to_u), formula in conversions.items():
            if from_u in q and to_u in q and val is not None:
                result = formula(val)
                return (f"Conversion Result:\n\n"
                       f"  {val} {from_u} = {result:.4f} {to_u}\n\n"
                       f"Formula: Used standard engineering conversion")

        # Use AI for complex conversions
        return self._ai("math",
            f"Convert with full explanation: {query}\n"
            "Show formula and step-by-step calculation.")

    # ── FEATURE 10: Alarm Code Decoder ──────────────────────────
    def _f10_alarm_help(self, query: str) -> str:
        """Decode PLC alarm codes and provide solutions."""
        prompt = (
            f"PLC Alarm/Fault Help: {query}\n\n"
            "Provide:\n"
            "1. What this alarm means\n"
            "2. Common causes\n"
            "3. Step-by-step resolution\n"
            "4. Preventive measures\n"
            "5. Which PLC brands show this (if applicable)")
        return self._ai("plc", prompt)

    # ── FEATURE 11: Wiring Helper ───────────────────────────────
    def _f11_wiring_help(self, query: str) -> str:
        """Help with electrical wiring and connections."""
        prompt = (
            f"Wiring help: {query}\n\n"
            "Provide:\n"
            "- Wire colors and their meaning\n"
            "- Terminal connections\n"
            "- Safety precautions\n"
            "- Common wiring diagrams description\n"
            "- Testing procedure\n"
            "Reference: NEC, IEC 60204 standards")
        return self._ai("safety", prompt)

    # ── FEATURE 12: Tag Name Suggester ──────────────────────────
    def _f12_tag_name(self, query: str) -> str:
        """Suggest professional PLC tag names."""
        prompt = (
            f"Suggest professional PLC tag names for: {query}\n\n"
            "Follow ISA-5.1 naming conventions.\n"
            "Provide names for:\n"
            "- Allen Bradley (Studio 5000 format)\n"
            "- Siemens (TIA Portal format)\n"
            "- IEC 61131-3 standard\n"
            "Include: digital inputs, outputs, analog, timers, counters\n"
            "Use proper prefixes: x=BOOL, r=REAL, i=INT, ton=Timer")
        return self._ai("plc", prompt)

    # ── FEATURE 13: Code Commenter ──────────────────────────────
    def _f13_comment_code(self, query: str) -> str:
        """Add professional comments to code."""
        prompt = (
            f"Add professional comments and documentation to:\n"
            f"{query}\n\n"
            "Add:\n"
            "- Function/program header comment\n"
            "- Inline comments for each section\n"
            "- Variable descriptions\n"
            "- Safety notes where relevant\n"
            "Return the fully commented version.")
        return self._ai("coder", prompt)

    # ── FEATURE 14: Test Plan Generator ─────────────────────────
    def _f14_test_plan(self, query: str) -> str:
        """Generate professional test plans."""
        prompt = (
            f"Create a professional test plan for: {query}\n\n"
            "Include:\n"
            "1. Test objectives\n"
            "2. Prerequisites and setup\n"
            "3. Test cases (input -> expected output)\n"
            "4. Pass/fail criteria\n"
            "5. Safety precautions during testing\n"
            "6. Documentation requirements\n"
            "Reference FAT/SAT procedures.")
        return self._ai("plc", prompt)

    # ── FEATURE 15: Risk Assessment ─────────────────────────────
    def _f15_risk_assess(self, query: str) -> str:
        """Generate risk assessments."""
        prompt = (
            f"Perform risk assessment for: {query}\n\n"
            "Use HAZOP/FMEA methodology:\n"
            "1. Identify hazards\n"
            "2. Severity (1-5) and Probability (1-5)\n"
            "3. Risk Level (Severity x Probability)\n"
            "4. Current safeguards\n"
            "5. Additional safety measures needed\n"
            "6. SIL level recommendation\n"
            "7. Residual risk\n"
            "Reference: IEC 61508, ISO 13849")
        return self._ai("safety", prompt)

    # ── FEATURE 16: PLC Migration Helper ────────────────────────
    def _f16_plc_migrate(self, query: str) -> str:
        """Help migrate PLC programs between brands."""
        prompt = (
            f"PLC Migration help: {query}\n\n"
            "Provide:\n"
            "1. Migration steps and process\n"
            "2. Instruction equivalents\n"
            "3. Key differences to watch\n"
            "4. Data type mapping\n"
            "5. Testing procedure after migration\n"
            "6. Common migration pitfalls\n"
            "7. Timeline estimate")
        return self._ai("plc", prompt)

    # ── FEATURE 17: Energy Calculator ───────────────────────────
    def _f17_energy_calc(self, query: str) -> str:
        """Calculate energy consumption and costs."""
        prompt = (
            f"Energy calculation: {query}\n\n"
            "Calculate and show:\n"
            "- Power consumption (kW)\n"
            "- Daily/monthly/annual energy (kWh)\n"
            "- Cost estimate (at $0.12/kWh average)\n"
            "- CO2 footprint\n"
            "- Energy saving recommendations\n"
            "Show all formulas and calculations step by step.")
        return self._ai("math", prompt)

    # ── FEATURE 18: I/O List Generator ──────────────────────────
    def _f18_io_list(self, query: str) -> str:
        """Generate professional I/O lists."""
        prompt = (
            f"Generate a professional I/O list for: {query}\n\n"
            "Format as table with columns:\n"
            "Tag Name | Description | Type | Address | Range | Eng Unit | P&ID Ref\n\n"
            "Include:\n"
            "- Digital inputs (pushbuttons, sensors, limits)\n"
            "- Digital outputs (motors, valves, lamps)\n"
            "- Analog inputs (temperature, pressure, flow)\n"
            "- Analog outputs (speed drives, control valves)\n"
            "Follow ISA-5.1 naming standards.")
        return self._ai("plc", prompt)

    # ── FEATURE 19: HMI Screen Designer ─────────────────────────
    def _f19_hmi_design(self, query: str) -> str:
        """Design HMI screens with AI guidance."""
        prompt = (
            f"Design HMI/SCADA screen for: {query}\n\n"
            "Provide:\n"
            "1. Screen layout description\n"
            "2. Required elements (indicators, buttons, trends)\n"
            "3. Color coding scheme (ISA-101 standard)\n"
            "4. Navigation structure\n"
            "5. Alarm display requirements\n"
            "6. Operator interaction points\n"
            "7. Key performance indicators to display\n"
            "Reference ISA-101 HMI standards.")
        return self._ai("docs", prompt)

    # ── FEATURE 20: Learning Path Creator ───────────────────────
    def _f20_training(self, query: str) -> str:
        """Create personalized learning paths."""
        prompt = (
            f"Create a learning path for: {query}\n\n"
            "Provide structured curriculum:\n"
            "Week 1-2: Fundamentals\n"
            "Week 3-4: Intermediate\n"
            "Week 5-6: Advanced\n"
            "Week 7-8: Expert\n\n"
            "For each week:\n"
            "- Topics to study\n"
            "- Practical exercises\n"
            "- Resources (standards, software, books)\n"
            "- Skills to demonstrate\n"
            "Make it specific to industrial automation/PLC engineering.")
        return self._ai("master", prompt)

    def get_feature_list(self) -> List[dict]:
        return [
            {"id":1,  "name":"Deep Explainer",    "trigger":"explain X"},
            {"id":2,  "name":"Tech Comparator",   "trigger":"compare X vs Y"},
            {"id":3,  "name":"Troubleshooter",    "trigger":"troubleshoot X"},
            {"id":4,  "name":"PLC Translator",    "trigger":"translate to Siemens"},
            {"id":5,  "name":"Checklist Maker",   "trigger":"checklist for X"},
            {"id":6,  "name":"Summarizer",        "trigger":"summarize X"},
            {"id":7,  "name":"Knowledge Quiz",    "trigger":"quiz me on X"},
            {"id":8,  "name":"Code Optimizer",    "trigger":"optimize this code"},
            {"id":9,  "name":"Unit Converter",    "trigger":"convert 100 PSI to Bar"},
            {"id":10, "name":"Alarm Decoder",     "trigger":"alarm code 123"},
            {"id":11, "name":"Wiring Helper",     "trigger":"wiring for X"},
            {"id":12, "name":"Tag Namer",         "trigger":"suggest tag name for X"},
            {"id":13, "name":"Code Commenter",    "trigger":"add comments to code"},
            {"id":14, "name":"Test Plan Maker",   "trigger":"test plan for X"},
            {"id":15, "name":"Risk Assessor",     "trigger":"risk assessment for X"},
            {"id":16, "name":"PLC Migrator",      "trigger":"migrate from Allen Bradley"},
            {"id":17, "name":"Energy Calculator", "trigger":"energy consumption of X"},
            {"id":18, "name":"IO List Maker",     "trigger":"io list for X"},
            {"id":19, "name":"HMI Designer",      "trigger":"hmi screen for X"},
            {"id":20, "name":"Learning Coach",    "trigger":"teach me PLC"},
        ]
