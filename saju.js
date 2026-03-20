// ===== 사주 명리 데이터 =====

const STEMS = ['갑','을','병','정','무','기','경','신','임','계'];
const STEMS_HANJA = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸'];
const BRANCHES = ['자','축','인','묘','진','사','오','미','신','유','술','해'];
const BRANCHES_HANJA = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥'];

const STEM_ELEMENT = ['wood','wood','fire','fire','earth','earth','metal','metal','water','water'];
const BRANCH_ELEMENT = ['water','earth','wood','wood','earth','fire','fire','earth','metal','metal','earth','water'];
const STEM_YIN_YANG = ['양','음','양','음','양','음','양','음','양','음'];
const BRANCH_ZODIAC = ['쥐','소','호랑이','토끼','용','뱀','말','양','원숭이','닭','개','돼지'];
const BRANCH_ZODIAC_EMOJI = ['🐭','🐮','🐯','🐰','🐲','🐍','🐴','🐑','🐵','🐓','🐶','🐷'];

const ELEMENT_KR = { wood:'목(木)', fire:'화(火)', earth:'토(土)', metal:'금(金)', water:'수(水)' };
const ELEMENT_COLOR = { wood:'#4ade80', fire:'#f87171', earth:'#fbbf24', metal:'#e2e8f0', water:'#60a5fa' };

