const API_URL = 'https://pet-app-sheet.onrender.com';

export interface Row {
  id: number;
  shk: string;
  kolichestvo: string;
  nomerKoroba: string;
  data: string;
}

function nowDatetime(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export async function fetchSheets(): Promise<string[]> {
  const r = await fetch(`${API_URL}/api/admin/sheets`);
  if (!r.ok) throw new Error('Ошибка загрузки листов');
  const data = await r.json();
  return data.active as string[];
}

export async function fetchRows(sheet: string): Promise<Row[]> {
  const r = await fetch(`${API_URL}/api/rows/${encodeURIComponent(sheet)}`);
  if (!r.ok) throw new Error('Ошибка загрузки строк');
  return r.json();
}

export async function addRow(sheet: string, row: Omit<Row, 'id'>): Promise<void> {
  const r = await fetch(`${API_URL}/api/rows/${encodeURIComponent(sheet)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...row, data: row.data || nowDatetime() }),
  });
  if (!r.ok) throw new Error('Ошибка добавления');
}

export async function updateRow(sheet: string, id: number, row: Omit<Row, 'id'>): Promise<void> {
  const r = await fetch(`${API_URL}/api/rows/${encodeURIComponent(sheet)}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(row),
  });
  if (!r.ok) throw new Error('Ошибка обновления');
}

export async function deleteRow(sheet: string, id: number): Promise<void> {
  const r = await fetch(`${API_URL}/api/rows/${encodeURIComponent(sheet)}/${id}`, {
    method: 'DELETE',
  });
  if (!r.ok) throw new Error('Ошибка удаления');
}
