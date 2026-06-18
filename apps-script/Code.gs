/**
 * 프로젝트 스케줄 보드 ↔ 구글 시트 동기화용 Apps Script
 *
 * 동작:
 *   - GET  : '스케줄보드' 시트의 모든 행을 JSON({tasks:[...]})으로 반환
 *   - POST : 받은 tasks 배열로 '스케줄보드' 시트를 통째로 다시 작성
 *
 * 설치 방법은 같은 폴더의 README.md 참고.
 */

var SHEET_NAME = '스케줄보드';
var HEADERS = ['id','parentId','project','task','category','assignee',
               'priority','start','end','status','doc','progress','issue','order'];

function getSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
    sh.appendRow(HEADERS);
    sh.setFrozenRows(1);
  }
  return sh;
}

function doGet() {
  var sh = getSheet_();
  var values = sh.getDataRange().getValues();
  var tasks = [];
  if (values.length > 1) {
    var head = values[0];
    for (var i = 1; i < values.length; i++) {
      var row = values[i];
      if (row.join('') === '') continue;             // 빈 행 건너뜀
      var o = {};
      for (var j = 0; j < head.length; j++) {
        var key = head[j];
        var val = row[j];
        if (key === 'order') val = Number(val) || 0;
        else if (key === 'parentId') val = val === '' ? null : String(val);
        else if (key === 'start' || key === 'end') val = formatDate_(val);
        else if (val instanceof Date) val = formatDate_(val);   // 어떤 날짜 셀도 YYYY-MM-DD로
        else val = val === '' ? '' : String(val);
        o[key] = val;
      }
      tasks.push(o);
    }
  }
  return json_({ tasks: tasks });
}

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var tasks = body.tasks || [];
    var sh = getSheet_();
    sh.clear();
    var rows = [HEADERS];
    for (var i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      var row = [];
      for (var j = 0; j < HEADERS.length; j++) {
        var v = t[HEADERS[j]];
        row.push(v == null ? '' : v);
      }
      rows.push(row);
    }
    sh.getRange(1, 1, rows.length, HEADERS.length).setValues(rows);
    sh.setFrozenRows(1);
    return json_({ ok: true, count: tasks.length });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
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
