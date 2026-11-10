// 곡 목록 다중 선택. keys는 화면에 보이는 순서대로의 행 키(플레이리스트면 항목 id, 아니면 곡 id).

// 한 행을 누른 결과. range(Shift)면 기준 행부터 누른 행까지 모두 선택하고 기준은 그대로 둔다.
// 아니면 누른 행만 켜고 끄며, 그 행이 다음 범위 선택의 기준이 된다.
export function clickSelection(selected, keys, index, { range = false, anchor = null } = {}) {
  const next = new Set(selected);
  const anchorIndex = anchor == null ? -1 : keys.indexOf(anchor);
  if (range && anchorIndex !== -1) {
    const [from, to] = anchorIndex < index ? [anchorIndex, index] : [index, anchorIndex];
    for (let i = from; i <= to; i++) next.add(keys[i]);
    return { selected: next, anchor };
  }
  const key = keys[index];
  if (next.has(key)) next.delete(key);
  else next.add(key);
  return { selected: next, anchor: key };
}

// 목록이 바뀌면(검색, 삭제 등) 더는 보이지 않는 행은 선택에서 뺀다.
export function pruneSelection(selected, keys) {
  const visible = new Set(keys);
  return new Set([...selected].filter((k) => visible.has(k)));
}
