/**
 * 프로젝트 스케줄 보드 ↔ 구글 시트 동기화용 Apps Script
 *
 * 동작:
 *   - GET  : '스케줄보드' 시트의 모든 행 + 메타(_meta)를 JSON({tasks, meta})으로 반환
 *   - POST : 받은 tasks 로 '스케줄보드' 시트를 다시 작성하고, meta(_meta)를 저장
 *
 * '스케줄보드' 탭의 컬럼(고정 순서, 1행은 한글 라벨):
 *   id / 상위ID / 프로젝트 / 진행업무 / 구분 / 담당자 / 우선순위 /
 *   시작일 / 종료일(예상) / 상태 / 결과물/진행문서 / 진행사항 / 이슈/확인사항 / 정렬
 *   ※ '결과물/진행문서'(11번째 열)가 원본 시트 J열과 동일한 의미입니다.
 *
 * 설치/배포 방법은 같은 폴더의 README.md 참고.
 */

var SHEET_NAME = '스케줄보드';
var META_NAME  = '_meta';
// 앱 내부 필드(고정 순서) — 행은 이 순서로 읽고 씁니다(헤더 텍스트가 아닌 '열 위치' 기준).
var FIELDS = ['id','parentId','project','task','category','assignee','priority',
              'start','end','status','doc','progress','issue','order'];
// 사람이 보기 위한 한글 헤더(1행에 표시)
var LABELS = ['id','상위ID','프로젝트','진행업무','구분','담당자','우선순위',
              '시작일','종료일(예상)','상태','결과물/진행문서','진행사항','이슈/확인사항','정렬'];

function getSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
    sh.appendRow(LABELS);
    sh.setFrozenRows(1);
  }
  return sh;
}

function doGet() {
  var sh = getSheet_();
  var values = sh.getDataRange().getValues();
  var tasks = [];
  for (var i = 1; i < values.length; i++) {       // 1행(헤더) 제외, 열 위치 기준 매핑
    var row = values[i];
    if (row.join('') === '') continue;
    var o = {};
    for (var j = 0; j < FIELDS.length; j++) {
      var key = FIELDS[j];
      var val = row[j];
      if (key === 'order') val = Number(val) || 0;
      else if (key === 'parentId') val = (val === '' || val == null) ? null : String(val);
      else if (key === 'start' || key === 'end') val = formatDate_(val);
      else if (val instanceof Date) val = formatDate_(val);
      else val = (val === '' || val == null) ? '' : String(val);
      o[key] = val;
    }
    tasks.push(o);
  }
  return json_({ tasks: tasks, meta: readMeta_() });
}

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var tasks = body.tasks || [];
    var sh = getSheet_();
    sh.clear();
    var rows = [LABELS];
    for (var i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      var row = [];
      for (var j = 0; j < FIELDS.length; j++) {
        var v = t[FIELDS[j]];
        row.push(v == null ? '' : v);
      }
      rows.push(row);
    }
    sh.getRange(1, 1, rows.length, FIELDS.length).setValues(rows);
    sh.setFrozenRows(1);
    if (body.meta) writeMeta_(body.meta);   // 프로젝트 링크/제목 등
    return json_({ ok: true, count: tasks.length });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

/* ---- 메타(_meta) 탭: 프로젝트 링크/보드 제목 등 작업 외 공유 데이터 ---- */
function readMeta_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var m = ss.getSheetByName(META_NAME);
  if (!m) return {};
  var v = m.getRange('A1').getValue();
  if (!v) return {};
  try { return JSON.parse(v); } catch (e) { return {}; }
}
function writeMeta_(meta) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var m = ss.getSheetByName(META_NAME);
  if (!m) { m = ss.insertSheet(META_NAME); m.getRange('A1').setNote('스케줄 보드 공유설정(JSON) - 자동 생성'); }
  m.getRange('A1').setValue(JSON.stringify(meta || {}));
}

function formatDate_(v) {
  if (v instanceof Date) {
    var y = v.getFullYear();
    var m = ('0' + (v.getMonth() + 1)).slice(-2);
    var d = ('0' + v.getDate()).slice(-2);
    return y + '-' + m + '-' + d;
  }
  return v === '' ? '' : String(v);
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
