import subprocess, json, time, sys

proc = subprocess.Popen(
    [r'.venv\Scripts\python.exe', '-m', 'app.mcp.claims_server'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, cwd=r'D:\HP\Pdf-Ingester-v1'
)
time.sleep(2)

def send(msg):
    proc.stdin.write(json.dumps(msg) + '\n')
    proc.stdin.flush()
    time.sleep(0.8)
    return proc.stdout.readline()

# 1. initialize
r = send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'1'}}})
print('INIT:', 'OK' if '2024-11-05' in r else r[:100])

# 2. notifications/initialized
proc.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized','params':{}}) + '\n')
proc.stdin.flush()
time.sleep(0.3)

# 3. tools/list
r = send({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}})
data = json.loads(r)
tools = data.get('result',{}).get('tools',[])
print(f'TOOLS DISCOVERED: {len(tools)}')
for t in tools:
    name = t['name']
    print(f'  - {name}')

# 4. tools/call get_claim (valid ID)
r = send({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'get_claim','arguments':{'claim_id':'CLM-W8-001'}}})
data = json.loads(r)
content = data.get('result',{}).get('content',[])
result_text = content[0].get('text','') if content else 'EMPTY'
print('TOOL CALL (valid ID):', result_text[:150])

# 5. tools/call get_claim (bad ID - recoverable error test)
r = send({'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'get_claim','arguments':{'claim_id':'CLM-W8-999'}}})
data = json.loads(r)
content = data.get('result',{}).get('content',[])
result_text = content[0].get('text','') if content else 'EMPTY'
print('TOOL CALL (bad ID):', result_text[:200])

proc.terminate()
print('\nDONE')
