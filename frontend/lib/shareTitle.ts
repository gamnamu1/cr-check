const TARGET = 28;    // 자른 뒤 목표 상한 (모바일 카드 1~2줄 기준 휴리스틱)
const GRACE = 32;     // 이 길이 이하면 자르지 않음
const MIN = 12;       // 이보다 짧게는 만들지 않음
const SEP_MIN = 14;   // 구분자 앞 주제부가 이보다 짧으면 구분자 무시
const SEP_TOL = 2;    // 구분자가 TARGET을 이만큼 넘어도 허용
const SEPARATORS = ['…', '...', '‥', ' - ', ' – ', '|', '｜', '│'];
const PAIRS: [string, string][] = [
  ['"', '"'], ["'", "'"], ['“', '”'], ['‘', '’'],
  ['(', ')'], ['[', ']'], ['「', '」'], ['『', '』'],
];

const len = (s: string): number => Array.from(s).length;
const count = (s: string, ch: string): number => s.split(ch).length - 1;

/** 열린 채 남은 따옴표·괄호의 닫는 문자와 위치. 없으면 null */
function unmatched(s: string): { close: string; pos: number } | null {
  for (const [o, c] of PAIRS) {
    const open = o === c ? count(s, o) % 2 === 1 : count(s, o) > count(s, c);
    if (open) return { close: c, pos: s.lastIndexOf(o) };
  }
  return null;
}

function tidyEnd(s: string): string {
  s = s.replace(/[\s‘“(\[「『,·:;!?~\-…]+$/u, '');
  for (const q of ['"', "'"]) {          // 끝의 직선 따옴표는 짝이 없을 때만 제거
    if (s.endsWith(q) && count(s, q) % 2 === 1)
      s = s.slice(0, -1).replace(/[\s,·]+$/u, '');
  }
  return s;
}

/** SNS 공유용 기사 제목 축약. GRACE 이하면 원문 그대로 반환. */
export function truncateShareTitle(raw: string, target = TARGET): string {
  const title = raw.replace(/\s+/g, ' ').trim();
  const chars = Array.from(title);
  if (chars.length <= GRACE) return title;

  // 1) 구조 구분자에서 자르기 — 허용 범위 안 마지막 구분자 (인용문·괄호 안의 구분자는 제외)
  let best = -1;
  for (const sep of SEPARATORS) {
    let idx = title.indexOf(sep);
    while (idx !== -1) {
      const before = title.slice(0, idx);
      const n = len(before);
      if (n >= SEP_MIN && n <= target + SEP_TOL && unmatched(before) === null && n > best) best = n;
      idx = title.indexOf(sep, idx + 1);
    }
  }
  if (best !== -1) return `${tidyEnd(chars.slice(0, best).join(''))}…`;

  // 2) 어절 경계(공백·가운뎃점·쉼표)에서 자르기 — target의 60% 이후에 있을 때만
  let cut = chars.slice(0, target).join('');
  const ls = Math.max(cut.lastIndexOf(' '), cut.lastIndexOf('·'), cut.lastIndexOf(','));
  if (ls >= Math.floor(target * 0.6)) cut = cut.slice(0, ls);
  cut = tidyEnd(cut);

  // 3) 열린 따옴표·괄호 처리 — 잔여가 2자 이하면 시작 전으로 되돌리고,
  //    아니면 '…' 뒤에 닫는 문자를 보강한다
  const u = unmatched(cut);
  if (u) {
    const remainder = tidyEnd(cut.slice(u.pos + 1));
    const back = tidyEnd(cut.slice(0, u.pos));
    if (len(remainder) <= 2 && len(back) >= MIN) return `${back}…`;
    return `${cut}…${u.close}`;
  }
  return `${cut}…`;
}
