/**
 * Google Sheets API v4 integration.
 *
 * Setup:
 * 1. Create a Google Cloud project, enable Sheets API.
 * 2. Create a Service Account, download JSON key.
 * 3. Share your spreadsheet with the service account email.
 * 4. Set SPREADSHEET_ID and SERVICE_ACCOUNT_KEY in config below.
 *
 * For web/dev you can use API key instead of service account
 * (read-only). For write access you need OAuth or service account.
 */

import axios from 'axios';

// ─── CONFIGURE THESE ──────────────────────────────────────────────────────────
export const SPREADSHEET_ID = process.env.EXPO_PUBLIC_SPREADSHEET_ID ?? '';
export const API_KEY = process.env.EXPO_PUBLIC_SHEETS_API_KEY ?? '';
// ──────────────────────────────────────────────────────────────────────────────

const BASE = 'https://sheets.googleapis.com/v4/spreadsheets';

export type SheetName = 'ДАА' | 'ЕОГ' | 'Ратчин' | 'ЧСА';

export interface Row {
  rowNumber: number;
  shk: string;
  tovar: string;
  artVB: string;
  razmer: string;
  kolichestvo: number;
  nomerKoroba: number;
  data: string;
}

/** Map sheet columns to Row fields (A–H). */
function parseRow(values: string[], rowNumber: number): Row {
  return {
    rowNumber,
    shk: values[0] ?? '',
    tovar: values[1] ?? '',
    artVB: values[2] ?? '',
    razmer: values[3] ?? '',
    kolichestvo: Number(values[4]) || 0,
    nomerKoroba: Number(values[5]) || 0,
    data: values[6] ?? '',
  };
}

/** Fetch all rows from a sheet (read-only with API key). */
export async function fetchRows(sheet: SheetName): Promise<Row[]> {
  const range = encodeURIComponent(`${sheet}!A2:H`);
  const url = `${BASE}/${SPREADSHEET_ID}/values/${range}?key=${API_KEY}`;
  const { data } = await axios.get(url);
  const values: string[][] = data.values ?? [];
  return values.map((row, i) => parseRow(row, i + 2));
}

/**
 * Append a new row to a sheet.
 * Requires OAuth token (passed from the auth flow).
 */
export async function appendRow(
  sheet: SheetName,
  row: Omit<Row, 'rowNumber' | 'tovar' | 'artVB' | 'razmer'>,
  accessToken: string,
): Promise<void> {
  const range = encodeURIComponent(`${sheet}!A:H`);
  const url = `${BASE}/${SPREADSHEET_ID}/values/${range}:append?valueInputOption=USER_ENTERED`;
  await axios.post(
    url,
    {
      values: [
        ['', row.shk, '', '', '', row.kolichestvo, row.nomerKoroba, row.data],
      ],
    },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
}

/**
 * Delete a row by clearing it (Sheets API doesn't delete rows via REST easily).
 * We overwrite with empty values and then the sheet will have a blank row.
 * For a proper delete use batchUpdate with DeleteDimensionRequest.
 */
export async function deleteRow(
  sheet: SheetName,
  rowNumber: number,
  sheetId: number,
  accessToken: string,
): Promise<void> {
  const url = `${BASE}/${SPREADSHEET_ID}:batchUpdate`;
  await axios.post(
    url,
    {
      requests: [
        {
          deleteDimension: {
            range: {
              sheetId,
              dimension: 'ROWS',
              startIndex: rowNumber - 1,
              endIndex: rowNumber,
            },
          },
        },
      ],
    },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
}

/** Update a single row's editable fields. */
export async function updateRow(
  sheet: SheetName,
  row: Pick<Row, 'rowNumber' | 'shk' | 'kolichestvo' | 'nomerKoroba' | 'data'>,
  accessToken: string,
): Promise<void> {
  const range = encodeURIComponent(`${sheet}!B${row.rowNumber}:H${row.rowNumber}`);
  const url = `${BASE}/${SPREADSHEET_ID}/values/${range}?valueInputOption=USER_ENTERED`;
  await axios.put(
    url,
    {
      values: [[row.shk, '', '', '', row.kolichestvo, row.nomerKoroba, row.data]],
    },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
}