// 천간 성격 정보
const STEM_INFO = {
  0: { name:'갑목(甲木)', title:'거목의 기상', desc:'강직하고 진취적이며 리더십이 강합니다. 새로운 시작을 좋아하고 개척 정신이 뛰어납니다.', personality:'솔직하고 직선적인 성격으로 불의에 타협하지 않습니다. 큰 꿈을 품고 앞으로 나아가는 힘이 있지만, 융통성이 부족할 수 있습니다.', love:'헌신적이고 의리를 중시하는 사랑을 합니다. 한번 마음을 주면 깊게 사랑하지만 고집이 충돌하면 힘들 수 있습니다.', career:'CEO, 사업가, 법조인, 정치인, 군인 등 리더 역할에 적합합니다. 독립적인 사업이 잘 맞습니다.', health:'간담(肝膽) 계통에 주의가 필요합니다. 스트레스 관리와 충분한 휴식이 중요합니다.' },
  1: { name:'을목(乙木)', title:'유연한 풀의 생명력', desc:'유연하고 적응력이 뛰어나며 섬세한 감성을 지닙니다. 예술적 재능이 있습니다.', personality:'온화하고 사교적이지만 내면은 강인합니다. 눈치가 빠르고 상황 파악 능력이 탁월합니다. 때로는 우유부단해 보일 수 있습니다.', love:'로맨틱하고 상대를 배려하는 사랑을 합니다. 감성이 풍부해 연애 감정이 세밀하고 깊습니다.', career:'예술가, 디자이너, 의사, 상담사, 외교관 등에 적합합니다. 협력하는 역할에서 빛납니다.', health:'간담 계통과 신경계에 주의하세요. 감정 기복이 건강에 영향을 미칩니다.' },
  2: { name:'병화(丙火)', title:'태양의 빛', desc:'밝고 활동적이며 카리스마가 넘칩니다. 주변을 밝게 만드는 긍정 에너지가 있습니다.', personality:'사교적이고 열정적이며 낙천적입니다. 표현력이 강하고 남들의 주목받기를 좋아합니다. 성급한 면이 있을 수 있습니다.', love:'열정적이고 솔직한 사랑을 합니다. 표현을 아끼지 않으며 파트너를 행복하게 만들려 노력합니다.', career:'방송, 연예, 교육, 마케팅, 영업 등 사람을 만나는 직업에 탁월합니다.', health:'심장과 소장에 주의가 필요합니다. 과도한 흥분과 스트레스를 피하세요.' },
  3: { name:'정화(丁火)', title:'촛불의 따뜻함', desc:'세심하고 직관력이 뛰어납니다. 내면의 빛으로 주변을 따뜻하게 합니다.', personality:'지혜롭고 통찰력이 강합니다. 감수성이 풍부하고 예의 바르며 섬세합니다. 완벽주의적 성향이 있습니다.', love:'진지하고 깊은 사랑을 합니다. 파트너에게 헌신적이며 정서적 교감을 중요시합니다.', career:'상담사, 교사, 종교인, 예술가, 의료인 등 남을 돕는 직업이 잘 맞습니다.', health:'심장과 혈관 계통에 주의하세요. 심리적 안정이 중요합니다.' },
  4: { name:'무토(戊土)', title:'대지의 중심', desc:'중후하고 신뢰감이 있습니다. 든든한 버팀목 역할을 합니다.', personality:'책임감이 강하고 신중합니다. 보수적이고 안정을 추구하며 의리를 중요시합니다. 고집이 셀 수 있습니다.', love:'안정적이고 든든한 파트너가 됩니다. 감정 표현이 서툴 수 있지만 변함없는 사랑을 줍니다.', career:'부동산, 건설, 금융, 농업, 공무원 등 안정적인 직종에 어울립니다.', health:'비위(脾胃) 즉 소화기 계통에 주의가 필요합니다.' },
  5: { name:'기토(己土)', title:'비옥한 땅', desc:'포용력이 넓고 세심합니다. 내면에 다양한 재능을 품고 있습니다.', personality:'온화하고 사려깊으며 주변을 잘 돌봅니다. 실용적이고 현실적인 판단력이 있습니다. 걱정이 많을 수 있습니다.', love:'배려심이 깊고 현실적인 사랑을 합니다. 가정을 소중히 여깁니다.', career:'영양사, 사회복지사, 금융, 서비스업, 요식업 등에 적합합니다.', health:'소화기와 비장에 신경 쓰세요. 규칙적인 식습관이 중요합니다.' },
  6: { name:'경금(庚金)', title:'강철의 의지', desc:'강하고 결단력이 있습니다. 불의에 굴하지 않는 정의감이 있습니다.', personality:'의협심이 강하고 솔직합니다. 추진력이 있고 변화를 두려워하지 않습니다. 때로는 너무 직설적일 수 있습니다.', love:'솔직하고 직접적인 사랑을 합니다. 한번 결정하면 흔들리지 않는 믿음직한 파트너입니다.', career:'군인, 경찰, 외과의사, 운동선수, 금속 관련 업종에 적합합니다.', health:'폐와 대장 계통을 주의하세요. 호흡기 건강관리가 중요합니다.' },
  7: { name:'신금(辛金)', title:'보석의 빛남', desc:'세련되고 예민합니다. 완성도를 추구하며 아름다움에 민감합니다.', personality:'분석력이 뛰어나고 완벽주의적입니다. 예의 바르고 깔끔하며 심미안이 있습니다. 예민하고 스트레스에 취약할 수 있습니다.', love:'까다롭지만 진지하게 사랑합니다. 상대에게 높은 기준을 가지고 있습니다.', career:'보석 디자인, 의사, 법조인, 미용, 예술 분야에서 뛰어납니다.', health:'폐, 피부, 신경계에 주의하세요. 정신적 스트레스 관리가 필요합니다.' },
  8: { name:'임수(壬水)', title:'큰 바다의 기운', desc:'지혜롭고 포용력이 넓습니다. 무한한 가능성을 품고 있습니다.', personality:'총명하고 상상력이 풍부합니다. 유연하게 상황을 해쳐나가는 능력이 있습니다. 변덕스러울 수 있습니다.', love:'자유롭고 낭만적인 사랑을 합니다. 다양한 감정을 풍부하게 나눕니다.', career:'철학가, 작가, 연구원, 여행업, 무역업, IT 분야에 적합합니다.', health:'신장과 방광 계통에 주의하세요. 수분 섭취와 냉기 방어가 중요합니다.' },
  9: { name:'계수(癸水)', title:'이슬비의 정화', desc:'섬세하고 지혜롭습니다. 깊은 내면의 세계를 지닙니다.', personality:'직관력이 뛰어나고 감수성이 풍부합니다. 겸손하고 내성적이지만 깊은 통찰력을 가집니다.', love:'신중하게 사랑을 시작하지만 깊은 정서적 유대를 맺습니다. 감성적인 교감을 중시합니다.', career:'작가, 예술가, 상담사, 종교인, 연구원 등 내면을 탐구하는 분야에 적합합니다.', health:'신장, 방광, 생식기 계통을 주의하세요. 체온 유지와 냉증 예방이 중요합니다.' },
};

