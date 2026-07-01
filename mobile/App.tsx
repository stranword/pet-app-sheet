import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Alert, FlatList, Keyboard, KeyboardAvoidingView,
  Modal, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput,
  TouchableOpacity, View,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { addRow, deleteRow, fetchRows, fetchSheets, Row, updateRow } from './src/api';

const BLUE = '#1a73e8';

function nowDatetime() {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

// ─── Scanner ──────────────────────────────────────────────────────────────────

interface ScannerProps {
  onScanned: (code: string) => void;
  onClose: () => void;
}

function Scanner({ onScanned, onClose }: ScannerProps) {
  const [permission, requestPermission] = useCameraPermissions();
  const scanned = useRef(false);

  useEffect(() => {
    if (!permission?.granted) requestPermission();
  }, []);

  if (!permission?.granted) {
    return (
      <View style={s.scanFull}>
        <Text style={s.scanMsg}>Нет доступа к камере</Text>
        <TouchableOpacity style={s.scanClose} onPress={onClose}>
          <Text style={s.scanCloseText}>Закрыть</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={s.scanFull}>
      <CameraView
        style={StyleSheet.absoluteFill}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8', 'code128', 'code39', 'qr'] }}
        onBarcodeScanned={({ data }) => {
          if (scanned.current) return;
          scanned.current = true;
          onScanned(data);
        }}
      />
      <View style={s.scanOverlay}>
        <View style={s.scanFrame} />
        <Text style={s.scanHint}>Наведите штрихкод на рамку</Text>
      </View>
      <TouchableOpacity style={s.scanClose} onPress={onClose}>
        <Text style={s.scanCloseText}>✕ Закрыть</Text>
      </TouchableOpacity>
    </View>
  );
}

// ─── Row Modal ────────────────────────────────────────────────────────────────

interface RowModalProps {
  visible: boolean;
  initial: Partial<Row> | null;
  onSave: (row: Omit<Row, 'id'>) => Promise<void>;
  onClose: () => void;
}

function RowModal({ visible, initial, onSave, onClose }: RowModalProps) {
  const [shk, setShk] = useState('');
  const [kol, setKol] = useState('1');
  const [korob, setKorob] = useState('1');
  const [scanning, setScanning] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (visible) {
      setShk(initial?.shk ?? '');
      setKol(initial?.kolichestvo ?? '1');
      setKorob(initial?.nomerKoroba ?? '1');
    }
  }, [visible, initial]);

  async function handleSave() {
    Keyboard.dismiss();
    setSaving(true);
    try {
      await onSave({ shk, kolichestvo: kol, nomerKoroba: korob, data: initial?.data || nowDatetime() });
      onClose();
    } catch (e: any) {
      Alert.alert('Ошибка', e.message);
    } finally {
      setSaving(false);
    }
  }

  if (scanning) {
    return (
      <Modal visible animationType="slide">
        <Scanner onScanned={code => { setShk(code); setScanning(false); }} onClose={() => setScanning(false)} />
      </Modal>
    );
  }

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <Pressable style={s.backdrop} onPress={onClose} />
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={s.modalWrap}>
        <View style={s.modal}>
          <Text style={s.modalTitle}>{initial?.id ? 'Изменить запись' : 'Добавить запись'}</Text>

          <Text style={s.label}>ШК (штрихкод)</Text>
          <View style={s.shkRow}>
            <TextInput style={[s.input, { flex: 1 }]} value={shk} onChangeText={setShk} placeholder="Сканируйте или введите" />
            <TouchableOpacity style={s.btnScan} onPress={() => setScanning(true)}>
              <Text style={{ color: '#fff', fontSize: 13 }}>📷 Скан</Text>
            </TouchableOpacity>
          </View>

          <Text style={s.label}>Количество</Text>
          <View style={s.counter}>
            <TouchableOpacity style={s.cBtn} onPress={() => setKol(v => String(Math.max(0, parseInt(v || '0') - 1)))}>
              <Text style={s.cBtnText}>−</Text>
            </TouchableOpacity>
            <TextInput style={[s.input, s.cInput]} value={kol} onChangeText={setKol} keyboardType="numeric" />
            <TouchableOpacity style={s.cBtn} onPress={() => setKol(v => String(parseInt(v || '0') + 1))}>
              <Text style={s.cBtnText}>+</Text>
            </TouchableOpacity>
          </View>

          <Text style={s.label}>Номер короба</Text>
          <View style={s.counter}>
            <TouchableOpacity style={s.cBtn} onPress={() => setKorob(v => String(Math.max(0, parseInt(v || '0') - 1)))}>
              <Text style={s.cBtnText}>−</Text>
            </TouchableOpacity>
            <TextInput style={[s.input, s.cInput]} value={korob} onChangeText={setKorob} keyboardType="numeric" />
            <TouchableOpacity style={s.cBtn} onPress={() => setKorob(v => String(parseInt(v || '0') + 1))}>
              <Text style={s.cBtnText}>+</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={[s.btnPrimary, saving && { opacity: 0.6 }]} onPress={handleSave} disabled={saving}>
            {saving ? <ActivityIndicator color="#fff" /> : <Text style={s.btnPrimaryText}>Сохранить</Text>}
          </TouchableOpacity>
          <TouchableOpacity style={s.btnSecondary} onPress={onClose}>
            <Text style={s.btnSecondaryText}>Отмена</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [sheets, setSheets] = useState<string[]>([]);
  const [activeSheet, setActiveSheet] = useState('');
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editRow, setEditRow] = useState<Row | null>(null);
  const [filterShk, setFilterShk] = useState('');

  useEffect(() => {
    fetchSheets()
      .then(list => {
        setSheets(list);
        if (list.length) setActiveSheet(list[0]);
      })
      .catch(e => Alert.alert('Ошибка', e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (activeSheet) loadRows();
  }, [activeSheet]);

  async function loadRows(isRefresh = false) {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const data = await fetchRows(activeSheet);
      setRows(data);
    } catch (e: any) {
      Alert.alert('Ошибка', e.message);
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }

  const handleSave = useCallback(async (row: Omit<Row, 'id'>) => {
    if (editRow?.id) {
      await updateRow(activeSheet, editRow.id, row);
    } else {
      await addRow(activeSheet, row);
    }
    await loadRows();
  }, [activeSheet, editRow]);

  async function handleDelete(id: number) {
    Alert.alert('Удалить строку?', undefined, [
      { text: 'Отмена', style: 'cancel' },
      {
        text: 'Удалить', style: 'destructive', onPress: async () => {
          try { await deleteRow(activeSheet, id); await loadRows(); }
          catch (e: any) { Alert.alert('Ошибка', e.message); }
        },
      },
    ]);
  }

  const filtered = filterShk
    ? rows.filter(r => (r.shk || '').toLowerCase().includes(filterShk.toLowerCase()))
    : rows;

  if (loading && !sheets.length) {
    return <View style={s.center}><ActivityIndicator size="large" color={BLUE} /></View>;
  }

  return (
    <View style={s.root}>
      <StatusBar style="light" />

      {/* Tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.tabs} contentContainerStyle={s.tabsContent}>
        {sheets.map(sh => (
          <TouchableOpacity key={sh} style={[s.tab, activeSheet === sh && s.tabActive]} onPress={() => setActiveSheet(sh)}>
            <Text style={[s.tabText, activeSheet === sh && s.tabTextActive]}>{sh}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Filter */}
      <View style={s.filterBar}>
        <TextInput style={s.filterInput} placeholder="🔍 Штрихкод" value={filterShk} onChangeText={setFilterShk} />
        {filterShk ? (
          <TouchableOpacity style={s.clearBtn} onPress={() => setFilterShk('')}>
            <Text style={{ color: '#666' }}>✕</Text>
          </TouchableOpacity>
        ) : null}
      </View>

      {/* List */}
      {loading ? (
        <View style={s.center}><ActivityIndicator size="large" color={BLUE} /></View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={r => String(r.id)}
          contentContainerStyle={filtered.length === 0 ? s.center : { padding: 12, paddingBottom: 80 }}
          refreshing={refreshing}
          onRefresh={() => loadRows(true)}
          ListEmptyComponent={<Text style={s.empty}>Нет данных</Text>}
          renderItem={({ item }) => (
            <View style={s.card}>
              <Text style={s.cardShk}>{item.shk || '—'}</Text>
              <View style={s.cardMeta}>
                <Text style={s.metaText}>Кол: <Text style={s.metaBold}>{item.kolichestvo}</Text></Text>
                <Text style={s.metaText}>Короб: <Text style={s.metaBold}>{item.nomerKoroba}</Text></Text>
                <Text style={s.metaDt}>📅 {item.data}</Text>
              </View>
              <View style={s.cardActions}>
                <TouchableOpacity style={s.btnEdit} onPress={() => { setEditRow(item); setModalVisible(true); }}>
                  <Text style={{ color: '#fff', fontSize: 13 }}>✏️</Text>
                </TouchableOpacity>
                <TouchableOpacity style={s.btnDel} onPress={() => handleDelete(item.id)}>
                  <Text style={{ color: '#fff', fontSize: 13 }}>🗑</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
        />
      )}

      {/* FAB */}
      <TouchableOpacity style={s.fab} onPress={() => { setEditRow(null); setModalVisible(true); }}>
        <Text style={{ color: '#fff', fontSize: 28, lineHeight: 32 }}>+</Text>
      </TouchableOpacity>

      <RowModal
        visible={modalVisible}
        initial={editRow}
        onSave={handleSave}
        onClose={() => { setModalVisible(false); setEditRow(null); }}
      />
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#f5f5f5', paddingTop: Platform.OS === 'ios' ? 50 : 30 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  tabs: { backgroundColor: BLUE, maxHeight: 48, flexGrow: 0 },
  tabsContent: { paddingHorizontal: 4 },
  tab: { paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 3, borderBottomColor: 'transparent' },
  tabActive: { borderBottomColor: '#fff' },
  tabText: { color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: '600' },
  tabTextActive: { color: '#fff' },

  filterBar: { backgroundColor: '#fff', flexDirection: 'row', padding: 10, gap: 8, borderBottomWidth: 1, borderBottomColor: '#eee', alignItems: 'center' },
  filterInput: { flex: 1, borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, fontSize: 14 },
  clearBtn: { padding: 8, backgroundColor: '#f0f0f0', borderRadius: 8 },

  card: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 10, shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 4, elevation: 2 },
  cardShk: { fontSize: 17, fontWeight: '700', marginBottom: 6 },
  cardMeta: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 10 },
  metaText: { fontSize: 13, color: '#666' },
  metaBold: { fontWeight: '700', color: '#222' },
  metaDt: { fontSize: 12, color: '#aaa' },
  cardActions: { flexDirection: 'row', gap: 8 },
  btnEdit: { backgroundColor: BLUE, borderRadius: 6, paddingHorizontal: 14, paddingVertical: 6 },
  btnDel: { backgroundColor: '#ea4335', borderRadius: 6, paddingHorizontal: 14, paddingVertical: 6 },
  empty: { color: '#999', fontSize: 15, textAlign: 'center' },

  fab: { position: 'absolute', bottom: 24, right: 24, width: 56, height: 56, borderRadius: 28, backgroundColor: BLUE, justifyContent: 'center', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 6, elevation: 6 },

  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  modalWrap: { justifyContent: 'flex-end' },
  modal: { backgroundColor: '#fff', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, paddingBottom: 40 },
  modalTitle: { fontSize: 18, fontWeight: '700', marginBottom: 16 },
  label: { fontSize: 13, color: '#555', marginBottom: 4 },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16, marginBottom: 12 },
  shkRow: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  btnScan: { backgroundColor: '#34a853', borderRadius: 8, paddingHorizontal: 14, justifyContent: 'center' },
  counter: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 12 },
  cBtn: { width: 36, height: 36, borderRadius: 18, borderWidth: 1, borderColor: '#ddd', backgroundColor: '#f0f0f0', justifyContent: 'center', alignItems: 'center' },
  cBtnText: { fontSize: 20, color: '#333' },
  cInput: { width: 70, textAlign: 'center', marginBottom: 0 },
  btnPrimary: { backgroundColor: BLUE, borderRadius: 10, padding: 14, alignItems: 'center', marginTop: 6 },
  btnPrimaryText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  btnSecondary: { backgroundColor: '#f0f0f0', borderRadius: 10, padding: 14, alignItems: 'center', marginTop: 8 },
  btnSecondaryText: { color: '#333', fontSize: 16 },

  scanFull: { flex: 1, backgroundColor: '#000', justifyContent: 'center', alignItems: 'center' },
  scanOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, justifyContent: 'center', alignItems: 'center' },
  scanFrame: { width: '80%', height: 100, borderWidth: 2, borderColor: 'rgba(255,255,255,0.85)', borderRadius: 8 },
  scanHint: { color: 'rgba(255,255,255,0.7)', fontSize: 13, marginTop: 16 },
  scanClose: { position: 'absolute', top: 60, right: 16, backgroundColor: 'rgba(0,0,0,0.7)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.4)', borderRadius: 10, paddingHorizontal: 20, paddingVertical: 12 },
  scanCloseText: { color: '#fff', fontSize: 16 },
  scanMsg: { color: '#fff', fontSize: 16, marginBottom: 20 },
});
