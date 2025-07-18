/**
 * 数式データ管理用のGoogle Apps Script
 * スプレッドシート構造: id, title, title_EN, formula, formula_type, tags, image_url, timestamp
 */

// スプレッドシートIDを設定（実際のIDに変更してください）
const SPREADSHEET_ID = 'your_spreadsheet_id_here';
const SHEET_NAME = 'formulas'; // シート名

/**
 * GETリクエスト処理
 */
function doGet(e) {
  try {
    const params = e.parameter;
    
    // パラメータに応じて処理を分岐
    if (params.id) {
      // 特定IDの数式データを取得
      return getFormulaById(params.id);
    } else if (params.type) {
      // 特定タイプの数式データ一覧を取得
      return getFormulasByType(params.type);
    } else if (params.search) {
      // 検索
      return searchFormulas(params.search);
    } else if (params.random === 'true') {
      // ランダム取得
      return getRandomFormula();
    } else {
      // 全データ取得
      return getAllFormulas();
    }
  } catch (error) {
    console.error('doGet Error:', error);
    return ContentService
      .createTextOutput(JSON.stringify({error: error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * POSTリクエスト処理（新規追加・更新）
 */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    
    if (!data.id || !data.title || !data.formula) {
      throw new Error('必須パラメータが不足しています (id, title, formula)');
    }
    
    return addOrUpdateFormula(data);
  } catch (error) {
    console.error('doPost Error:', error);
    return ContentService
      .createTextOutput(JSON.stringify({error: error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * DELETEリクエスト処理（削除）
 */
function doDelete(e) {
  try {
    const params = e.parameter;
    
    if (!params.id) {
      throw new Error('IDパラメータが必要です');
    }
    
    return deleteFormula(params.id);
  } catch (error) {
    console.error('doDelete Error:', error);
    return ContentService
      .createTextOutput(JSON.stringify({error: error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * 特定IDの数式データを取得
 */
function getFormulaById(id) {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  
  // ヘッダー行をスキップして検索
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (row[0] && row[0].toString() === id.toString()) {
      const formula = rowToFormula(headers, row);
      return ContentService
        .createTextOutput(JSON.stringify(formula))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }
  
  return ContentService
    .createTextOutput(JSON.stringify(null))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 全数式データを取得
 */
function getAllFormulas() {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const formulas = [];
  
  // ヘッダー行をスキップして処理
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (row[0]) { // IDが存在する行のみ
      formulas.push(rowToFormula(headers, row));
    }
  }
  
  return ContentService
    .createTextOutput(JSON.stringify(formulas))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 特定タイプの数式データ一覧を取得
 */
function getFormulasByType(type) {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const formulas = [];
  
  const typeIndex = headers.indexOf('formula_type');
  if (typeIndex === -1) {
    throw new Error('formula_type列が見つかりません');
  }
  
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (row[0] && row[typeIndex] && row[typeIndex].toString() === type) {
      formulas.push(rowToFormula(headers, row));
    }
  }
  
  return ContentService
    .createTextOutput(JSON.stringify(formulas))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 検索機能（タイトルやタグで検索）
 */
function searchFormulas(query) {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const formulas = [];
  
  const titleIndex = headers.indexOf('title');
  const titleENIndex = headers.indexOf('title_EN');
  const tagsIndex = headers.indexOf('tags');
  
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (!row[0]) continue; // IDが空の行はスキップ
    
    const searchText = query.toLowerCase();
    let matches = false;
    
    // タイトル（日本語）で検索
    if (titleIndex !== -1 && row[titleIndex] && 
        row[titleIndex].toString().toLowerCase().includes(searchText)) {
      matches = true;
    }
    
    // タイトル（英語）で検索
    if (titleENIndex !== -1 && row[titleENIndex] && 
        row[titleENIndex].toString().toLowerCase().includes(searchText)) {
      matches = true;
    }
    
    // タグで検索
    if (tagsIndex !== -1 && row[tagsIndex] && 
        row[tagsIndex].toString().toLowerCase().includes(searchText)) {
      matches = true;
    }
    
    if (matches) {
      formulas.push(rowToFormula(headers, row));
    }
  }
  
  return ContentService
    .createTextOutput(JSON.stringify(formulas))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * ランダムな数式データを1つ取得
 */
function getRandomFormula() {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const validRows = [];
  
  // 有効な行（IDが存在する行）を収集
  for (let i = 1; i < data.length; i++) {
    if (data[i][0]) {
      validRows.push(data[i]);
    }
  }
  
  if (validRows.length === 0) {
    return ContentService
      .createTextOutput(JSON.stringify(null))
      .setMimeType(ContentService.MimeType.JSON);
  }
  
  // ランダムに選択
  const randomIndex = Math.floor(Math.random() * validRows.length);
  const randomRow = validRows[randomIndex];
  const formula = rowToFormula(headers, randomRow);
  
  return ContentService
    .createTextOutput(JSON.stringify(formula))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 数式データを追加または更新
 */
function addOrUpdateFormula(data) {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
  const sheetData = sheet.getDataRange().getValues();
  const headers = sheetData[0];
  
  // 既存のIDを検索
  let existingRowIndex = -1;
  for (let i = 1; i < sheetData.length; i++) {
    if (sheetData[i][0] && sheetData[i][0].toString() === data.id.toString()) {
      existingRowIndex = i;
      break;
    }
  }
  
  // 新しい行データを作成
  const timestamp = new Date().toISOString();
  const newRow = [
    data.id,
    data.title || '',
    data.title_EN || '',
    data.formula || '',
    data.formula_type || '',
    data.tags || '',
    data.image_url || '',
    timestamp
  ];
  
  if (existingRowIndex !== -1) {
    // 既存データを更新
    sheet.getRange(existingRowIndex + 1, 1, 1, headers.length).setValues([newRow]);
  } else {
    // 新規データを追加
    sheet.appendRow(newRow);
  }
  
  return ContentService
    .createTextOutput(JSON.stringify({success: true, id: data.id}))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 数式データを削除
 */
function deleteFormula(id) {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  
  // 対象行を検索
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] && data[i][0].toString() === id.toString()) {
      sheet.deleteRow(i + 1);
      return ContentService
        .createTextOutput(JSON.stringify({success: true, deleted_id: id}))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }
  
  return ContentService
    .createTextOutput(JSON.stringify({error: '指定されたIDが見つかりません'}))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 行データを数式オブジェクトに変換
 */
function rowToFormula(headers, row) {
  const formula = {};
  
  for (let j = 0; j < headers.length && j < row.length; j++) {
    const header = headers[j];
    const value = row[j];
    
    if (header && value !== undefined && value !== null && value !== '') {
      formula[header] = value;
    }
  }
  
  return formula;
}
