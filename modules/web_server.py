from typing import Optional, List, Dict, Any, Callable, Generator, Set, Tuple
"""
GP PRO AGENT — Web Interface
Access from phone browser: http://localhost:5000
Control AI from any device on same WiFi network.
"""
import threading, json, time, os, sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

HTML_PAGE = '''<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GP PRO AGENT</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0f1a;color:#d0e8ff;font-family:Consolas,monospace;height:100vh;display:flex;flex-direction:column}
header{background:#0d1526;border-bottom:1px solid #1a3a5c;padding:12px 16px;display:flex;align-items:center;gap:12px}
.logo{color:#00e5ff;font-size:20px;font-weight:bold}
.status{color:#00ff88;font-size:11px}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px}
.msg-user{background:#0a2a4a;color:#00e5ff;padding:10px 14px;border-radius:8px;align-self:flex-end;max-width:80%;font-size:13px}
.msg-agent{background:#0d1526;color:#00ff88;padding:10px 14px;border-radius:8px;align-self:flex-start;max-width:90%;font-size:13px;white-space:pre-wrap;border:1px solid #1a3a5c}
.msg-model{color:#ff6b2b;font-size:11px;align-self:flex-start;padding:2px 14px}
.msg-system{color:#3a5a7a;font-size:11px;align-self:center;padding:4px}
#input-area{background:#0d1526;border-top:1px solid #1a3a5c;padding:12px}
.input-row{display:flex;gap:8px}
#inp{flex:1;background:#071020;color:#d0e8ff;border:1px solid #1a3a5c;border-radius:6px;padding:10px;font-family:Consolas;font-size:14px;resize:none}
#send{background:#00e5ff;color:#0a0f1a;border:none;border-radius:6px;padding:10px 20px;font-weight:bold;cursor:pointer;font-family:Consolas}
#send:disabled{background:#1a3a5c;color:#3a5a7a}
.quick-btns{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.qbtn{background:#0a2a4a;color:#d0e8ff;border:1px solid #1a3a5c;border-radius:4px;padding:4px 10px;font-size:11px;cursor:pointer;font-family:Consolas}
.qbtn:hover{background:#1a3a5c}
#status{color:#3a5a7a;font-size:10px;padding:4px 0;text-align:center}
.brain-badge{background:#ff6b2b22;color:#ff6b2b;border:1px solid #ff6b2b44;border-radius:3px;padding:1px 6px;font-size:10px}
</style>
</head>
<body>
<header>
  <span class="logo">[GP] GP PRO AGENT</span>
  <span class="status">● Online — Web Access</span>
  <span style="margin-left:auto;color:#3a5a7a;font-size:10px" id="ram">RAM: --</span>
</header>
<div id="chat">
  <div class="msg-system">>> GP PRO AGENT Web Interface — Connected</div>
  <div class="msg-system">Ask anything or control your PC remotely</div>
</div>
<div id="input-area">
  <div class="quick-btns">
    <button class="qbtn" onclick="send('PLC ladder logic basics')">PLC Basics</button>
    <button class="qbtn" onclick="send('Safety protocols SIL LOTO')">Safety</button>
    <button class="qbtn" onclick="send('Take a screenshot')">Screenshot</button>
    <button class="qbtn" onclick="send('Open Notepad')">Open Notepad</button>
    <button class="qbtn" onclick="send('What is on my screen?')">Read Screen</button>
    <button class="qbtn" onclick="send('System status')">Status</button>
  </div>
  <div class="input-row">
    <textarea id="inp" rows="2" placeholder="Ask anything..."></textarea>
    <button id="send" onclick="doSend()">▶ SEND</button>
  </div>
  <div id="status">Ready</div>
</div>
<script>
const chat=document.getElementById('chat');
const inp=document.getElementById('inp');
const btn=document.getElementById('send');
const st=document.getElementById('status');

inp.addEventListener('keydown',e=>{
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();doSend()}
});

function addMsg(cls,text){
  const d=document.createElement('div');
  d.className=cls;
  d.textContent=text;
  chat.appendChild(d);
  chat.scrollTop=chat.scrollHeight;
  return d;
}

async function doSend(){
  const q=inp.value.trim();
  if(!q)return;
  inp.value='';
  btn.disabled=true;
  st.textContent='Processing...';
  addMsg('msg-user',q);
  const thinking=addMsg('msg-system','Thinking...');
  try{
    const r=await fetch('/query',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({query:q})
    });
    const d=await r.json();
    thinking.remove();
    if(d.brain){
      addMsg('msg-model',`[${d.brain.toUpperCase()} BRAIN | ${d.duration}s | ${d.accuracy}%]`);
    }
    addMsg('msg-agent',d.answer);
    st.textContent=`Done in ${d.duration}s | Brain: ${d.brain}`;
  }catch(e){
    thinking.remove();
    addMsg('msg-agent','Error: '+e.message);
    st.textContent='Error';
  }
  btn.disabled=false;
}

function send(q){inp.value=q;doSend()}

// Poll RAM usage
setInterval(async()=>{
  try{
    const r=await fetch('/status');
    const d=await r.json();
    document.getElementById('ram').textContent='RAM: '+d.ram_mb+'MB';
  }catch(e){}
},3000);
</script>
</body>
</html>'''

class WebServer:
    def __init__(self, agent_callback, port=5000):
        self._callback = agent_callback
        self._port     = port
        self._running  = False
        self._server   = None

    def start(self):
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()
        print(f"[WEB] Server starting at http://localhost:{self._port}")

    def _run(self):
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import json, os

            callback = self._callback
            port     = self._port

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args): pass  # Suppress logs

                def do_GET(self):
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-Type','text/html')
                        self.end_headers()
                        self.wfile.write(HTML_PAGE.encode())
                    elif self.path == '/status':
                        self.send_response(200)
                        self.send_header('Content-Type','application/json')
                        self.end_headers()
                        try:
                            import psutil
                            mb = psutil.Process(os.getpid()).memory_info().rss/(1024**2)
                        except: mb = 0
                        self.wfile.write(json.dumps({
                            "ram_mb": round(mb,1),
                            "status": "online"
                        }).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

                def do_POST(self):
                    if self.path == '/query':
                        length = int(self.headers['Content-Length'])
                        body   = json.loads(self.rfile.read(length))
                        query  = body.get('query','')
                        result = callback(query)
                        self.send_response(200)
                        self.send_header('Content-Type','application/json')
                        self.send_header('Access-Control-Allow-Origin','*')
                        self.end_headers()
                        self.wfile.write(json.dumps(result).encode())

            server = HTTPServer(('0.0.0.0', port), Handler)
            self._server = server
            server.serve_forever()
        except Exception as e:
            print(f"[WEB] Server error: {e}")

    def stop(self):
        self._running = False
        if self._server:
            self._server.shutdown()

    def get_url(self):
        try:
            import socket
            ip = socket.gethostbyname(socket.gethostname())
            return f"http://{ip}:{self._port}"
        except:
            return f"http://localhost:{self._port}"
