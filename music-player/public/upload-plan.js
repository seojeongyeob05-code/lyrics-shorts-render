// 많은 파일을 한 번에 올릴 때 요청 하나가 너무 커지지 않도록 여러 묶음으로 나눈다.
// 같은 이름의 음원과 .lrc는 서버가 같은 요청 안에서 짝짓기 때문에 항상 같은 묶음에 넣는다.
export const BATCH_FILES = 20;
export const BATCH_BYTES = 200 * 1024 * 1024;

const baseKey = (name) => name.replace(/\.[^.]*$/, '').normalize('NFC').trim().toLowerCase();

export function planUploads(files, { maxFileBytes = Infinity, batchFiles = BATCH_FILES, batchBytes = BATCH_BYTES } = {}) {
  const tooLarge = [];
  const groups = new Map(); // 이름(확장자 제외) → 파일들, 처음 나온 순서 유지
  for (const file of files) {
    if (file.size > maxFileBytes) {
      tooLarge.push(file);
      continue;
    }
    const key = baseKey(file.name);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(file);
  }

  const batches = [];
  let current = [];
  let currentBytes = 0;
  for (const group of groups.values()) {
    const bytes = group.reduce((sum, f) => sum + f.size, 0);
    const fits = current.length + group.length <= batchFiles && currentBytes + bytes <= batchBytes;
    if (current.length && !fits) {
      batches.push(current);
      current = [];
      currentBytes = 0;
    }
    current.push(...group); // 묶음 한도보다 큰 그룹도 혼자 한 묶음으로 보낸다
    currentBytes += bytes;
  }
  if (current.length) batches.push(current);
  return { batches, tooLarge };
}

// 묶음별 서버 응답을 하나로 합친다.
export function mergeResults(results) {
  const merged = { added: [], duplicates: [], rejected: [], lyrics: { attached: [], unmatched: [] } };
  for (const r of results) {
    merged.added.push(...(r.added ?? []));
    merged.duplicates.push(...(r.duplicates ?? []));
    merged.rejected.push(...(r.rejected ?? []));
    merged.lyrics.attached.push(...(r.lyrics?.attached ?? []));
    merged.lyrics.unmatched.push(...(r.lyrics?.unmatched ?? []));
  }
  return merged;
}
