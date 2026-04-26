"""
GP PRO AGENT - Real PLC Direct Connection
Connects directly to PLC hardware via Ethernet/IP or Modbus.
No software needed - raw protocol communication.
"""
import threading, time, json, socket
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

class PLCTag:
    def __init__(self, name: str, address: int,
                 data_type: str = "DINT"):
        self.name      = name
        self.address   = address
        self.data_type = data_type
        self.value     = None
        self.quality   = "Unknown"
        self.timestamp = None

    def to_dict(self):
        return {
            "name":      self.name,
            "address":   self.address,
            "data_type": self.data_type,
            "value":     self.value,
            "quality":   self.quality,
            "timestamp": self.timestamp,
        }


class PLCDirectConnection:
    """
    Direct PLC hardware connection.
    Supports: Modbus TCP/RTU, Ethernet/IP simulation,
    S7 protocol basics.
    """
    def __init__(self, brain_root):
        self._path      = Path(brain_root) / "plc_direct"
        self._path.mkdir(parents=True, exist_ok=True)
        self._config    = self._path / "connections.json"
        self._connections = {}
        self._active    = {}
        self._tags      = {}
        self._polling   = False
        self._poll_thread = None
        self._callbacks = []
        self._load_config()

    def _load_config(self):
        try:
            if self._config.exists():
                with open(self._config) as f:
                    self._connections = json.load(f)
        except Exception:
            self._connections = {}

    def _save_config(self):
        try:
            with open(self._config, "w") as f:
                json.dump(self._connections, f, indent=2)
        except Exception as e:
            print(f"[PLC-DIRECT] Config save error: {e}")

    def add_connection(self, name: str, protocol: str,
                       ip: str, port: int = 502,
                       unit_id: int = 1) -> dict:
        conn = {
            "name":     name,
            "protocol": protocol,
            "ip":       ip,
            "port":     port,
            "unit_id":  unit_id,
            "connected": False,
        }
        self._connections[name] = conn
        self._save_config()
        return conn

    def connect(self, conn_name: str) -> tuple:
        """Connect to PLC."""
        conn = self._connections.get(conn_name)
        if not conn:
            return False, f"Connection '{conn_name}' not found"
        protocol = conn.get("protocol","modbus").lower()
        ip       = conn["ip"]
        port     = conn["port"]
        try:
            if protocol in ("modbus","modbus_tcp"):
                return self._connect_modbus(conn_name, conn)
            elif protocol == "s7":
                return self._connect_s7(conn_name, conn)
            elif protocol == "ping":
                return self._ping_test(ip)
            else:
                return False, f"Unknown protocol: {protocol}"
        except Exception as e:
            return False, str(e)

    def _connect_modbus(self, name: str,
                        conn: dict) -> tuple:
        try:
            from pymodbus.client import ModbusTcpClient
            client = ModbusTcpClient(
                conn["ip"], port=conn["port"])
            if client.connect():
                self._active[name] = client
                self._connections[name]["connected"] = True
                self._save_config()
                return True, f"Connected to {conn['ip']}:{conn['port']}"
            return False, f"Cannot connect to {conn['ip']}"
        except ImportError:
            return False, "Install pymodbus: pip install pymodbus"
        except Exception as e:
            return False, str(e)

    def _connect_s7(self, name: str, conn: dict) -> tuple:
        try:
            import snap7
            client = snap7.client.Client()
            client.connect(conn["ip"], 0, 1)
            if client.get_connected():
                self._active[name] = client
                return True, f"S7 Connected to {conn['ip']}"
            return False, "S7 connection failed"
        except ImportError:
            return False, "Install python-snap7: pip install python-snap7"
        except Exception as e:
            return False, str(e)

    def _ping_test(self, ip: str) -> tuple:
        """Basic connectivity test."""
        try:
            sock = socket.create_connection((ip, 502), timeout=3)
            sock.close()
            return True, f"Port 502 reachable at {ip}"
        except Exception:
            try:
                sock = socket.create_connection((ip, 102), timeout=3)
                sock.close()
                return True, f"S7 Port 102 reachable at {ip}"
            except:
                return False, f"Cannot reach {ip}"

    def disconnect(self, conn_name: str):
        if conn_name in self._active:
            try:
                self._active[conn_name].close()
            except: pass
            del self._active[conn_name]
            if conn_name in self._connections:
                self._connections[conn_name]["connected"] = False
                self._save_config()

    def read_tag(self, conn_name: str,
                 address: int, count: int = 1,
                 data_type: str = "DINT") -> Optional[Any]:
        """Read tag value from PLC."""
        client = self._active.get(conn_name)
        if not client:
            return None
        try:
            # Try Modbus
            if hasattr(client, 'read_holding_registers'):
                result = client.read_holding_registers(
                    address, count, unit=1)
                if not result.isError():
                    regs = result.registers
                    if data_type == "BOOL":
                        return bool(regs[0])
                    elif data_type == "REAL" and len(regs) >= 2:
                        import struct
                        raw = struct.pack(">HH", regs[0], regs[1])
                        return struct.unpack(">f", raw)[0]
                    return regs[0] if count==1 else regs
        except Exception as e:
            print(f"[PLC-DIRECT] Read error: {e}")
        return None

    def write_tag(self, conn_name: str,
                  address: int, value: Any,
                  data_type: str = "DINT") -> bool:
        """Write tag value to PLC."""
        client = self._active.get(conn_name)
        if not client:
            return False
        try:
            if hasattr(client, 'write_register'):
                if data_type == "BOOL":
                    result = client.write_coil(address, bool(value))
                elif data_type == "REAL":
                    import struct
                    raw  = struct.pack(">f", float(value))
                    regs = struct.unpack(">HH", raw)
                    result = client.write_registers(address, list(regs))
                else:
                    result = client.write_register(address, int(value))
                return not result.isError()
        except Exception as e:
            print(f"[PLC-DIRECT] Write error: {e}")
        return False

    def read_all_tags(self, conn_name: str) -> dict:
        """Read all configured tags."""
        results = {}
        for tag_name, tag in self._tags.items():
            val = self.read_tag(
                conn_name, tag.address, 1, tag.data_type)
            tag.value     = val
            tag.quality   = "Good" if val is not None else "Bad"
            tag.timestamp = datetime.now().isoformat()
            results[tag_name] = tag.to_dict()
        return results

    def add_tag(self, name: str, address: int,
                data_type: str = "DINT"):
        self._tags[name] = PLCTag(name, address, data_type)

    def start_polling(self, conn_name: str, interval: float = 1.0):
        """Start continuous polling."""
        self._polling = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            args=(conn_name, interval),
            daemon=True)
        self._poll_thread.start()

    def stop_polling(self):
        self._polling = False

    def _poll_loop(self, conn_name: str, interval: float):
        while self._polling:
            values = self.read_all_tags(conn_name)
            for cb in self._callbacks:
                try:
                    cb(values)
                except Exception:
                    pass
            time.sleep(interval)

    def on_update(self, callback):
        self._callbacks.append(callback)

    def execute_command(self, command: str) -> str:
        """Natural language PLC command execution."""
        q = command.lower()
        # Find active connection
        active_conns = list(self._active.keys())

        if not active_conns and not any(w in q for w in
                                        ["add","configure","connect"]):
            return ("No active PLC connections.\n"
                   "Add a connection first:\n"
                   "'Connect to PLC at 192.168.1.1'\n"
                   "Protocol: Modbus TCP (port 502) or S7 (port 102)")

        if "connect" in q or "add connection" in q:
            import re
            ip = re.search(r'\d+\.\d+\.\d+\.\d+', q)
            if ip:
                ip_str = ip.group()
                proto  = "s7" if any(w in q for w in
                    ["s7","siemens","tia"]) else "modbus"
                port   = 102 if proto=="s7" else 502
                conn   = self.add_connection(
                    f"PLC_{ip_str}", proto, ip_str, port)
                ok, msg = self.connect(f"PLC_{ip_str}")
                return (f"{'OK' if ok else 'FAILED'}: {msg}\n"
                       f"Protocol: {proto.upper()} | IP: {ip_str}")
            return "Specify IP: 'Connect to PLC at 192.168.1.1'"

        if not active_conns:
            return "No active connections. Connect first."

        conn_name = active_conns[0]

        if "read" in q:
            import re
            addr = re.search(r'\b(\d+)\b', q)
            if addr:
                val = self.read_tag(conn_name, int(addr.group()))
                return f"Address {addr.group()} = {val}"
            vals = self.read_all_tags(conn_name)
            result = f"Tags from {conn_name}:\n"
            for name, tag in vals.items():
                result += f"  {name}: {tag['value']} ({tag['quality']})\n"
            return result

        if "write" in q or "set" in q:
            import re
            m = re.search(r'(?:write|set)\s+(\d+)\s+(?:to\s+)?(\d+)', q)
            if m:
                addr = int(m.group(1))
                val  = int(m.group(2))
                ok   = self.write_tag(conn_name, addr, val)
                return (f"{'OK' if ok else 'FAILED'}: "
                       f"Write {val} to address {addr}")
            return "Specify: 'write 100 to 1234' (address, value)"

        if "status" in q or "info" in q:
            result = "PLC Direct Connection Status:\n\n"
            for name, conn in self._connections.items():
                status = "Connected" if name in self._active else "Disconnected"
                result += (f"  {name}: {status}\n"
                          f"  {conn['protocol'].upper()} | "
                          f"{conn['ip']}:{conn['port']}\n\n")
            return result if self._connections else "No connections configured."

        return (f"PLC Direct ready. Connected: {active_conns}\n"
               "Commands: 'read tags' | 'write 100 to addr' | 'status'")

    @property
    def connection_count(self):
        return len(self._connections)

    @property
    def active_count(self):
        return len(self._active)
