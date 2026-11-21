// Static check of the question bank: every question has an explanation, mc has 1 answer + 3 wrong,
// no duplicate options, balanced $…$ math, and the page script parses.
const fs = require('fs'), path = require('path');
const h = fs.readFileSync(path.join(__dirname, '..', 'chem-daily.html'), 'utf8');
const txt = h.split('<script type="text/plain" id="course">')[1].split('</script>')[0];
const js = h.split('<script>\n(function')[1].split('</script>')[0];
new Function('(function' + js);
const parseCourse = eval('(' + js.match(/function parseCourse[\s\S]*?return lessons;\n  }/)[0] + ')');
const L = parseCourse(txt); const bad = []; let n = 0;
for (const l of L) {
  if (!l.concept.length) bad.push(l.id + ' no concept');
  for (const q of l.qs) {
    n++;
    if (!q.q || !q.e) bad.push(q.id + ' missing q/e');
    if (q.type === 'mc' && (q.a.length !== 1 || q.w.length !== 3)) bad.push(q.id + ' mc shape');
    if (q.type === 'ord' && q.s.length < 3) bad.push(q.id + ' ord too short');
    const opts = [...q.a, ...q.w]; if (new Set(opts).size !== opts.length) bad.push(q.id + ' duplicate option');
    if ((q.q + q.e + q.a.join() + q.w.join() + q.s.join()).split('$').length % 2 === 0) bad.push(q.id + ' unbalanced $');
  }
}
console.log(L.length + ' lessons, ' + n + ' questions');
console.log(L.map(l => l.id + ':' + l.qs.length).join(' '));
if (bad.length) { console.log('PROBLEMS', bad); process.exit(1); } else console.log('OK');