// 2026년 운세 (병오년 → 실제는 병오년 아님, 2026은 병오년)
// 2026 = 丙午 병오년
const ANNUAL_2026 = {
  wood: '2026 병오년(丙午年)은 목(木) 기운을 가진 당신에게 <strong>활발한 성장의 해</strong>입니다. 화(火)의 기운이 넘치는 해로 목이 화를 생하니 에너지가 외부로 발산됩니다. 새로운 도전과 확장이 기대되며, 인간관계가 넓어지는 시기입니다. 다만 너무 많은 일을 벌이지 않도록 집중력을 유지하세요.',
  fire: '2026 병오년(丙午年)은 화(火) 기운을 가진 당신에게 <strong>강렬한 에너지가 충만한 해</strong>입니다. 같은 화 기운이 겹쳐 열정이 배가됩니다. 자신감이 넘치고 표현력이 극대화되는 시기. 열정적인 도전이 결실을 맺을 수 있습니다. 다만 과열되지 않도록 냉정함을 유지하는 것이 중요합니다.',
  earth: '2026 병오년(丙午年)은 토(土) 기운의 당신에게 <strong>안정 속 성장의 해</strong>입니다. 화가 토를 생하니 든든한 지원을 받는 형국입니다. 재물운이 상승하고 신뢰가 쌓이는 해입니다. 부동산, 투자 등 장기적 안목의 결정이 좋은 결과를 낼 수 있습니다.',
  metal: '2026 병오년(丙午年)은 금(金) 기운의 당신에게 <strong>변화와 도전의 해</strong>입니다. 화극금(火剋金)의 기운으로 압박감을 느낄 수 있습니다. 단, 이 압박이 당신을 더욱 단단하게 만들어 줍니다. 건강관리에 특히 신경 쓰고, 무리한 계획보다는 내실을 다지는 해로 활용하세요.',
  water: '2026 병오년(丙午年)은 수(水) 기운의 당신에게 <strong>지혜가 빛나는 해</strong>입니다. 화수(火水)의 상극 구도에서 지혜와 냉철함이 더욱 강조됩니다. 감정적 충동보다는 분석적 판단이 중요한 해입니다. 인간관계에서 갈등을 주의하고, 내면의 성찰에 집중하면 빛나는 한 해가 될 것입니다.'
};

// 행운 데이터 (오행별)
const LUCKY = {
  wood: { color:'초록, 파랑', number:'3, 8', direction:'동쪽', season:'봄', gemstone:'에메랄드, 비취' },
  fire: { color:'빨강, 주황', number:'2, 7', direction:'남쪽', season:'여름', gemstone:'루비, 가넷' },
  earth: { color:'노랑, 갈색', number:'5, 0', direction:'중앙', season:'환절기', gemstone:'호박, 황옥' },
  metal: { color:'흰색, 금색', number:'4, 9', direction:'서쪽', season:'가을', gemstone:'다이아몬드, 백수정' },
  water: { color:'검정, 파랑', number:'1, 6', direction:'북쪽', season:'겨울', gemstone:'사파이어, 흑진주' }
};

// ===== 사주 계산 로직 =====

// 연주(年柱) 계산: 1984년 = 갑자(0,0)
function getYearPillar(year) {
  const stemIdx = (year - 4) % 10;
  const branchIdx = (year - 4) % 12;
  return {
    stem: ((stemIdx % 10) + 10) % 10,
    branch: ((branchIdx % 12) + 12) % 12
  };
}

