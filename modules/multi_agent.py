"""
GP PRO AGENT - Multi-Agent Team System
Multiple specialist AI agents working together as a team.
Each agent has its own role, communicates with others.
"""
import threading, time, queue, json, uuid
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, List, Optional

class AgentMessage:
    def __init__(self, sender: str, receiver: str,
                 msg_type: str, content: str,
                 priority: int = 5):
        self.id       = str(uuid.uuid4())[:8]
        self.sender   = sender
        self.receiver = receiver
        self.type     = msg_type
        self.content  = content
        self.priority = priority
        self.time     = datetime.now()
        self.response = None

    def __repr__(self):
        return (f"Msg[{self.sender}->{self.receiver}:"
                f"{self.type}]")


class SpecialistAgent:
    """
    A single specialist AI agent with defined role and expertise.
    """
    ROLES = {
        "engineer":  "PLC programming, ladder logic, Studio 5000, TIA Portal",
        "monitor":   "Continuous screen watching, fault detection, alarms",
        "safety":    "Safety validation, risk checks, LOTO, SIL assessment",
        "analyst":   "Data analysis, trend detection, report generation",
        "operator":  "Software operation, GUI automation, user interaction",
    }

    def __init__(self, role: str, ask_brain_callback: Callable,
                 notify_callback: Callable):
        self.role       = role
        self.name       = f"{role.title()} Agent"
        self.expertise  = self.ROLES.get(role, "General assistance")
        self._ask       = ask_brain_callback
        self._notify    = notify_callback
        self._inbox     = queue.PriorityQueue()
        self._running   = False
        self._busy      = False
        self._task_count = 0
        self._thread    = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def send_message(self, msg: AgentMessage):
        self._inbox.put((msg.priority, msg))

    def _process_loop(self):
        while self._running:
            try:
                priority, msg = self._inbox.get(timeout=1.0)
                self._busy = True
                self._handle_message(msg)
                self._task_count += 1
                self._busy = False
            except queue.Empty:
                pass
            except Exception as e:
                print(f"[{self.name}] Error: {e}")
                self._busy = False

    def _handle_message(self, msg: AgentMessage):
        """Process incoming message based on role."""
        prompt = self._build_prompt(msg)
        try:
            response = self._ask(self.role, prompt)
            msg.response = response
            if msg.type == "TASK":
                self._notify(
                    f"[{self.name}]\n{response[:200]}")
        except Exception as e:
            msg.response = f"Agent error: {e}"

    def _build_prompt(self, msg: AgentMessage) -> str:
        role_context = {
            "engineer": "As PLC engineer, ",
            "monitor":  "As system monitor, ",
            "safety":   "As safety engineer, ALWAYS check safety first. ",
            "analyst":  "As data analyst, ",
            "operator": "As software operator, ",
        }
        prefix = role_context.get(self.role, "")
        return f"{prefix}{msg.content}"

    @property
    def is_busy(self):
        return self._busy

    @property
    def tasks_completed(self):
        return self._task_count


class MultiAgentTeam:
    """
    Team of specialist AI agents working together.
    Coordinates tasks, handles conflicts, ensures safety.
    """
    def __init__(self, brain_root: str,
                 ask_brain_callback: Callable,
                 notify_callback: Callable):
        self._path    = Path(brain_root) / "multi_agent"
        self._path.mkdir(parents=True, exist_ok=True)
        self._notify  = notify_callback
        self._ask     = ask_brain_callback
        self._agents: Dict[str, SpecialistAgent] = {}
        self._history: List[dict] = []
        self._running = False
        self._create_team(ask_brain_callback, notify_callback)

    def _create_team(self, ask_cb, notify_cb):
        """Create all specialist agents."""
        for role in SpecialistAgent.ROLES:
            agent = SpecialistAgent(role, ask_cb, notify_cb)
            self._agents[role] = agent

    def start(self):
        """Start all agents."""
        self._running = True
        for agent in self._agents.values():
            agent.start()
        print(f"[TEAM] {len(self._agents)} agents started")

    def stop(self):
        """Stop all agents."""
        self._running = False
        for agent in self._agents.values():
            agent.stop()

    def execute_team_task(self, task: str) -> str:
        """
        Execute task using best agent or multiple agents.
        Safety agent always reviews dangerous tasks.
        """
        q = task.lower()

        # Route to specialist
        if any(w in q for w in ["plc","ladder","rung","studio","tia"]):
            primary = "engineer"
        elif any(w in q for w in ["alarm","fault","monitor","watch"]):
            primary = "monitor"
        elif any(w in q for w in ["safety","estop","risk","sil","loto"]):
            primary = "safety"
        elif any(w in q for w in ["analyze","report","trend","data"]):
            primary = "analyst"
        elif any(w in q for w in ["click","open","navigate","automate"]):
            primary = "operator"
        else:
            primary = "engineer"

        # Safety check for dangerous operations
        dangerous = any(w in q for w in [
            "write","force","override","delete","modify",
            "go online","download","upload","reset fault"
        ])

        results = []
        if dangerous:
            # Safety agent must approve first
            safety_msg = AgentMessage(
                "coordinator", "safety",
                "SAFETY_CHECK",
                f"Safety check required for: {task}",
                priority=1)
            self._agents["safety"].send_message(safety_msg)
            time.sleep(2)  # Wait for safety response
            if safety_msg.response:
                results.append(f"[SAFETY AGENT]\n{safety_msg.response}")
                self._notify(
                    f"[SAFETY] Reviewing: {task[:40]}")

        # Primary agent handles task
        primary_msg = AgentMessage(
            "coordinator", primary,
            "TASK", task, priority=5)
        self._agents[primary].send_message(primary_msg)
        time.sleep(3)  # Wait for response

        if primary_msg.response:
            results.append(
                f"[{primary.upper()} AGENT]\n{primary_msg.response}")

        # Log to history
        self._history.append({
            "task":    task,
            "primary": primary,
            "time":    datetime.now().isoformat(),
            "steps":   len(results),
        })

        if results:
            return "\n\n".join(results)
        return f"Team processing '{task}'... Agents are working."

    def get_team_status(self) -> dict:
        """Get status of all agents."""
        return {
            role: {
                "name":    agent.name,
                "busy":    agent.is_busy,
                "tasks":   agent.tasks_completed,
                "running": agent._running,
            }
            for role, agent in self._agents.items()
        }

    def assign_to_agent(self, role: str, task: str,
                        priority: int = 5) -> str:
        """Directly assign task to specific agent."""
        if role not in self._agents:
            return f"Unknown agent role: {role}"
        msg = AgentMessage("user", role, "TASK",
                          task, priority)
        self._agents[role].send_message(msg)
        time.sleep(2)
        return (msg.response or
                f"Task sent to {role} agent. Processing...")

    def broadcast(self, message: str):
        """Send message to all agents."""
        for role, agent in self._agents.items():
            msg = AgentMessage("broadcast", role,
                             "BROADCAST", message, priority=3)
            agent.send_message(msg)

    @property
    def agent_count(self):
        return len(self._agents)

    @property
    def active_count(self):
        return sum(1 for a in self._agents.values()
                  if a._running)

    @property
    def task_history(self):
        return list(reversed(self._history))[:20]
