/*
 * Claude Premiere Bridge - 패널 로직
 *
 * 동작:
 *  1) ~/ClaudePremiereBridge/commands/ 폴더를 1초마다 감시
 *  2) 새 *.jsx 파일이 보이면 그 내용을 프리미어 ExtendScript 엔진에서 실행
 *  3) 실행 결과를 ~/ClaudePremiereBridge/results/<같은이름>.json 으로 기록
 *  4) 처리한 명령 파일은 *.jsx.done 으로 이름 변경(중복 실행 방지)
 *
 * Node.js(--enable-nodejs --mixed-context)가 켜져 있어야 require가 동작합니다.
 */

(function () {
  "use strict";

  var fs = require("fs");
  var path = require("path");
  var os = require("os");

  var BRIDGE_DIR = path.join(os.homedir(), "ClaudePremiereBridge");
  var CMD_DIR = path.join(BRIDGE_DIR, "commands");
  var RESULT_DIR = path.join(BRIDGE_DIR, "results");

  var running = true;
  var processing = false;

  // ---- UI 헬퍼 ----------------------------------------------------------
  function log(msg, cls) {
    var el = document.getElementById("log");
    var line = document.createElement("div");
    if (cls) line.className = cls;
    line.textContent = "[" + new Date().toLocaleTimeString() + "] " + msg;
    el.appendChild(line);
    el.scrollTop = el.scrollHeight;
  }

  function setStatus(on, text) {
    var s = document.getElementById("status");
    s.className = "status " + (on ? "on" : "off");
    s.textContent = text;
  }

  // ---- ExtendScript 실행 ------------------------------------------------
  function evalES(script) {
    return new Promise(function (resolve) {
      // CSInterface.js 없이 CEP 내부 브리지를 직접 사용
      window.__adobe_cep__.evalScript(script, function (res) {
        resolve(res);
      });
    });
  }

  function ensureDirs() {
    [BRIDGE_DIR, CMD_DIR, RESULT_DIR].forEach(function (d) {
      if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
    });
  }

  // 패널 시작 시 host/index.jsx 의 헬퍼 함수들을 ExtendScript 전역에 로드
  function loadHostHelpers() {
    var hostPath = path
      .join(__dirname, "..", "..", "host", "index.jsx")
      .replace(/\\/g, "/");
    return evalES('$.evalFile("' + hostPath + '")').then(function (r) {
      log("host 헬퍼 로드: " + hostPath, "ok");
    });
  }

  // ---- 명령 처리 --------------------------------------------------------
  function processFile(file) {
    var full = path.join(CMD_DIR, file);
    var base = file.replace(/\.jsx$/i, "");
    var script;
    try {
      script = fs.readFileSync(full, "utf8");
    } catch (e) {
      return Promise.resolve();
    }
    log("▶ 실행: " + file);

    return evalES(script)
      .then(function (result) {
        writeResult(base, file, result, true);
        log("✔ 완료: " + file + " → " + truncate(result), "ok");
      })
      .catch(function (e) {
        writeResult(base, file, String(e), false);
        log("✖ 오류: " + file + " → " + e, "err");
      })
      .then(function () {
        try {
          fs.renameSync(full, full + ".done");
        } catch (e) {}
      });
  }

  function writeResult(base, file, result, ok) {
    var out = path.join(RESULT_DIR, base + ".json");
    var payload = {
      command: file,
      ok: ok,
      result: result,
      time: new Date().toISOString(),
    };
    try {
      fs.writeFileSync(out, JSON.stringify(payload, null, 2));
    } catch (e) {
      log("결과 기록 실패: " + e, "err");
    }
  }

  function truncate(s) {
    s = String(s == null ? "" : s);
    return s.length > 120 ? s.slice(0, 120) + "…" : s;
  }

  // ---- 감시 루프 (순차 처리) --------------------------------------------
  function scan() {
    if (!running || processing) return;
    var files;
    try {
      files = fs.readdirSync(CMD_DIR).filter(function (f) {
        return /\.jsx$/i.test(f);
      });
    } catch (e) {
      return;
    }
    if (files.length === 0) return;
    files.sort(); // 파일명(타임스탬프) 순서대로 실행
    processing = true;
    // 한 번에 하나씩 순차 실행
    var chain = Promise.resolve();
    files.forEach(function (f) {
      chain = chain.then(function () {
        return processFile(f);
      });
    });
    chain.then(function () {
      processing = false;
    });
  }

  // ---- 버튼 -------------------------------------------------------------
  function wireButtons() {
    document.getElementById("toggleBtn").addEventListener("click", function () {
      running = !running;
      this.textContent = running ? "일시정지" : "재개";
      setStatus(
        running,
        running ? "감시 중 (실행 대기)" : "일시정지됨"
      );
      log(running ? "감시 재개" : "감시 일시정지");
    });
    document.getElementById("clearBtn").addEventListener("click", function () {
      document.getElementById("log").innerHTML = "";
    });
    document.getElementById("testBtn").addEventListener("click", function () {
      evalES('(function(){ return "Premiere " + app.version + " 연결 OK"; })()').then(
        function (r) {
          log("연결 테스트: " + r, "ok");
        }
      );
    });
  }

  // ---- 시작 -------------------------------------------------------------
  function start() {
    document.getElementById("watchPath").textContent = "감시 폴더: " + CMD_DIR;
    wireButtons();
    try {
      ensureDirs();
    } catch (e) {
      setStatus(false, "폴더 생성 실패");
      log("폴더 생성 실패: " + e, "err");
      return;
    }
    loadHostHelpers()
      .then(function () {
        setStatus(true, "감시 중 (실행 대기)");
        log("Bridge 시작됨. 1초 간격으로 감시합니다.", "ok");
        setInterval(scan, 1000);
      })
      .catch(function (e) {
        setStatus(true, "감시 중 (host 로드 실패)");
        log("host 로드 실패하지만 감시는 계속: " + e, "err");
        setInterval(scan, 1000);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