// 월주(月柱) 계산
// 월간 = (연간 * 2 + 월) % 10
function getMonthPillar(yearStem, month) {
  const stemIdx = (yearStem * 2 + month) % 10;
  const branchIdx = (month + 1) % 12; // 인월(2)=3월, 묘월(3)=4월 ...
  return { stem: stemIdx, branch: branchIdx };
}

// 일주(日柱) 계산
// 갑자일: 1900-01-31 기준
function getDayPillar(year, month, day) {
  const base = new Date(1900, 0, 31); // 갑자일 (stem=0, branch=0)
  const target = new Date(year, month - 1, day);
  const diffDays = Math.round((target - base) / 86400000);
  const stemIdx = ((diffDays % 10) + 10) % 10;
  const branchIdx = ((diffDays % 12) + 12) % 12;
  return { stem: stemIdx, branch: branchIdx };
}

// 시주(時柱) 계산
function getHourPillar(dayStem, hourIdx) {
  if (hourIdx < 0) return null;
  const stemIdx = (dayStem * 2 + hourIdx) % 10;
  return { stem: stemIdx, branch: hourIdx };
}

// 오행 집계
function countElements(pillars) {
  const count = { wood:0, fire:0, earth:0, metal:0, water:0 };
  pillars.forEach(p => {
    if (!p) return;
    count[STEM_ELEMENT[p.stem]]++;
    count[BRANCH_ELEMENT[p.branch]]++;
  });
  return count;
}

// ===== UI 렌더링 =====

function renderPillar(label, pillar) {
  if (!pillar) {
    return `<div class="pillar">
      <div class="pillar-label">${label}</div>
      <div class="pillar-stem elem-metal" style="opacity:0.3">
        <span class="hanja">?</span><span class="hangul">모름</span>
      </div>
      <div class="pillar-branch elem-water" style="opacity:0.3">
        <span class="hanja">?</span><span class="hangul">모름</span>
      </div>
    </div>`;
  }
  const stemElem = STEM_ELEMENT[pillar.stem];
  const branchElem = BRANCH_ELEMENT[pillar.branch];
  return `<div class="pillar">
    <div class="pillar-label">${label}</div>
    <div class="pillar-stem elem-${stemElem}" title="${ELEMENT_KR[stemElem]}">
      <span class="hanja">${STEMS_HANJA[pillar.stem]}</span>
      <span class="hangul">${STEMS[pillar.stem]} ${STEM_YIN_YANG[pillar.stem]}</span>
    </div>
    <div class="pillar-branch elem-${branchElem}" title="${BRANCH_ZODIAC[pillar.branch]}">
      <span class="hanja">${BRANCHES_HANJA[pillar.branch]}</span>
      <span class="hangul">${BRANCHES[pillar.branch]} ${BRANCH_ZODIAC_EMOJI[pillar.branch]}</span>
    </div>
  </div>`;
}

function renderElements(count) {
  const total = Object.values(count).reduce((a,b) => a+b, 0);
  const rows = Object.entries(count).map(([elem, val]) => {
    const pct = total > 0 ? Math.round(val / total * 100) : 0;
    return `<div class="element-row">
      <span class="element-name" style="color:${ELEMENT_COLOR[elem]}">${ELEMENT_KR[elem]}</span>
      <div class="element-track">
        <div class="element-fill fill-${elem}" style="width:${pct}%"></div>
      </div>
      <span class="element-count">${val}</span>
    </div>`;
  }).join('');
  document.getElementById('elementsBar').innerHTML = rows;
}

function renderDayMaster(dayStem) {
  const info = STEM_INFO[dayStem];
  const elem = STEM_ELEMENT[dayStem];
  const color = ELEMENT_COLOR[elem];
  document.getElementById('daymasterContainer').querySelector('h3').textContent =
    `일간 (日干) — 나의 본질 : ${info.name}`;
  document.getElementById('daymasterInfo').innerHTML = `
    <div class="daymaster-box">
      <div class="daymaster-char elem-${elem}" style="background:rgba(${hexToRgb(color)},0.15); border:1px solid rgba(${hexToRgb(color)},0.4); color:${color}">
        ${STEMS_HANJA[dayStem]}
      </div>
      <div class="daymaster-desc">
        <div class="daymaster-title">${info.title}</div>
        <div class="daymaster-detail">${info.desc}</div>
      </div>
    </div>`;
}

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `${r},${g},${b}`;
}

