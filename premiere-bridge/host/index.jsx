/*
 * Claude Premiere Bridge - ExtendScript 헬퍼 라이브러리
 *
 * 패널이 시작될 때 $.evalFile 로 이 파일을 불러옵니다.
 * 여기서 정의한 함수는 이후 모든 명령(.jsx)에서 그대로 호출할 수 있습니다.
 *
 * 자주 쓰는 동작을 함수로 만들어두면 Claude가 짧은 명령으로 호출할 수 있어요.
 * (직접 app.* API 를 명령 안에 다 써도 됩니다.)
 */

// ---- 정보 조회 ----------------------------------------------------------

/** 프리미어 버전 문자열 반환 (연결 확인용) */
function ppVersion() {
  return "Premiere " + app.version;
}

/** 현재 활성 시퀀스 이름 (없으면 표시) */
function ppActiveSequence() {
  var seq = app.project.activeSequence;
  return seq ? seq.name : "(활성 시퀀스 없음)";
}

/** 프로젝트의 모든 항목 이름을 줄바꿈으로 반환 */
function ppListProjectItems() {
  var out = [];
  function walk(item) {
    var children = item.children;
    if (!children) return;
    for (var i = 0; i < children.numItems; i++) {
      var it = children[i];
      out.push(it.name);
      if (it.type === ProjectItemType.BIN) walk(it);
    }
  }
  walk(app.project.rootItem);
  return out.join("\n");
}

/** 활성 시퀀스의 트랙/클립 개요를 JSON 문자열로 반환 */
function ppSequenceInfo() {
  var seq = app.project.activeSequence;
  if (!seq) return "(활성 시퀀스 없음)";
  function clips(track) {
    var arr = [];
    for (var i = 0; i < track.clips.numItems; i++) {
      var c = track.clips[i];
      arr.push({
        name: c.name,
        start: c.start.seconds,
        end: c.end.seconds,
      });
    }
    return arr;
  }
  var info = { name: seq.name, video: [], audio: [] };
  for (var v = 0; v < seq.videoTracks.numTracks; v++) {
    info.video.push(clips(seq.videoTracks[v]));
  }
  for (var a = 0; a < seq.audioTracks.numTracks; a++) {
    info.audio.push(clips(seq.audioTracks[a]));
  }
  return JSON.stringify(info);
}

// ---- 편집 동작 ----------------------------------------------------------

/** 재생헤드를 지정 초로 이동 */
function ppSeek(seconds) {
  var seq = app.project.activeSequence;
  if (!seq) return "(활성 시퀀스 없음)";
  var t = new Time();
  t.seconds = seconds;
  seq.setPlayerPosition(t.ticks);
  return "재생헤드 이동: " + seconds + "s";
}

/**
 * 프로젝트 항목(이름으로 검색)을 활성 시퀀스의 비디오 트랙에 삽입
 * @param {string} itemName  프로젝트 패널의 클립 이름
 * @param {number} atSeconds 삽입 시작 시각(초)
 * @param {number} trackIndex 비디오 트랙 인덱스(0부터)
 */
function ppInsertClip(itemName, atSeconds, trackIndex) {
  trackIndex = trackIndex || 0;
  var seq = app.project.activeSequence;
  if (!seq) return "(활성 시퀀스 없음)";
  var item = ppFindItem(itemName);
  if (!item) return "항목 없음: " + itemName;
  var t = new Time();
  t.seconds = atSeconds;
  seq.videoTracks[trackIndex].insertClip(item, t);
  return "삽입 완료: " + itemName + " @ " + atSeconds + "s (V" + (trackIndex + 1) + ")";
}

/** 이름으로 프로젝트 항목 찾기 (재귀) */
function ppFindItem(name) {
  var found = null;
  function walk(item) {
    var children = item.children;
    if (!children) return;
    for (var i = 0; i < children.numItems; i++) {
      var it = children[i];
      if (it.name === name) {
        found = it;
        return;
      }
      if (it.type === ProjectItemType.BIN) walk(it);
    }
  }
  walk(app.project.rootItem);
  return found;
}

/** 프로젝트 저장 */
function ppSave() {
  app.project.save();
  return "저장됨: " + app.project.name;
}

// 로드 확인용 반환값
"Claude Premiere Bridge host helpers loaded";
