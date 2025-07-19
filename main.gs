function doGet(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Messages");
  var key = e.parameter.key;
  if (!key) {
    // 全件取得
    var data = sheet.getDataRange().getValues();
    var result = [];
    for (var i = 1; i < data.length; i++) {
      result.push(rowToMessage(data[i]));
    }
    return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
  } else {
    // 1件取得
    var data = sheet.getDataRange().getValues();
    for (var i = 1; i < data.length; i++) {
      if (data[i][0] == key) {
        return ContentService.createTextOutput(JSON.stringify(rowToMessage(data[i]))).setMimeType(ContentService.MimeType.JSON);
      }
    }
    return ContentService.createTextOutput(JSON.stringify({error: "not found"})).setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Messages");
  var params = JSON.parse(e.postData.contents);
  var key = params.key;
  if (!key) {
    return ContentService.createTextOutput(JSON.stringify({error: "key required"})).setMimeType(ContentService.MimeType.JSON);
  }
  // 既存行の検索
  var data = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (data[i][0] == key) {
      // 更新
      sheet.getRange(i+1, 2, 1, 4).setValues([[
        params.content || "",
        params.embed_title || "",
        params.embed_description || "",
        params.embed_color || ""
      ]]);
      return ContentService.createTextOutput(JSON.stringify({result: "updated"})).setMimeType(ContentService.MimeType.JSON);
    }
  }
  // 新規追加
  sheet.appendRow([
    key,
    params.content || "",
    params.embed_title || "",
    params.embed_description || "",
    params.embed_color || ""
  ]);
  return ContentService.createTextOutput(JSON.stringify({result: "added"})).setMimeType(ContentService.MimeType.JSON);
}

function doDelete(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Messages");
  var key = e.parameter.key;
  if (!key) {
    return ContentService.createTextOutput(JSON.stringify({error: "key required"})).setMimeType(ContentService.MimeType.JSON);
  }
  var data = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (data[i][0] == key) {
      sheet.deleteRow(i+1);
      return ContentService.createTextOutput(JSON.stringify({result: "deleted"})).setMimeType(ContentService.MimeType.JSON);
    }
  }
  return ContentService.createTextOutput(JSON.stringify({error: "not found"})).setMimeType(ContentService.MimeType.JSON);
}

function rowToMessage(row) {
  return {
    key: row[0],
    content: row[1],
    embed: {
      title: row[2],
      description: row[3],
      color: row[4]
    }
  };
}