function renderFortune(dayStem) {
  const info = STEM_INFO[dayStem];
  document.getElementById('personalityText').textContent = info.personality;
  document.getElementById('loveText').textContent = info.love;
  document.getElementById('careerText').textContent = info.career;
  document.getElementById('healthText').textContent = info.health;
}

function renderLucky(dominantElem) {
  const lucky = LUCKY[dominantElem];
  const items = [
    { label:'행운의 색', value: lucky.color },
    { label:'행운의 숫자', value: lucky.number },
    { label:'행운의 방향', value: lucky.direction },
    { label:'행운의 계절', value: lucky.season },
    { label:'행운의 보석', value: lucky.gemstone },
  ];
  document.getElementById('luckyGrid').innerHTML = items.map(i => `
    <div class="lucky-item">
      <span class="lucky-item-label">${i.label}</span>
      <span class="lucky-item-value">${i.value}</span>
    </div>`).join('');
}

function renderAnnual(dominantElem) {
  document.getElementById('annualFortune').innerHTML = ANNUAL_2026[dominantElem];
}

// ===== 지배 오행 계산 =====
function getDominant(count) {
  return Object.entries(count).sort((a,b) => b[1]-a[1])[0][0];
}

// ===== 이벤트 핸들러 =====

// 일 선택지 동적 생성
function updateDays() {
  const year = parseInt(document.getElementById('birthYear').value) || 2000;
  const month = parseInt(document.getElementById('birthMonth').value) || 1;
  const maxDay = new Date(year, month, 0).getDate();
  const daySelect = document.getElementById('birthDay');
  const currentVal = daySelect.value;
  daySelect.innerHTML = '<option value="">일 선택</option>';
  for (let d = 1; d <= maxDay; d++) {
    const opt = document.createElement('option');
    opt.value = d; opt.textContent = `${d}일`;
    if (d == currentVal) opt.selected = true;
    daySelect.appendChild(opt);
  }
}

document.getElementById('birthMonth').addEventListener('change', updateDays);
document.getElementById('birthYear').addEventListener('change', updateDays);
updateDays();

document.getElementById('sajuForm').addEventListener('submit', function(e) {
  e.preventDefault();
  const year = parseInt(document.getElementById('birthYear').value);
  const month = parseInt(document.getElementById('birthMonth').value);
  const day = parseInt(document.getElementById('birthDay').value);
  const hourIdx = parseInt(document.getElementById('birthHour').value);

  if (!year || !month || !day) return;

  // 사주 계산
  const yearPillar = getYearPillar(year);
  const monthPillar = getMonthPillar(yearPillar.stem, month);
  const dayPillar = getDayPillar(year, month, day);
  const hourPillar = getHourPillar(dayPillar.stem, hourIdx);

  const pillars = [yearPillar, monthPillar, dayPillar, hourPillar];

  // 오행 집계 (시주 모를 때 제외)
  const activePillars = hourPillar ? pillars : pillars.slice(0,3);
  const elementCount = countElements(activePillars);
  const dominant = getDominant(elementCount);

  // 렌더링
  document.getElementById('pillars').innerHTML =
    renderPillar('년주(年柱)', yearPillar) +
    renderPillar('월주(月柱)', monthPillar) +
    renderPillar('일주(日柱)', dayPillar) +
    renderPillar('시주(時柱)', hourPillar);

  renderElements(elementCount);
  renderDayMaster(dayPillar.stem);
  renderFortune(dayPillar.stem);
  renderLucky(dominant);
  renderAnnual(dominant);

  // 섹션 전환
  document.getElementById('inputSection').classList.add('hidden');
  document.getElementById('resultSection').classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

document.getElementById('resetBtn').addEventListener('click', function() {
  document.getElementById('resultSection').classList.add('hidden');
  document.getElementById('inputSection').classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
});
