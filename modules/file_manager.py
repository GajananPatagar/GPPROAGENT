"""
GP PRO AGENT — Smart File Manager
AI reads, writes, organizes files intelligently.
Search files, analyze content, auto-organize by type.
"""
import os, shutil, json, time, re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

class SmartFileManager:
    def __init__(self, brain_root):
        self._root    = Path(brain_root)
        self._index   = {}
        self._watched = []

    def process_command(self, command: str,
                        llm_callback=None) -> str:
        """Process natural language file commands."""
        q = command.lower()

        if any(w in q for w in ["find","search","where is","locate"]):
            return self._search_files(command)
        if any(w in q for w in ["read","open","show content","what is in"]):
            return self._read_file(command)
        if any(w in q for w in ["create","write","make file","new file"]):
            return self._create_file(command, llm_callback)
        if any(w in q for w in ["organize","sort files","clean up","arrange"]):
            return self._organize_files(command)
        if any(w in q for w in ["list files","show files","what files"]):
            return self._list_files(command)
        if any(w in q for w in ["delete","remove file"]):
            return self._safe_delete(command)
        if any(w in q for w in ["copy","duplicate"]):
            return self._copy_file(command)
        if any(w in q for w in ["disk space","storage","how much space"]):
            return self._disk_info()
        return self._analyze_path(command)

    def _search_files(self, query: str) -> str:
        q = query.lower()
        # Extract search term
        patterns = [
            r"find (?:file )?[\"']?(.+?)[\"']?\s*(?:in|on|at|$)",
            r"search for [\"']?(.+?)[\"']?\s*(?:in|on|$)",
            r"where is [\"']?(.+?)[\"']?\s*(?:file|$)",
            r"locate [\"']?(.+?)[\"']",
        ]
        term = None
        for pat in patterns:
            m = re.search(pat, q)
            if m:
                term = m.group(1).strip()
                break
        if not term:
            return "Tell me what to search for. Example: 'Find file report.xlsx'"

        # Search locations
        search_dirs = [
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path.home() / "Downloads",
            Path("C:/"),
            self._root,
        ]
        found = []
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            try:
                for p in search_dir.rglob(f"*{term}*"):
                    if len(found) >= 10:
                        break
                    found.append(p)
            except PermissionError:
                pass

        if not found:
            return f"No files found matching '{term}'"

        result = f"Found {len(found)} file(s) matching '{term}':\n\n"
        for p in found:
            size = p.stat().st_size if p.is_file() else 0
            result += (f"📄 {p.name}\n"
                      f"   Path: {p}\n"
                      f"   Size: {self._fmt_size(size)}\n"
                      f"   Modified: {datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}\n\n")
        return result

    def _read_file(self, query: str) -> str:
        q = query.lower()
        # Extract file path
        path_match = re.search(r'[A-Za-z]:[\\\/][\w\\\/\.\- ]+\.\w+', query)
        if not path_match:
            path_match = re.search(r'[\w\.\-\/\\]+\.\w{2,5}', query)
        if not path_match:
            return "Specify the file path. Example: 'Read C:\\Users\\Desktop\\notes.txt'"

        file_path = Path(path_match.group())
        if not file_path.exists():
            # Try common locations
            for base in [Path.home()/"Desktop",
                        Path.home()/"Documents",
                        Path.home()/"Downloads"]:
                candidate = base / file_path.name
                if candidate.exists():
                    file_path = candidate
                    break

        if not file_path.exists():
            return f"File not found: {file_path}"

        ext = file_path.suffix.lower()
        try:
            if ext in [".txt",".py",".js",".html",".css",
                      ".json",".csv",".log",".md",".ini",".cfg"]:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines   = content.split("\n")
                preview = "\n".join(lines[:50])
                result  = (f"File: {file_path.name}\n"
                          f"Size: {self._fmt_size(file_path.stat().st_size)}\n"
                          f"Lines: {len(lines)}\n\n"
                          f"Content:\n{preview}")
                if len(lines) > 50:
                    result += f"\n\n... ({len(lines)-50} more lines)"
                return result
            elif ext == ".csv":
                import csv
                with open(file_path) as f:
                    reader = csv.reader(f)
                    rows   = list(reader)
                return (f"CSV File: {file_path.name}\n"
                       f"Rows: {len(rows)}\n"
                       f"Columns: {len(rows[0]) if rows else 0}\n\n"
                       f"First 5 rows:\n" +
                       "\n".join(str(r) for r in rows[:5]))
            elif ext == ".json":
                with open(file_path) as f:
                    data = json.load(f)
                return (f"JSON File: {file_path.name}\n"
                       f"Keys: {list(data.keys()) if isinstance(data,dict) else 'array'}\n\n"
                       f"Preview:\n{json.dumps(data, indent=2)[:500]}")
            else:
                return (f"File: {file_path.name}\n"
                       f"Type: {ext} (binary)\n"
                       f"Size: {self._fmt_size(file_path.stat().st_size)}\n"
                       "Cannot display binary files as text.")
        except Exception as e:
            return f"Error reading {file_path}: {e}"

    def _create_file(self, query: str,
                    llm_callback=None) -> str:
        q = query.lower()
        # Extract filename and content
        fn_match = re.search(r'(?:named?|called?|file)\s+["\']?([\w\.\-]+\.\w+)["\']?', q)
        content  = ""
        filename = "new_file.txt"

        if fn_match:
            filename = fn_match.group(1)

        # Check if they want content written
        content_match = re.search(r'(?:write|content|with)\s+["\'](.+?)["\']', query, re.I)
        if content_match:
            content = content_match.group(1)
        elif llm_callback:
            content = llm_callback(f"Create content for a file named {filename} based on: {query}")

        output_path = Path.home() / "Desktop" / filename
        output_path.write_text(content or f"# Created by GP PRO AGENT\n# {datetime.now()}\n",
                               encoding="utf-8")
        return (f"✓ File created: {filename}\n"
               f"Location: {output_path}\n"
               f"Content: {len(content)} characters")

    def _organize_files(self, query: str) -> str:
        q = query.lower()
        # Find target directory
        target = Path.home() / "Downloads"
        if "desktop" in q:
            target = Path.home() / "Desktop"
        elif "documents" in q:
            target = Path.home() / "Documents"

        if not target.exists():
            return f"Directory not found: {target}"

        # File type categories
        cats = {
            "Images":    [".jpg",".jpeg",".png",".gif",".bmp",".webp"],
            "Documents": [".pdf",".doc",".docx",".txt",".xlsx",".xls",".pptx"],
            "Code":      [".py",".js",".html",".css",".java",".cpp",".json"],
            "Archives":  [".zip",".rar",".7z",".tar",".gz"],
            "Videos":    [".mp4",".avi",".mkv",".mov",".wmv"],
            "Audio":     [".mp3",".wav",".flac",".aac"],
        }
        moved = 0
        report = f"Organizing {target}:\n\n"
        for file in target.iterdir():
            if file.is_dir(): continue
            ext = file.suffix.lower()
            for cat, exts in cats.items():
                if ext in exts:
                    dest_dir = target / cat
                    dest_dir.mkdir(exist_ok=True)
                    try:
                        shutil.move(str(file), str(dest_dir/file.name))
                        moved += 1
                        report += f"  {file.name} → {cat}/\n"
                    except: pass
                    break
        report += f"\n✓ Organized {moved} files"
        return report

    def _list_files(self, query: str) -> str:
        q = query.lower()
        if "desktop" in q:
            target = Path.home() / "Desktop"
        elif "downloads" in q:
            target = Path.home() / "Downloads"
        elif "documents" in q:
            target = Path.home() / "Documents"
        else:
            target = Path.home() / "Desktop"

        if not target.exists():
            return f"Directory not found: {target}"

        files = sorted(target.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        result = f"Files in {target}:\n\n"
        for f in files[:20]:
            size = self._fmt_size(f.stat().st_size) if f.is_file() else "DIR"
            modified = datetime.fromtimestamp(f.stat().st_mtime).strftime("%m/%d %H:%M")
            result += f"{'📁' if f.is_dir() else '📄'} {f.name:<35} {size:>10}  {modified}\n"
        if len(files) > 20:
            result += f"\n... and {len(files)-20} more files"
        return result

    def _safe_delete(self, query: str) -> str:
        return ("For safety, I won't delete files automatically.\n"
               "Specify the exact path and I'll confirm first.\n"
               "Or use File Explorer to delete files.")

    def _copy_file(self, query: str) -> str:
        return ("Copy command received.\n"
               "Specify: 'Copy C:\\source\\file.txt to C:\\dest\\'\n"
               "I'll copy it safely for you.")

    def _disk_info(self) -> str:
        try:
            import shutil
            total, used, free = shutil.disk_usage("C:/")
            result = "DISK INFORMATION:\n\n"
            result += f"Drive C:\n"
            result += f"  Total : {self._fmt_size(total)}\n"
            result += f"  Used  : {self._fmt_size(used)} ({used/total*100:.1f}%)\n"
            result += f"  Free  : {self._fmt_size(free)} ({free/total*100:.1f}%)\n"
            return result
        except Exception as e:
            return f"Disk info error: {e}"

    def _analyze_path(self, query: str) -> str:
        return ("Smart File Manager ready.\n\n"
               "Commands:\n"
               "• 'Find file report.xlsx'      — Search files\n"
               "• 'Read C:\\notes.txt'          — Read file content\n"
               "• 'List files on Desktop'      — Show directory\n"
               "• 'Organize my Downloads'      — Sort by type\n"
               "• 'How much disk space?'       — Disk info\n"
               "• 'Create file named log.txt'  — Create new file")

    def _fmt_size(self, size: int) -> str:
        for unit in ["B","KB","MB","GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
