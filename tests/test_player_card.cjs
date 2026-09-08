// Run with: node tests/test_player_card.cjs
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../frontend/js/player-card.js'), 'utf8')
    .replace(/^import .*\n/, '').replace('export function ', 'function ');
const context = { apiBaseUrl: '', URL, AbortSignal };
vm.createContext(context);
vm.runInContext(source, context);
const html = context.createOfficialPlayerCardHtml({
    sp_id: 844273018, player_name: '<img src=x onerror=alert(1)>',
    ovr: 141, grade: 8, position: 'CM', salary: 29,
});
assert(!html.includes('<img src=x'));
assert(html.includes('&lt;img src=x'));
assert(html.includes('class="ovr">141'));
assert(html.includes('gold">8'));
console.log('PASS: player identity escaped; adjusted OVR and enhancement retained');
