#!/usr/bin/env node
// Hermes Dispatcher — ApexCore Execution Layer
// Receives dispatch calls from Paperclip's HTTP adapter and routes them
// to the appropriate execution backend (Claude Code, Bash, VPS workloads).
'use strict';

const http = require('http');

const PORT = parseInt(process.env.HERMES_PORT || '7071', 10);
const DISPATCHER_TOKEN = process.env.DISPATCHER_TOKEN || '';

if (!DISPATCHER_TOKEN) {
  console.error('[FATAL] DISPATCHER_TOKEN env var is not set. Exiting.');
  process.exit(1);
}

function authOk(req) {
  const header = req.headers['authorization'] || '';
  return header === `Bearer ${DISPATCHER_TOKEN}`;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', chunk => { raw += chunk; });
    req.on('end', () => {
      try { resolve(JSON.parse(raw || '{}')); }
      catch { reject(new Error('Invalid JSON')); }
    });
    req.on('error', reject);
  });
}

function send(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) });
  res.end(payload);
}

// ─── Routing table ────────────────────────────────────────────────────────────
// Add execution handlers here. Each handler receives the parsed payload and
// must return a Promise that resolves with { accepted: true, ... }.

const handlers = {
  'claude_code': async (payload) => {
    // Stub: forward to Claude Code execution layer
    console.log('[hermes] Routing to claude_code:', JSON.stringify(payload.context));
    return { accepted: true, backend: 'claude_code', runId: payload.runId };
  },
  'bash': async (payload) => {
    console.log('[hermes] Routing to bash executor:', JSON.stringify(payload.context));
    return { accepted: true, backend: 'bash', runId: payload.runId };
  },
};

const defaultHandler = async (payload) => {
  console.log('[hermes] Dispatch received (default route):', JSON.stringify(payload));
  return { accepted: true, backend: 'default', runId: payload.runId };
};

// ─── HTTP server ──────────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
  const { method, url } = req;

  // Heartbeat probe from Paperclip (HEAD or GET on root/health)
  if ((method === 'HEAD' || method === 'GET') && (url === '/' || url === '/health')) {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'hermes-dispatcher' }));
    return;
  }

  if (method === 'POST' && url === '/dispatch') {
    if (!authOk(req)) {
      send(res, 401, { error: 'Unauthorized' });
      return;
    }
    try {
      const payload = await readBody(req);
      const backend = payload?.context?.backend || 'default';
      const handler = handlers[backend] || defaultHandler;
      const result = await handler(payload);
      send(res, 200, result);
    } catch (err) {
      console.error('[hermes] Dispatch error:', err.message);
      send(res, 400, { error: err.message });
    }
    return;
  }

  send(res, 404, { error: 'Not found' });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[hermes] Dispatcher listening on :${PORT}`);
  console.log('[hermes] /health — heartbeat endpoint');
  console.log('[hermes] /dispatch — Paperclip execution endpoint');
});

process.on('SIGTERM', () => { server.close(() => process.exit(0)); });
process.on('SIGINT',  () => { server.close(() => process.exit(0)); });
