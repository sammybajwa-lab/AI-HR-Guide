const employee = document.getElementById('employee');
const message = document.getElementById('message');
const confirmBox = document.getElementById('confirm');
const send = document.getElementById('send');
const result = document.getElementById('result');
const answer = document.getElementById('answer');
const statusEl = document.getElementById('result-status');
const sources = document.getElementById('sources');
const trace = document.getElementById('trace');
const clarification = document.getElementById('clarification');

function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
}

for (const button of document.querySelectorAll('.quick')) {
  button.addEventListener('click', () => {
    employee.value = button.dataset.employee;
    message.value = button.dataset.prompt;
    message.focus();
  });
}

async function checkHealth() {
  const el = document.getElementById('health');
  try {
    const r = await fetch('/health');
    const data = await r.json();
    el.textContent = data.mcp === 'ok' ? `${data.mcp_tool_count} MCP tools ready` : 'tool layer degraded';
  } catch {
    el.textContent = 'health check unavailable';
  }
}

send.addEventListener('click', async () => {
  const text = message.value.trim();
  if (!text) return;
  send.disabled = true;
  send.textContent = 'Running…';
  result.classList.remove('hidden');
  answer.textContent = 'Checking policy and tool data…';
  sources.innerHTML = '';
  trace.innerHTML = '';
  clarification.classList.add('hidden');
  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        message: text,
        employee_id: employee.value.trim() || null,
        confirm_action: confirmBox.checked
      })
    });
    const data = await response.json();
    answer.textContent = data.answer || 'No answer returned.';
    statusEl.textContent = data.status || '';
    if (data.clarification_question) {
      clarification.textContent = data.clarification_question;
      clarification.classList.remove('hidden');
    }
    for (const s of data.citations || []) {
      const div = document.createElement('div');
      div.className = 'source';
      div.innerHTML = `<strong>${esc(s.document_id)} · ${esc(s.section)}</strong><div>${esc(s.snippet)}</div>`;
      sources.appendChild(div);
    }
    for (const t of data.trace || []) {
      const div = document.createElement('div');
      div.className = 'trace-item';
      div.innerHTML = `<strong>${esc(t.tool)} ${t.ok ? '✓' : '✕'}</strong><div>${esc(t.elapsed_ms ?? '')} ms</div><code>args: ${esc(JSON.stringify(t.arguments))}\nresult: ${esc(t.result_summary)}</code>`;
      trace.appendChild(div);
    }
  } catch {
    answer.textContent = 'The request failed before a grounded answer was returned. No action was taken.';
    statusEl.textContent = 'request_error';
  } finally {
    send.disabled = false;
    send.textContent = 'Run request';
  }
});

checkHealth();
