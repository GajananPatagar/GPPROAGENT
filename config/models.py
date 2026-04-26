MODELS = {
    "master":  {
        "name":"Llama-3.1-8B — Master Brain",
        "file":"llama3-master.gguf",
        "url":"https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size_gb":4.9,"ram_mb":450,"speed_s":6,"accuracy":95,"can_chat":True,
        "role":"Deep reasoning, planning, analysis, general questions",
        "triggers":["analyze","explain","plan","why","how does","what is","tell me about","describe","understand","compare","difference","best way","suggest","recommend","think","reason"],
        "color":"#00e5ff"
    },
    "reflex":  {
        "name":"Phi-3-Mini — Reflex Brain",
        "file":"phi3-reflex.gguf",
        "url":"https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
        "size_gb":2.4,"ram_mb":200,"speed_s":0.8,"accuracy":82,"can_chat":True,
        "role":"Ultra fast simple answers, greetings, quick facts",
        "triggers":["hi","hello","hey","who are you","your name","what are you","quick","fast","simple","yes or no","is it","are you","can you","do you","will you"],
        "color":"#00ff88"
    },
    "plc":     {
        "name":"Mistral-7B — PLC Brain",
        "file":"mistral7b-plc.gguf",
        "url":"https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "size_gb":4.4,"ram_mb":400,"speed_s":5,"accuracy":93,"can_chat":True,
        "role":"PLC, ladder logic, SCADA, industrial automation, Siemens, Allen Bradley",
        "triggers":["plc","ladder","rung","coil","contact","scada","allen bradley","rslogix","studio 5000","siemens","tia portal","modbus","profibus","profinet","ethernet/ip","opc","hmi","vfd","relay","sensor","actuator","industrial","automation","iec 61131","function block","structured text"],
        "color":"#ff6b2b"
    },
    "coder":   {
        "name":"DeepSeek-Coder — Code Brain",
        "file":"deepseek-coder.gguf",
        "url":"https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q8_0.gguf",
        "size_gb":1.4,"ram_mb":200,"speed_s":2,"accuracy":91,"can_chat":True,
        "role":"Python, coding, scripts, debugging, programming",
        "triggers":["code","python","script","function","class","debug","error","syntax","import","def ","print(","variable","loop","if else","try except","fix code","write code","program","algorithm","api","json","csv","database","sql","html","javascript"],
        "color":"#bf5fff"
    },
    "screen":  {
        "name":"Gemma-2B — Screen Brain",
        "file":"gemma2b-screen.gguf",
        "url":"https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q8_0.gguf",
        "size_gb":2.5,"ram_mb":250,"speed_s":1.5,"accuracy":88,"can_chat":True,
        "role":"GUI automation, clicking, typing, navigating software on screen",
        "triggers":["click","type","write in","navigate","go to","select","copy","paste","right click","double click","scroll","drag","press","keyboard","mouse","automate","button","checkbox","menu","toolbar","window","tab","minimize","maximize","close window","switch to"],
        "color":"#ffaa00"
    },
    "safety":  {
        "name":"Gemma-2B-Safety — Safety Brain",
        "file":"gemma2b-safety.gguf",
        "url":"https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q6_K.gguf",
        "size_gb":1.9,"ram_mb":220,"speed_s":1.5,"accuracy":94,"can_chat":True,
        "role":"Safety protocols, E-stop, SIL, LOTO, hazard, risk",
        "triggers":["safety","estop","e-stop","emergency stop","risk","alarm","fault","danger","hazard","sil","interlock","loto","lockout","tagout","ppe","protection","safe","unsafe","accident","incident","procedure","permit"],
        "color":"#ff4444"
    },
    "memory":  {
        "name":"MiniLM — Memory Search",
        "file":"minilm-memory.gguf",
        "url":"https://huggingface.co/second-state/All-MiniLM-L6-v2-Embedding-GGUF/resolve/main/all-MiniLM-L6-v2-Q8_0.gguf",
        "size_gb":0.04,"ram_mb":64,"speed_s":0.1,"accuracy":90,"can_chat":False,
        "role":"Embedding search only — not a chat model",
        "triggers":[],
        "color":"#00ffcc"
    },
    "docs":    {
        "name":"Qwen2-7B — Documentation Brain",
        "file":"qwen2-docs.gguf",
        "url":"https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF/resolve/main/qwen2-7b-instruct-q4_k_m.gguf",
        "size_gb":4.5,"ram_mb":420,"speed_s":6,"accuracy":92,"can_chat":True,
        "role":"Writing documents, reports, emails, summaries, technical writing",
        "triggers":["write a","draft","document","report","email","letter","summary","summarize","generate report","technical document","create document","write report","compose","format","template"],
        "color":"#aaaaff"
    },
    "learner": {
        "name":"Llama-3.2-3B — Learning Brain",
        "file":"llama3-learner.gguf",
        "url":"https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q8_0.gguf",
        "size_gb":3.4,"ram_mb":350,"speed_s":3,"accuracy":89,"can_chat":True,
        "role":"Opening software, operating applications, step by step tutorials",
        "triggers":["open","launch","start","run app","how to use","operate","tutorial","show me how","step by step","guide me","teach","learn how","use this software","install","setup","configure","pcwin","notepad","excel","word","browser","calculator"],
        "color":"#ffdd00"
    },
    "ocr":     {
        "name":"Phi-3-Mini — OCR Vision Brain",
        "file":"phi3-ocr.gguf",
        "url":"https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
        "size_gb":2.4,"ram_mb":200,"speed_s":0.5,"accuracy":90,"can_chat":True,
        "role":"Reading screen text, OCR, vision, screenshot analysis",
        "triggers":["read screen","what is on screen","ocr","text on screen","extract text","read this image","what does screen show","analyze screenshot","describe screen","vision","see screen","look at screen"],
        "color":"#ff88ff"
    },
    "math":    {
        "name":"Phi-3-Math — Math Brain",
        "file":"phi3-math.gguf",
        "url":"https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
        "size_gb":2.4,"ram_mb":200,"speed_s":1,"accuracy":93,"can_chat":True,
        "role":"Math calculations, engineering formulas, unit conversions",
        "triggers":["calculate","compute","formula","convert","equation","math","plus","minus","multiply","divide","percentage","square root","power","log","sin","cos","psi","bar","celsius","fahrenheit","ohm","voltage","current","resistance","area","volume","speed","force","pressure"],
        "color":"#88ffaa"
    },
}
TOTAL_GB = sum(m["size_gb"] for m in MODELS.values())
CHAT_MODELS = {k:v for k,v in MODELS.items() if v.get("can_chat",True)}
