const r = await fetch('http://127.0.0.1:18092/health');
const d = await r.json();
console.log('status:', r.status, '| live:', d.live, '| dead:', d.dead, '| requests:', d.requests, '| ok:', d.ok);
