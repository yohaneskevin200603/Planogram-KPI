import os
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

try:
    import plotly.graph_objects as go
except ImportError:
    go = None

st.set_page_config(page_title="Monitoring Picking DPD", layout="wide", initial_sidebar_state="collapsed")

FILE_DISPLAY = "Planogram_Display.csv"
FILE_STORAGE = "Planogram_Storage.csv"
FILE_ZONA = "mapping_zona.csv"


@st.cache_data
def muat_data():
    d = pd.read_csv(FILE_DISPLAY, dtype={"LINE": str})
    s = pd.read_csv(FILE_STORAGE, dtype={"LINE": str})

    # Rapikan PLU (di file Display bentuknya desimal) dan buat kode lokasi
    for df in (d, s):
        df["PLU"] = pd.to_numeric(df["PLU"], errors="coerce").astype("Int64").astype("string")
        df["LOKASI"] = (
            df["LINE"] + "-" + df["RAK"].astype(str).str.zfill(2) + "-"
            + df["SHELF"].astype(str).str.zfill(2) + "-"
            + df["CELL"].astype(str) + "-" + df["SUBCELL"].astype(str)
        )

    # Mapping LINE -> ZONA. Kalau file belum ada, dibuatkan template kosong.
    if not os.path.exists(FILE_ZONA):
        semua_line = sorted(set(d["LINE"]) | set(s["LINE"]))
        pd.DataFrame({"LINE": semua_line, "ZONA": ""}).to_csv(FILE_ZONA, index=False)
    zona = pd.read_csv(FILE_ZONA, dtype=str).fillna("")
    # Excel sering menghapus nol di depan (01 jadi 1), jadi disamakan lagi jadi 2 karakter
    zona["LINE"] = zona["LINE"].str.strip().str.zfill(2)
    zona["ZONA"] = zona["ZONA"].str.strip().str.replace(r"\.0$", "", regex=True)
    zona["ZONA"] = zona["ZONA"].apply(
        lambda z: "Belum dipetakan" if z == "" else (f"Zona {int(z):02d}" if z.isdigit() else z)
    )
    d = d.merge(zona, on="LINE", how="left")
    s = s.merge(zona, on="LINE", how="left")
    d["ZONA"] = d["ZONA"].fillna("Belum dipetakan")
    s["ZONA"] = s["ZONA"].fillna("Belum dipetakan")
    return d, s


try:
    display, storage = muat_data()
except FileNotFoundError as e:
    st.error(f"File tidak ditemukan: {e.filename}. Taruh file CSV satu folder dengan app.py.")
    st.stop()

KOLOM_DISPLAY = ["ZONA", "LOKASI", "PLU", "NAMA", "FRAC", "UNIT", "QTY_IN_STORAGE", "TGL_EXP"]
KOLOM_STORAGE = ["ZONA", "LOKASI", "PLU", "NAMA", "QTY", "TGL_EXP"]
display_terisi = display[display["PLU"].notna()]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@600;700&display=swap');
.stApp { font-family: 'Barlow', sans-serif; }
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 5rem !important; max-width: 1250px; }
.hero { background: #12337a; color: #fff; padding: 18px 24px 16px; border-bottom: 5px solid #d62828;
        border-radius: 6px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.hero-title { font-family: 'Barlow Condensed', sans-serif; font-size: 2.3rem; font-weight: 700; line-height: 1.05; margin: 0; }
.hero-sub { opacity: .88; margin-top: 6px; font-size: 1rem; }
.hero-badge { background: #f2b705; color: #1a1a1a; padding: 3px 10px; border-radius: 4px; font-weight: 600; font-size: .85rem; white-space: nowrap; }
div[data-testid="stMetric"] { background: rgba(128,128,128,.09); border-left: 4px solid #3b6fe0; padding: 12px 16px; border-radius: 6px; }
div[data-testid="stMetricValue"] { font-family: 'Barlow Condensed', sans-serif; font-size: 2.2rem; font-weight: 700; }
button[data-baseweb="tab"] p { font-size: 1rem; font-weight: 600; }
@media (max-width: 640px) {
  .block-container, [data-testid="stMainBlockContainer"] { padding-left: .9rem !important; padding-right: .9rem !important; padding-top: 4.2rem !important; }
  .hero { flex-direction: column; padding: 14px 16px 12px; }
  .hero-title { font-size: 1.7rem; }
  .hero-sub { font-size: .9rem; }
  div[data-testid="stMetricValue"] { font-size: 1.8rem; }
  button[data-baseweb="tab"] p { font-size: .9rem; }
  h2, h3 { font-size: 1.25rem !important; }
}
</style>
<div class="hero">
  <div>
    <div class="hero-title">Monitoring Picking DC</div>
    <div class="hero-sub">Waktu picking per DPD terhadap target 1 menit 45 detik, per zona dan per hari</div>
  </div>
  <div class="hero-badge">Data contoh</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Tentang dashboard")
    st.write("Prototipe untuk memantau KPI waktu picking tanpa turun ke lapangan.")
    st.markdown("**Sumber data saat ini**")
    st.write("Planogram asli, sedangkan waktu dan picker masih data contoh.")
    st.markdown("**Rencana pengembangan**")
    st.write("1. Sinkron real-time ke server DPD")
    st.write("2. Riwayat picking dari database")
    st.write("3. Login dan hak akses per peran")
    st.write("4. Notifikasi saat zona lewat target")

tab8, tab4, tab6, tab5, tab7, tab1, tab2, tab3 = st.tabs(
    ["Performance WH", "Monitoring Hari Ini", "Riwayat dan Tren", "Layout 3D", "Jalan Keliling 3D", "Cari Item", "Lihat per LINE", "Ringkasan"]
)

# ---------- TAB 1: cari item ----------
with tab1:
    kata = st.text_input("Ketik PLU atau nama item", placeholder="contoh: marlboro, atau 20107181")
    if kata:
        cocok = lambda df: df[
            df["PLU"].fillna("").str.contains(kata, case=False)
            | df["NAMA"].fillna("").str.contains(kata, case=False)
        ]
        hasil_d = cocok(display_terisi)
        hasil_s = cocok(storage)
        st.subheader(f"Lokasi Display / picking ({len(hasil_d)})")
        st.dataframe(hasil_d[KOLOM_DISPLAY], use_container_width=True, hide_index=True)
        st.subheader(f"Lokasi Storage / stok cadangan ({len(hasil_s)})")
        st.dataframe(hasil_s[KOLOM_STORAGE], use_container_width=True, hide_index=True)
    else:
        st.info("Ketik nama atau PLU item untuk melihat lokasinya.")

# ---------- TAB 2: per LINE ----------
with tab2:
    pilih = st.selectbox("Pilih LINE", sorted(display["LINE"].unique()))
    hanya_terisi = st.checkbox("Tampilkan hanya lokasi yang terisi", value=True)
    data_line = display[display["LINE"] == pilih]
    if hanya_terisi:
        data_line = data_line[data_line["PLU"].notna()]
    st.caption(f"Zona: {data_line['ZONA'].iloc[0] if len(data_line) else '-'} | {len(data_line)} lokasi")
    st.dataframe(data_line[KOLOM_DISPLAY], use_container_width=True, hide_index=True)

# ---------- TAB 3: ringkasan ----------
with tab3:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total lokasi display", f"{len(display):,}")
    c2.metric("Lokasi terisi", f"{len(display_terisi):,}")
    c3.metric("Item unik di display", f"{display_terisi['PLU'].nunique():,}")
    c4.metric("Lokasi storage", f"{len(storage):,}")
    st.subheader("Jumlah lokasi terisi per LINE")
    st.bar_chart(display_terisi.groupby("LINE").size())
    st.subheader("Jumlah lokasi terisi per ZONA")
    st.bar_chart(display_terisi.groupby("ZONA").size())

    st.divider()
    st.subheader("Kapasitas Storage: Terisi vs Kosong")
    st.caption("Dihitung dari baris lokasi di Planogram_Storage.csv — tiap baris mewakili satu slot nyata (RAK/SHELF/CELL/SUBCELL), terisi kalau ada PLU.")
    cap = storage.groupby("ZONA").agg(total=("PLU", "size"), terisi=("PLU", "count"))
    cap["kosong"] = cap["total"] - cap["terisi"]
    cap["persen_kosong"] = (cap["kosong"] / cap["total"] * 100).round(1)
    cap = cap[cap.index != "Belum dipetakan"].sort_values("kosong", ascending=False)

    total_all, terisi_all = int(cap["total"].sum()), int(cap["terisi"].sum())
    kosong_all = total_all - terisi_all
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total slot storage", f"{total_all:,}")
    s2.metric("Terisi", f"{terisi_all:,}", f"{terisi_all/total_all*100:.1f}%")
    s3.metric("Kosong", f"{kosong_all:,}", f"{kosong_all/total_all*100:.1f}%", delta_color="inverse")
    s4.metric("Zona paling banyak kosong", cap.index[0] if len(cap) else "-",
              f"{int(cap['kosong'].iloc[0]):,} slot" if len(cap) else "")

    if go is not None:
        kk1, kk2 = st.columns(2)
        with kk1:
            fkk = go.Figure(go.Bar(x=cap["kosong"], y=cap.index, orientation="h", marker_color="#8690a6",
                                    hovertemplate="%{y}: %{x:,} slot kosong<extra></extra>"))
            fkk.update_layout(title="Jumlah Slot Kosong per Zona", height=420, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fkk, use_container_width=True)
        with kk2:
            fkp = go.Figure(go.Bar(x=cap["persen_kosong"], y=cap.index, orientation="h", marker_color="#f2b705",
                                    hovertemplate="%{y}: %{x:.1f}%% kosong<extra></extra>"))
            fkp.update_layout(title="Persentase Kosong per Zona (%)", height=420, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fkp, use_container_width=True)
    else:
        st.bar_chart(cap["kosong"])
    with st.expander("Lihat tabel lengkap per zona"):
        st.dataframe(cap[["total", "terisi", "kosong", "persen_kosong"]], use_container_width=True)

# ---------- DATA CONTOH PICKING (nanti diganti data asli dari support) ----------
TARGET_DETIK = 105   # 1 menit 45 detik per DPD (1 toko di 1 zona)
TARGET_TOKO = 250    # target toko per hari


def fmt(detik):
    detik = int(round(detik))
    return f"{detik // 60}:{detik % 60:02d}"


@st.cache_data
def buat_data_contoh():
    rng = np.random.default_rng(42)
    zona_aktif = sorted(z for z in display_terisi["ZONA"].unique() if z not in ("Belum dipetakan", "Zona 00"))
    jam = {}
    awal = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
    dpd_rows, item_rows, n = [], [], 0
    for toko in range(1, TARGET_TOKO + 1):
        for z in rng.choice(zona_aktif, size=int(rng.integers(2, 5)), replace=False):
            n += 1
            id_dpd = f"DPD-{n:05d}"
            picker = f"Picker {z[-2:]}-{int(rng.integers(1, 4))}"
            sumber = display_terisi[display_terisi["ZONA"] == z]
            item = sumber.sample(min(len(sumber), int(rng.integers(3, 9))), random_state=n)
            durasi = int(np.clip(rng.normal(100, 28), 40, 260))
            mulai = jam.get(picker, awal) + timedelta(seconds=int(rng.integers(5, 300)))
            selesai = mulai + timedelta(seconds=durasi)
            jam[picker] = selesai
            total_qty = 0
            for r in item.itertuples():
                qty = int(rng.integers(1, 13))
                total_qty += qty
                item_rows.append((id_dpd, z, r.LOKASI, r.PLU, r.NAMA, qty))
            dpd_rows.append((id_dpd, f"TOKO-{1000 + toko}", z, picker, mulai, selesai, durasi, len(item), total_qty))
    dpd = pd.DataFrame(dpd_rows, columns=["ID_DPD", "TOKO", "ZONA", "PICKER", "MULAI", "SELESAI", "DURASI", "JML_ITEM", "TOTAL_QTY"])
    item = pd.DataFrame(item_rows, columns=["ID_DPD", "ZONA", "LOKASI", "PLU", "NAMA", "QTY"])
    return dpd, item


# ---------- TAB 4: monitoring picking ----------
with tab4:
    st.warning("DATA CONTOH: waktu, picker, dan toko dibuat acak untuk melihat tampilan. Bukan data asli.")
    dpd, item = buat_data_contoh()
    pilih_zona = st.multiselect("Filter zona (kosong = semua)", sorted(dpd["ZONA"].unique()))
    if pilih_zona:
        dpd = dpd[dpd["ZONA"].isin(pilih_zona)]
        item = item[item["ID_DPD"].isin(dpd["ID_DPD"])]

    rata = dpd["DURASI"].mean()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("DPD selesai", f"{len(dpd):,}")
    c2.metric("Toko terlayani", f"{dpd['TOKO'].nunique()} / {TARGET_TOKO}")
    c3.metric("Rata-rata waktu", fmt(rata), f"{rata - TARGET_DETIK:+.0f} dtk vs target", delta_color="inverse")
    c4.metric("Tercapai target", f"{(dpd['DURASI'] <= TARGET_DETIK).mean() * 100:.0f}%")
    c5.metric("Total qty item", f"{item['QTY'].sum():,}")

    st.subheader("Waktu rata-rata per zona (detik)")
    st.caption(f"Target: {TARGET_DETIK} detik (1:45). Batang di atas angka itu berarti lewat target.")
    per_zona = dpd.groupby("ZONA").agg(
        DPD=("ID_DPD", "count"), RATA=("DURASI", "mean"),
        TERCAPAI=("DURASI", lambda s: (s <= TARGET_DETIK).mean() * 100),
    )
    st.bar_chart(per_zona["RATA"])
    tabel_zona = per_zona.assign(
        RATA_WAKTU=per_zona["RATA"].map(fmt),
        TERCAPAI_PERSEN=per_zona["TERCAPAI"].round(0).astype(int).astype(str) + "%",
        STATUS=np.where(per_zona["RATA"] <= TARGET_DETIK, "✅ OK", "⚠️ Lewat target"),
    )[["DPD", "RATA_WAKTU", "TERCAPAI_PERSEN", "STATUS"]]
    st.dataframe(tabel_zona, use_container_width=True)

    st.subheader("10 picker paling lambat")
    per_picker = dpd.groupby("PICKER").agg(DPD=("ID_DPD", "count"), RATA=("DURASI", "mean")).sort_values("RATA", ascending=False).head(10)
    per_picker["RATA_WAKTU"] = per_picker["RATA"].map(fmt)
    st.dataframe(per_picker[["DPD", "RATA_WAKTU"]], use_container_width=True)

    st.subheader("Detail DPD: item apa yang dipicking")
    urut = dpd.sort_values("DURASI", ascending=False)
    label = {r.ID_DPD: f"{r.ID_DPD} | {r.ZONA} | {r.PICKER} | {fmt(r.DURASI)}" for r in urut.itertuples()}
    pilih_dpd = st.selectbox("Pilih DPD (diurutkan dari yang terlama)", list(label), format_func=label.get)
    info = dpd[dpd["ID_DPD"] == pilih_dpd].iloc[0]
    st.write(f"**{info['TOKO']}** | {info['ZONA']} | {info['PICKER']} | "
             f"{info['MULAI']:%H:%M:%S} - {info['SELESAI']:%H:%M:%S} | durasi {fmt(info['DURASI'])}")
    st.dataframe(item[item["ID_DPD"] == pilih_dpd][["LOKASI", "PLU", "NAMA", "QTY"]], use_container_width=True, hide_index=True)

# ---------- TAB 5: layout 3D per zona ----------
# Posisi tiap zona di denah: (x_kiri, x_kanan, y_atas, y_bawah) dalam piksel gambar layout.
# Satu zona boleh punya lebih dari satu kotak. Posisi mengikuti koreksi dari lapangan.
# Zona 12 dan 13 ukurannya masih perkiraan: ubah angkanya di sini kalau perlu.
DENAH = {
    "Zona 06": [(335, 445, 465, 685)], "Zona 15": [(478, 520, 465, 685)], "Zona 07": [(548, 805, 465, 685)],
    "Zona 08": [(835, 1100, 465, 685)], "Zona 09": [(1130, 1320, 465, 685)],
    "Zona 01": [(338, 380, 775, 990)], "Zona 14": [(410, 520, 775, 990)], "Zona 02": [(548, 735, 775, 990)],
    "Zona 03": [(765, 950, 775, 990)], "Zona 04": [(982, 1175, 775, 990)], "Zona 05": [(1205, 1320, 775, 990)],
    "Zona 10": [(635, 1300, 355, 440)],
    "Zona 11": [(635, 1300, 240, 285), (635, 1300, 295, 345)],
    "Zona 12": [(270, 300, 250, 370)], "Zona 13": [(270, 300, 410, 530)],
    "Rak kosong": [(338, 548, 245, 440)],
}
JENIS_ZONA = {
    "Zona 01": "Rokok", "Zona 02": "Non Food", "Zona 03": "Non Food", "Zona 04": "Susu Bubuk",
    "Zona 05": "Minuman Botol", "Zona 06": "Non Food (Non Storage)", "Zona 07": "Non Food",
    "Zona 08": "Snack", "Zona 09": "Snack", "Zona 10": "Bulky Fraction", "Zona 11": "Bulky Karton",
    "Zona 12": "Coklat (Non Storage)", "Zona 13": "Obat (Non Storage)",
    "Zona 14": "Raw Material + Tetrapack", "Zona 15": "Snack",
}
WARNA_ZONA = {
    "Zona 01": "#e63946", "Zona 02": "#9aa0a6", "Zona 03": "#8e44ad", "Zona 04": "#f77f00",
    "Zona 05": "#2ecc71", "Zona 06": "#27ae60", "Zona 07": "#b9770e", "Zona 08": "#3b3bd6",
    "Zona 09": "#e63946", "Zona 10": "#1e90ff", "Zona 11": "#b9770e", "Zona 12": "#f1c40f",
    "Zona 13": "#e0b000", "Zona 14": "#7f8c8d", "Zona 15": "#d4a017",
}


def kotak_3d(x0, x1, y0, y1, h, warna, teks, op=1.0):
    x = [x0, x1, x1, x0, x0, x1, x1, x0]
    y = [y0, y0, y1, y1, y0, y0, y1, y1]
    z = [0, 0, 0, 0, h, h, h, h]
    return go.Mesh3d(
        x=x, y=y, z=z, color=warna, flatshading=True, opacity=op,
        i=[0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3], j=[1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4],
        k=[2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7], hoverinfo="text", text=teks,
    )


@st.cache_data
def hitung_occupancy(display_df, storage_df):
    """Untuk tiap LINE, hitung struktur asli (RAK=kedalaman, SHELF=tinggi, CELL=lebar) dan
    daftar slot yang benar-benar terisi (ada PLU) dari kedua file CSV, dipisah storage vs display."""
    hasil = {}
    for ln in sorted(set(display_df["LINE"]) | set(storage_df["LINE"])):
        d = display_df[display_df["LINE"] == ln]
        s = storage_df[storage_df["LINE"] == ln]
        rak_max = int(max([d["RAK"].max() if len(d) else 0, s["RAK"].max() if len(s) else 0, 1]))
        shelf_max = int(max([d["SHELF"].max() if len(d) else 0, s["SHELF"].max() if len(s) else 0, 1]))
        storage_tier = int(s["SHELF"].max()) if len(s) and s["SHELF"].notna().any() else 2
        cell_max = int(max([d["CELL"].max() if len(d) else 0, s["CELL"].max() if len(s) else 0, 1]))
        occ_s = list(s.loc[s["PLU"].notna(), ["RAK", "SHELF", "CELL"]].itertuples(index=False, name=None))
        occ_d = list(d.loc[d["PLU"].notna(), ["RAK", "SHELF", "CELL"]].itertuples(index=False, name=None))
        hasil[ln] = dict(rak_max=max(rak_max, 1), shelf_max=max(shelf_max, 1), storage_tier=max(storage_tier, 1),
                          cell_max=max(cell_max, 1), occ_storage=occ_s, occ_display=occ_d)
    return hasil


def buat_batch_kotak():
    return {"x": [], "y": [], "z": [], "i": [], "j": [], "k": [], "facecolor": [], "n": 0}


_FACES = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
          (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]


def tambah_kotak_batch(batch, x0, x1, y0, y1, z0, z1, warna):
    base = batch["n"]
    batch["x"] += [x0, x1, x1, x0, x0, x1, x1, x0]
    batch["y"] += [y0, y0, y1, y1, y0, y0, y1, y1]
    batch["z"] += [z0, z0, z0, z0, z1, z1, z1, z1]
    for f in _FACES:
        batch["i"].append(base + f[0]); batch["j"].append(base + f[1]); batch["k"].append(base + f[2])
        batch["facecolor"].append(warna)
    batch["n"] += 8


def mesh_dari_batch(batch):
    if batch["n"] == 0:
        return None
    return go.Mesh3d(x=batch["x"], y=batch["y"], z=batch["z"], i=batch["i"], j=batch["j"], k=batch["k"],
                      facecolor=batch["facecolor"], flatshading=True, hoverinfo="skip", showlegend=False)


def gambar_line_detail(batch, frame_x, frame_y, frame_z, c, w, l0, l1, aZ, h_tier, info_tiang, occ, tiang_set):
    """Gambar satu baris rak (satu LINE) sedetail mungkin: kedalaman=RAK, tinggi=SHELF, lebar=CELL (dengan jarak).
    tiang_set dipakai supaya tiang di batas antara dua LINE yang bersebelahan tidak digambar dua kali (dedup),
    persis jumlah tiang pembagi antar rak di gudang asli (rak_max + 1 per baris rak, bukan dobel)."""
    rak_max, shelf_max, storage_tier, cell_max = occ["rak_max"], occ["shelf_max"], occ["storage_tier"], occ["cell_max"]
    bay_pitch = (l1 - l0) / rak_max
    slot_pitch = w / cell_max

    def xy(s, l):
        return (s, l) if aZ else (l, s)

    # rangka tiang di tiap batas bay (rak_max + 1 posisi), supaya terlihat jelas slot yang masih kosong
    tiang_l = np.linspace(l0, l1, rak_max + 1)
    for tepi in (c - w / 2, c + w / 2):
        for l in tiang_l:
            kunci = (round(tepi, 2), round(l, 2))
            if kunci in tiang_set:
                continue  # sudah digambar oleh LINE sebelahnya di batas yang sama
            tiang_set.add(kunci)
            x, y = xy(tepi, l)
            frame_x += [x, x, None]; frame_y += [y, y, None]; frame_z += [0, h_tier * 9, None]

    for tier in (max(1, storage_tier), shelf_max):  # rel bawah tier storage & rel paling atas, sbg siluet
        for l in (l0, l1):
            x, y = xy(c - w / 2, l); x2, y2 = xy(c + w / 2, l)
            z = h_tier * tier
            frame_x += [x, x2, None]; frame_y += [y, y2, None]; frame_z += [z, z, None]

    for tipe, warna in (("occ_storage", "#d62828"), ("occ_display", "#00a844")):
        for rak, shelf, cell in occ[tipe]:
            try:
                rak_i, shelf_i, cell_i = int(rak) - 1, int(shelf) - 1, int(cell) - 1
            except (ValueError, TypeError):
                continue
            if rak_i < 0 or shelf_i < 0 or cell_i < 0:
                continue
            rak_i = min(rak_i, rak_max - 1)
            cell_i = cell_i % cell_max
            depth_c = l0 + (rak_i + 0.5) * bay_pitch
            lat_c = (c - w / 2) + (cell_i + 0.5) * slot_pitch
            dh, lh = bay_pitch * 0.40, slot_pitch * 0.36
            x0, y0 = xy(lat_c - lh, depth_c - dh); x1, y1 = xy(lat_c + lh, depth_c + dh)
            z0 = h_tier * shelf_i
            tambah_kotak_batch(batch, min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), z0, z0 + h_tier * 0.8, warna)


with tab5:
    if go is None:
        st.error("Library plotly belum terinstall. Di Terminal ketik: python -m pip install plotly, lalu jalankan ulang.")
        st.stop()
    st.caption(
        "Putar dengan mouse (klik-tahan), zoom dengan scroll. Struktur rak mengikuti data asli: **RAK = kedalaman "
        "ke belakang** (9 untuk zona fraction, 12 untuk zona bulky, sesuai data), **SHELF = tinggi**, **CELL = lebar "
        "dalam satu rak** (dipisah jarak). Kotak **merah solid = tingkat storage terisi**, **hijau solid = tingkat "
        "display/picking terisi** — kotak hanya muncul di lokasi yang benar-benar ada barangnya (PLU); rangka kosong "
        "berarti lokasi itu kosong. Posisi Zona 12 dan 13 masih perkiraan."
    )
    occ_all = hitung_occupancy(display, storage)
    jml_line = display.groupby("ZONA")["LINE"].unique()
    jml_line_s = storage.groupby("ZONA")["LINE"].unique()

    batch = buat_batch_kotak()
    frame_x, frame_y, frame_z = [], [], []
    label_traces = []
    h_total = 9 * 1.2  # skala sama seperti sebelumnya (9 tingkat x 1.2 unit)
    h_tier = h_total / 9

    for nama, daftar_kotak in DENAH.items():
        label = nama[-2:] if nama.startswith("Zona") else "kosong"
        daftar_line = sorted(set(jml_line.get(nama, [])) | set(jml_line_s.get(nama, [])))
        if not daftar_line:
            daftar_line = ["?"] * max(1, len(daftar_kotak) * 4)  # fallback: zona tanpa data LINE sungguhan
        n_line = len(daftar_line)
        li = 0
        tiang_set = set()  # satu zona = satu set dedup, supaya tiang di batas antar-LINE tidak digambar dobel
        for xa, xb, ya, yb in daftar_kotak:
            X0, X1 = xa / 10, xb / 10
            Y0, Y1 = (1130 - ya) / 10, (1130 - yb) / 10
            aZ = (X1 - X0) <= 4.0  # rak memanjang ke arah y kalau kotaknya sempit (lebar <= 4 unit)
            y0, y1 = min(Y0, Y1), max(Y0, Y1)
            s0, s1, l0, l1 = (X0, X1, y0, y1) if aZ else (y0, y1, X0, X1)
            n_disini = max(1, n_line // len(daftar_kotak)) if len(daftar_kotak) > 1 else n_line
            w = min(1.2, (s1 - s0) / max(n_disini, 1) * 0.72)
            for k in range(n_disini):
                if li >= n_line:
                    break
                ln = daftar_line[li]; li += 1
                c = s0 + (k + 0.5) * (s1 - s0) / n_disini
                if ln in occ_all:
                    gambar_line_detail(batch, frame_x, frame_y, frame_z, c, w, l0, l1, aZ, h_tier, nama, occ_all[ln], tiang_set)
                else:
                    # tidak ada data asli utk LINE ini: rangka datar polos saja, tanpa kotak terisi
                    for tepi in (c - w / 2, c + w / 2):
                        for l in (l0, l1):
                            x, y = (tepi, l) if aZ else (l, tepi)
                            frame_x += [x, x, None]; frame_y += [y, y, None]; frame_z += [0, h_total, None]
            label_traces.append((nama[-2:] if nama.startswith("Zona") else "kosong",
                                  (xa + xb) / 20, (2260 - ya - yb) / 20, h_total + 0.3))

    fig = go.Figure()
    mesh = mesh_dari_batch(batch)
    if mesh is not None:
        fig.add_trace(mesh)
    fig.add_trace(go.Scatter3d(x=frame_x, y=frame_y, z=frame_z, mode="lines",
                                line=dict(color="#1f4fd8", width=2.2), hoverinfo="skip", showlegend=False))
    for lbl, lx, ly, lz in label_traces:
        fig.add_trace(go.Scatter3d(x=[lx], y=[ly], z=[lz], mode="text", text=[lbl],
                                    textfont=dict(size=13, color="#0f2a63"), hoverinfo="skip", showlegend=False))
    fig.update_layout(
        height=560, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
        scene=dict(aspectmode="data", xaxis_visible=False, yaxis_visible=False, zaxis_visible=False,
                   camera=dict(eye=dict(x=0.0, y=-1.4, z=1.1))),
    )
    st.plotly_chart(fig, use_container_width=True)
    total_slot = sum(len(o["occ_storage"]) + len(o["occ_display"]) for o in occ_all.values())
    st.caption(f"Total {total_slot:,} slot terisi digambar sebagai kotak solid, dari {len(occ_all)} baris rak (LINE) di seluruh gudang. "
               "Ringkasan jumlah slot kosong per zona ada di tab **Ringkasan**.")


# ---------- TAB 6: riwayat dan tren (data contoh) ----------
@st.cache_data
def buat_riwayat_contoh(hari=60):
    rng = np.random.default_rng(7)
    zona_aktif = sorted(z for z in display_terisi["ZONA"].unique() if z not in ("Belum dipetakan", "Zona 00"))
    selisih = {z: rng.normal(0, 9) for z in zona_aktif}  # tiap zona punya karakter sendiri
    akhir = datetime.now().date()
    baris = []
    for i in range(hari):
        tgl = pd.Timestamp(akhir - timedelta(days=hari - 1 - i))
        faktor = 0.6 if tgl.weekday() >= 5 else 1.0
        toko = int(rng.normal(245, 12) * faktor)
        dasar = 114 - i * 0.28  # contoh: performa membaik pelan-pelan
        for z in zona_aktif:
            dpd = int(toko * rng.uniform(0.4, 0.75))
            rata = float(np.clip(rng.normal(dasar + selisih[z], 4), 60, 200))
            ok = float(np.clip(100 - (rata - 85) * 2.1 + rng.normal(0, 3), 30, 99))
            baris.append((tgl, z, toko, dpd, rata, ok, int(dpd * rng.normal(32, 3))))
    return pd.DataFrame(baris, columns=["TANGGAL", "ZONA", "TOKO", "DPD", "RATA", "TERCAPAI", "QTY"])


def rapikan(fig, tinggi=330):
    fig.update_layout(height=tinggi, margin=dict(l=10, r=10, t=10, b=10), font=dict(family="Barlow, sans-serif"))
    return fig


with tab6:
    if go is None:
        st.error("Library plotly belum terinstall (cek requirements.txt).")
        st.stop()
    st.caption("Data contoh 60 hari. Nanti diganti riwayat dari database picking.")
    rentang = st.radio("Periode", [7, 14, 30], index=1, horizontal=True, format_func=lambda n: f"{n} hari terakhir")

    riw = buat_riwayat_contoh()
    riw["W_RATA"] = riw["RATA"] * riw["DPD"]
    riw["W_OK"] = riw["TERCAPAI"] * riw["DPD"]
    harian = riw.groupby("TANGGAL").agg(
        TOKO=("TOKO", "first"), DPD=("DPD", "sum"), QTY=("QTY", "sum"), W_RATA=("W_RATA", "sum"), W_OK=("W_OK", "sum"))
    harian["RATA"] = harian["W_RATA"] / harian["DPD"]
    harian["TERCAPAI"] = harian["W_OK"] / harian["DPD"]
    cur, prev = harian.tail(rentang), harian.iloc[-2 * rentang:-rentang]

    def rata_berbobot(d):
        return d["W_RATA"].sum() / d["DPD"].sum()

    def ok_berbobot(d):
        return d["W_OK"].sum() / d["DPD"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rata-rata waktu per DPD", fmt(rata_berbobot(cur)),
              f"{rata_berbobot(cur) - rata_berbobot(prev):+.0f} dtk dari periode lalu", delta_color="inverse")
    c2.metric("DPD tercapai target", f"{ok_berbobot(cur):.0f}%", f"{ok_berbobot(cur) - ok_berbobot(prev):+.1f} poin dari periode lalu")
    c3.metric("Toko per hari", f"{cur['TOKO'].mean():.0f}", f"target {TARGET_TOKO}", delta_color="off")
    c4.metric("Total qty item", f"{cur['QTY'].sum():,}", f"{(cur['QTY'].sum() / prev['QTY'].sum() - 1) * 100:+.1f}% dari periode lalu")

    st.subheader("Perkembangan waktu picking")
    f1 = go.Figure(go.Scatter(x=cur.index, y=cur["RATA"], mode="lines+markers", name="Rata-rata waktu",
                              line=dict(color="#3b6fe0", width=3), hovertemplate="%{x|%d %b}: %{y:.0f} detik<extra></extra>"))
    f1.add_hline(y=TARGET_DETIK, line_dash="dash", line_color="#d62828", annotation_text="Target 1:45", annotation_position="top left")
    f1.update_yaxes(title="detik per DPD")
    st.plotly_chart(rapikan(f1), use_container_width=True)

    k1, k2 = st.columns(2)
    with k1:
        st.subheader("DPD tercapai target (%)")
        f2 = go.Figure(go.Bar(x=cur.index, y=cur["TERCAPAI"], marker_color="#2e9e5b",
                              hovertemplate="%{x|%d %b}: %{y:.0f}%<extra></extra>"))
        f2.update_yaxes(range=[0, 100])
        st.plotly_chart(rapikan(f2, 280), use_container_width=True)
    with k2:
        st.subheader("Toko terlayani per hari")
        f3 = go.Figure(go.Bar(x=cur.index, y=cur["TOKO"], marker_color="#3b6fe0",
                              hovertemplate="%{x|%d %b}: %{y} toko<extra></extra>"))
        f3.add_hline(y=TARGET_TOKO, line_dash="dash", line_color="#d62828", annotation_text="Target 250")
        st.plotly_chart(rapikan(f3, 280), use_container_width=True)

    st.subheader("Peta panas waktu picking: zona per hari")
    st.caption("Hijau lebih cepat dari target 1:45, merah lebih lambat.")
    pv = riw[riw["TANGGAL"].isin(cur.index)].pivot(index="ZONA", columns="TANGGAL", values="RATA")
    f4 = go.Figure(go.Heatmap(z=pv.values, x=pv.columns, y=pv.index, zmid=TARGET_DETIK,
                              colorscale=[[0, "#2e9e5b"], [0.5, "#f3f0e8"], [1, "#d62828"]],
                              colorbar=dict(title="detik"), hovertemplate="%{y}, %{x|%d %b}: %{z:.0f} detik<extra></extra>"))
    f4.update_yaxes(autorange="reversed")
    st.plotly_chart(rapikan(f4, 420), use_container_width=True)

    st.subheader("Peringkat zona pada periode ini")
    pz = riw[riw["TANGGAL"].isin(cur.index)].groupby("ZONA").agg(DPD=("DPD", "sum"), W_RATA=("W_RATA", "sum"), W_OK=("W_OK", "sum"))
    pz["Rata-rata waktu"] = (pz["W_RATA"] / pz["DPD"]).map(fmt)
    pz["Tercapai"] = (pz["W_OK"] / pz["DPD"]).round(0).astype(int).astype(str) + "%"
    pz["Status"] = np.where(pz["W_RATA"] / pz["DPD"] <= TARGET_DETIK, "OK", "Lewat target")
    st.dataframe(pz.assign(_u=pz["W_RATA"] / pz["DPD"]).sort_values("_u", ascending=False)[["DPD", "Rata-rata waktu", "Tercapai", "Status"]],
                 use_container_width=True)


# ---------- TAB 7: jalan keliling gudang (prototipe konsep, Three.js) ----------
HTML_WALK = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;overflow:hidden;background:#dfe6ee;font-family:Arial,sans-serif;touch-action:none}
#c{display:block;width:100%;height:100%}
.hud{position:absolute;color:#fff;background:rgba(18,51,122,.88);padding:6px 10px;border-radius:6px;font-size:13px}
#zona{top:10px;left:10px;font-weight:bold}
#jump{top:10px;right:10px}
#hint{bottom:10px;left:10px;max-width:46%;font-size:12px}
#mini{position:absolute;right:10px;bottom:10px;border:2px solid #12337a;background:rgba(255,255,255,.75);border-radius:4px}
#joy{position:absolute;left:18px;bottom:18px;width:110px;height:110px;border-radius:50%;background:rgba(18,51,122,.22);border:2px solid rgba(18,51,122,.5);display:none}
#knob{position:absolute;left:35px;top:35px;width:40px;height:40px;border-radius:50%;background:rgba(18,51,122,.85)}
@media (pointer:coarse){#hint{left:145px;max-width:34%}}
</style></head><body>
<canvas id="c" tabindex="0"></canvas>
<div class="hud" id="zona">Zona: -</div>
<select class="hud" id="jump"></select>
<canvas id="mini" width="170" height="137"></canvas>
<div id="joy"><div id="knob"></div></div>
<div class="hud" id="hint">Klik gambar, seret mouse untuk melihat sekeliling, tombol W A S D untuk berjalan (Shift = lari)</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
if(!window.THREE){document.body.innerHTML='<p style="padding:20px">Three.js gagal dimuat. Cek koneksi internet.</p>';}
else{
const D=__DATA__, W=140, HD=113, LV=9, LH=1.2, RH=LV*LH, CART=[0xc89b6a,0xb98652,0xd8b88a];
const cv=document.getElementById('c');
const renderer=new THREE.WebGLRenderer({canvas:cv,antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
const scene=new THREE.Scene(); scene.background=new THREE.Color(0xdfe6ee); scene.fog=new THREE.Fog(0xdfe6ee,50,230);
const cam=new THREE.PerspectiveCamera(70,1,0.1,400); cam.rotation.order='YXZ';
scene.add(new THREE.HemisphereLight(0xffffff,0x8899aa,1.0));
const sun=new THREE.DirectionalLight(0xffffff,0.5); sun.position.set(40,100,30); scene.add(sun);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(W,HD),new THREE.MeshLambertMaterial({color:0xc9ced6}));
floor.rotation.x=-Math.PI/2; floor.position.set(W/2,0,HD/2); scene.add(floor);

const B={post:[],red:[],green:[],carton:[]}, solids=[];
const add=(l,x,y,z,sx,sy,sz,c)=>l.push([x,y,z,sx,sy,sz,c]);
function label(txt,sub,color,x,y,z){
  const c=document.createElement('canvas'); c.width=512; c.height=160; const g=c.getContext('2d');
  g.fillStyle='rgba(18,51,122,.92)'; g.fillRect(0,0,512,160); g.fillStyle=color; g.fillRect(0,0,16,160);
  g.fillStyle='#fff'; g.font='bold 64px Arial'; g.fillText(txt,34,76); g.font='34px Arial'; g.fillText(sub,34,126);
  const s=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c)})); s.scale.set(11,3.4,1); s.position.set(x,y,z); scene.add(s);
}
// Struktur rak mengikuti data asli: RAK=kedalaman, SHELF=tinggi, CELL=lebar (dengan jarak).
// Kotak solid hanya digambar di slot yang benar-benar terisi (ada PLU); sisanya cuma rangka kosong.
D.forEach((zn,zi)=>{
  const tiangSet=new Set(); // dedup: tiang di batas antar-LINE bersebelahan jangan digambar dobel
  const tiang=(s,l,aZ)=>{
    const key=(aZ?'Z':'X')+Math.round(s*50)+'_'+Math.round(l*50);
    if(tiangSet.has(key)) return; tiangSet.add(key);
    add(B.post, aZ?s:l, RH/2, aZ?l:s, 0.14,RH,0.14, 0);
  };
  zn.rects.forEach((r,ri)=>{
    const x0=r[0],x1=r[1],z0=r[2],z1=r[3],w=x1-x0,d=z1-z0;
    const p=new THREE.Mesh(new THREE.PlaneGeometry(w,d),new THREE.MeshLambertMaterial({color:zn.warna,transparent:true,opacity:.55}));
    p.rotation.x=-Math.PI/2; p.position.set((x0+x1)/2,0.02,(z0+z1)/2); scene.add(p);
    const aZ=w<=4.0, n=Math.max(1, Math.round((zn.lines.length||1)/zn.rects.length));
    const s0=aZ?x0:z0, s1=aZ?x1:z1, l0=aZ?z0:x0, l1=aZ?z1:x1;
    const rw=Math.min(1.2,(s1-s0)/n*0.72);
    const mulai = ri*n;
    for(let i=0;i<n;i++){
      const c=s0+(i+.5)*(s1-s0)/n;
      solids.push(aZ?[c-rw/2,c+rw/2,l0,l1]:[l0,l1,c-rw/2,c+rw/2]);
      const ln = zn.lines[mulai+i];
      if(!ln){ // tidak ada data LINE asli: rangka datar polos (cuma 2 tiang depan-belakang)
        for(const e of [-1,1]){ const s=c+e*rw/2; tiang(s,l0,aZ); tiang(s,l1,aZ); }
        continue;
      }
      const bays=ln.rak, cells=ln.cell, bl=(l1-l0)/bays, cw=rw/cells;
      for(let b=0;b<=bays;b++) for(const e of [-1,1]){
        tiang(c+e*rw/2, l0+b*bl, aZ); // rak_max+1 tiang per baris rak (dedup di batas antar-LINE)
      }
      // rel referensi cuma di 2 tingkat (batas tier storage & paling atas), BUKAN di tiap 9 tingkat —
      // supaya tiang vertikal (rak_max+1) tetap yang paling menonjol, bukan tertimbun rel horizontal
      for(const kTier of [Math.max(1, ln.stor), ln.shelf]){
        const y=kTier*LH, m=(l0+l1)/2;
        for(const e of [-1,1]){ const s=c+e*rw/2; add(B.post, aZ?s:m, y, aZ?m:s, aZ?0.1:(l1-l0), 0.1, aZ?(l1-l0):0.1, 0); }
      }
      const taruh=(list,rak,shelf,cell)=>{
        const rak_i=Math.min(Math.max(0,(rak|0)-1), bays-1), shelf_i=Math.max(0,(shelf|0)-1), cell_i=((cell|0)-1+cells*999)%cells;
        if(shelf_i>=LV) return;
        const depthC=l0+(rak_i+0.5)*bl, latC=(c-rw/2)+(cell_i+0.5)*cw;
        const dh=bl*0.40, lh=cw*0.36, y0=(shelf_i)*LH;
        add(list, aZ?latC:depthC, y0+LH*0.4, aZ?depthC:latC, aZ?lh*2:bl*0.8, LH*0.8, aZ?bl*0.8:lh*2, 0);
      };
      ln.os.forEach(t=>taruh(B.red, t[0], t[1], t[2]));
      ln.od.forEach(t=>taruh(B.green, t[0], t[1], t[2]));
    }
    if(ri===0) label(zn.nama.toUpperCase(), zn.jenis, zn.warna, (x0+x1)/2, RH+3, (z0+z1)/2);
  });
});
const bg=new THREE.BoxGeometry(1,1,1);
function inst(list,color){
  if(!list.length) return;
  const m=new THREE.InstancedMesh(bg,new THREE.MeshLambertMaterial({color:0xffffff}),list.length);
  const M=new THREE.Matrix4(), q=new THREE.Quaternion(), col=new THREE.Color();
  list.forEach((a,i)=>{ M.compose(new THREE.Vector3(a[0],a[1],a[2]),q,new THREE.Vector3(a[3],a[4],a[5])); m.setMatrixAt(i,M); col.set(color===null?a[6]:color); m.setColorAt(i,col); });
  scene.add(m);
}
inst(B.post,0x1f4fd8); inst(B.red,0xd62828); inst(B.green,0x00a844); inst(B.carton,null);

// pemain dan tabrakan
const P={x:112,z:73,yaw:Math.PI/2,pitch:0}, R=0.45;
const hit=(x,z)=>{ for(const s of solids) if(x>s[0]-R&&x<s[1]+R&&z>s[2]-R&&z<s[3]+R) return true; return x<1||x>W-1||z<1||z>HD-1; };
const unstick=()=>{ let n=0; while(hit(P.x,P.z)&&n++<80) P.z+=0.5; };
function jump(zn){
  const r=zn.rects[0], cx=(r[0]+r[1])/2, cz=(r[2]+r[3])/2;
  if(r[2]>=75){P.x=cx;P.z=73;P.yaw=Math.PI;}
  else if(r[2]>=46&&r[3]<=70){P.x=cx;P.z=73;P.yaw=0;}
  else if(r[1]<=31){P.x=24;P.z=cz;P.yaw=-Math.PI/2;}
  else{P.x=135;P.z=cz;P.yaw=Math.PI/2;}
  P.pitch=0; unstick();
}
const sel=document.getElementById('jump');
sel.innerHTML='<option value="">Lompat ke zona...</option>'+D.map((z,i)=>'<option value="'+i+'">'+z.nama+' - '+z.jenis+'</option>').join('');
sel.onchange=()=>{ if(sel.value!==''){ jump(D[+sel.value]); sel.value=''; cv.focus(); } };

// kontrol
const keys={}; addEventListener('keydown',e=>{keys[e.key.toLowerCase()]=true;}); addEventListener('keyup',e=>{keys[e.key.toLowerCase()]=false;});
const clampP=v=>Math.max(-1.2,Math.min(1.2,v));
let drag=false,lx=0,ly=0;
cv.addEventListener('mousedown',e=>{drag=true;lx=e.clientX;ly=e.clientY;cv.focus();});
addEventListener('mouseup',()=>{drag=false;});
addEventListener('mousemove',e=>{ if(!drag) return; P.yaw+=(e.clientX-lx)*0.005; P.pitch=clampP(P.pitch+(e.clientY-ly)*0.005); lx=e.clientX; ly=e.clientY; });
const joy=document.getElementById('joy'), knob=document.getElementById('knob');
if(matchMedia('(pointer:coarse)').matches) joy.style.display='block';
let jt=null,lt=null,jc=[0,0],jv=[0,0];
cv.addEventListener('touchstart',e=>{ for(const t of e.changedTouches){
  if(t.clientX<innerWidth*0.4&&jt===null){jt=t.identifier;jc=[t.clientX,t.clientY];}
  else if(lt===null){lt=t.identifier;lx=t.clientX;ly=t.clientY;} } e.preventDefault(); },{passive:false});
cv.addEventListener('touchmove',e=>{ for(const t of e.changedTouches){
  if(t.identifier===jt){ let dx=(t.clientX-jc[0])/45, dy=(t.clientY-jc[1])/45; const m=Math.hypot(dx,dy); if(m>1){dx/=m;dy/=m;} jv=[dx,dy]; knob.style.transform='translate('+(dx*30)+'px,'+(dy*30)+'px)'; }
  else if(t.identifier===lt){ P.yaw+=(t.clientX-lx)*0.006; P.pitch=clampP(P.pitch+(t.clientY-ly)*0.006); lx=t.clientX; ly=t.clientY; } } e.preventDefault(); },{passive:false});
cv.addEventListener('touchend',e=>{ for(const t of e.changedTouches){
  if(t.identifier===jt){jt=null;jv=[0,0];knob.style.transform='';} if(t.identifier===lt) lt=null; } });

function step(dt){
  let f=0,s=0;
  if(keys['w']||keys['arrowup']) f+=1; if(keys['s']||keys['arrowdown']) f-=1;
  if(keys['d']) s+=1; if(keys['a']) s-=1;
  if(keys['arrowleft']) P.yaw+=1.6*dt; if(keys['arrowright']) P.yaw-=1.6*dt;
  f+=-jv[1]; s+=jv[0];
  const sp=(keys['shift']?12:6)*dt, fx=-Math.sin(P.yaw), fz=-Math.cos(P.yaw), rx=Math.cos(P.yaw), rz=-Math.sin(P.yaw);
  const dx=(fx*f+rx*s)*sp, dz=(fz*f+rz*s)*sp;
  if(!hit(P.x+dx,P.z)) P.x+=dx; if(!hit(P.x,P.z+dz)) P.z+=dz;
}
const mini=document.getElementById('mini'), mg=mini.getContext('2d'), zonaEl=document.getElementById('zona');
function hud(){
  const k=mini.width/W; mg.clearRect(0,0,mini.width,mini.height);
  D.forEach(z=>{ mg.fillStyle=z.warna; z.rects.forEach(r=>mg.fillRect(r[0]*k,r[2]*k,(r[1]-r[0])*k,(r[3]-r[2])*k)); });
  mg.fillStyle='#000'; mg.beginPath(); mg.arc(P.x*k,P.z*k,3.5,0,7); mg.fill();
  mg.strokeStyle='#000'; mg.lineWidth=2; mg.beginPath(); mg.moveTo(P.x*k,P.z*k); mg.lineTo((P.x-Math.sin(P.yaw)*7)*k,(P.z-Math.cos(P.yaw)*7)*k); mg.stroke();
  let nm='Lorong / area umum';
  D.forEach(z=>z.rects.forEach(r=>{ if(P.x>=r[0]-1&&P.x<=r[1]+1&&P.z>=r[2]-1&&P.z<=r[3]+1) nm=z.nama+': '+z.jenis; }));
  zonaEl.textContent=nm;
}
function resize(){ renderer.setSize(innerWidth,innerHeight,false); cam.aspect=innerWidth/innerHeight; cam.updateProjectionMatrix(); }
addEventListener('resize',resize); resize();
let last=performance.now();
(function loop(now){
  const dt=Math.min(0.05,(now-last)/1000); last=now; step(dt);
  cam.position.set(P.x,1.6,P.z); cam.rotation.y=P.yaw; cam.rotation.x=P.pitch;
  renderer.render(scene,cam); hud(); requestAnimationFrame(loop);
})(last);
}
</script></body></html>"""

with tab7:
    import json
    import streamlit.components.v1 as components

    st.caption("Prototipe konsep: jalan keliling gudang seperti game. Laptop: klik gambar, seret mouse untuk melihat sekeliling, "
               "tombol W A S D untuk berjalan. HP: joystick di kiri bawah untuk berjalan, geser jari di sisi kanan untuk melihat. "
               "Pakai menu di kanan atas untuk lompat ke zona.")
    occ_all_w = hitung_occupancy(display, storage)
    jml_line_w = display.groupby("ZONA")["LINE"].unique()
    jml_line_ws = storage.groupby("ZONA")["LINE"].unique()
    data_zona = []
    for nama, kotak in DENAH.items():
        daftar_line = sorted(set(jml_line_w.get(nama, [])) | set(jml_line_ws.get(nama, [])))
        lines_detail = []
        for ln in daftar_line:
            o = occ_all_w.get(ln)
            if o:
                lines_detail.append({
                    "rak": o["rak_max"], "shelf": o["shelf_max"], "stor": o["storage_tier"], "cell": o["cell_max"],
                    "os": o["occ_storage"], "od": o["occ_display"],
                })
        data_zona.append({
            "nama": nama, "jenis": JENIS_ZONA.get(nama, "Rak kosong"), "warna": WARNA_ZONA.get(nama, "#777777"),
            "rects": [[a / 10, b / 10, c / 10, d / 10] for a, b, c, d in kotak],
            "lines": lines_detail,
        })
    components.html(HTML_WALK.replace("__DATA__", json.dumps(data_zona)), height=620)


# ---------- TAB 8: Performance Warehouse (DATA ASLI, Agustus 2026) ----------
@st.cache_data
def muat_performance_wh():
    harian = pd.read_csv("performance_harian.csv", parse_dates=["tanggal"])
    sl_zona = pd.read_csv("sl_per_zona.csv", parse_dates=["tanggal"])
    tp_zona = pd.read_csv("time_pick_per_zona.csv", parse_dates=["tanggal"])
    nkl_zona = pd.read_csv("nkl_per_zona.csv")
    rusak_zona = pd.read_csv("rusak_per_zona.csv")
    tren_rusak = pd.read_csv("tren_rusak.csv", parse_dates=["tanggal"])
    harian["nkl_persen"] = harian["nkl"] / harian["npb"] * 100
    harian["nbr_persen"] = harian["nbr"] / harian["npb"] * 100
    # Beberapa baris berisi teks seperti "OFF" (toko tutup/libur) bercampur dengan angka;
    # ubah jadi angka, baris yang bukan angka jadi kosong (NaN) dan otomatis diabaikan saat dihitung.
    sl_zona["sl_persen"] = pd.to_numeric(sl_zona["sl_persen"], errors="coerce")
    tp_zona["waktu_detik"] = pd.to_numeric(tp_zona["waktu_detik"], errors="coerce")
    return harian, sl_zona, tp_zona, nkl_zona, rusak_zona, tren_rusak


with tab8:
    try:
        harian, sl_zona, tp_zona, nkl_zona, rusak_zona, tren_rusak = muat_performance_wh()
    except FileNotFoundError as e:
        st.error(f"File tidak ditemukan: {e.filename}. Taruh ke-6 file CSV performance_*/sl_*/time_pick_*/nkl_*/rusak_*/tren_* satu folder dengan app.py.")
        st.stop()

    if go is None:
        st.error("Library plotly belum terinstall (cek requirements.txt).")
        st.stop()

    BULAN_NAMA = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
                  "September", "Oktober", "November", "Desember"]
    BULAN_IDX_ASLI = 8  # Agustus

    @st.cache_data
    def buat_bulan_contoh(bulan_idx):
        """Data contoh untuk bulan selain Agustus, skalanya dikalibrasi dari rata-rata data asli Agustus."""
        rng = np.random.default_rng(2026_00 + bulan_idx)
        start = pd.Timestamp(year=2026, month=bulan_idx, day=1)
        tanggal = pd.date_range(start, start + pd.offsets.MonthEnd(0), freq="D")
        n = len(tanggal)
        base_tp, base_sl = harian["time_pick_detik"].mean(), harian["sl"].mean()
        base_npb, base_toko = harian["npb"].mean(), harian["toko"].mean()
        tren = (bulan_idx - BULAN_IDX_ASLI) * -1.2  # asumsi membaik sedikit menjelang akhir tahun
        weekend = tanggal.weekday >= 5
        toko = np.clip(rng.normal(base_toko, 6, n), 215, 265) * np.where(weekend, 0.92, 1)
        npb = np.clip(rng.normal(base_npb, base_npb * 0.07, n), base_npb * 0.5, None)
        time_pick = np.clip(rng.normal(base_tp + tren, 24, n), 140, 260)
        sl = np.clip(rng.normal(base_sl, 0.6, n), 92, 100)
        nkl = rng.normal(0, 4_800_000, n)
        nbr = np.clip(rng.normal(300_000, 190_000, n), 0, None)
        df = pd.DataFrame({"tanggal": tanggal, "toko": toko.round(), "npb": npb,
                            "time_pick_detik": time_pick, "sl": sl, "nkl": nkl, "nbr": nbr})
        df["nkl_persen"] = df["nkl"] / df["npb"] * 100
        df["nbr_persen"] = df["nbr"] / df["npb"] * 100
        return df

    opsi_bulan = ["Tren Sepanjang 2026 (semua bulan)"] + [f"{b} 2026" for b in BULAN_NAMA]
    pilih_bulan = st.selectbox("Tampilkan", opsi_bulan, index=0)

    # ===================== MODE: TREN SEPANJANG 2026 (semua bulan) =====================
    if pilih_bulan == opsi_bulan[0]:
        st.info("🟢 Agustus = **data asli** dari Excel adm reporting. Bulan lain = **data contoh** (skala mengikuti pola Agustus), untuk melihat gambaran tren sepanjang tahun sambil menunggu data bulan lain yang sesungguhnya.")
        ring = []
        for i, nama in enumerate(BULAN_NAMA, start=1):
            d = harian if i == BULAN_IDX_ASLI else buat_bulan_contoh(i)
            ring.append({"bulan": nama, "idx": i, "avg_tp": d["time_pick_detik"].mean(), "avg_sl": d["sl"].mean(),
                         "total_nkl": d["nkl"].sum(), "total_nbr": d["nbr"].sum(), "asli": i == BULAN_IDX_ASLI})
        ring = pd.DataFrame(ring)
        warna = ["#2e9e5b" if a else "#b8c0d6" for a in ring["asli"]]

        k1, k2 = st.columns(2)
        with k1:
            f1 = go.Figure(go.Bar(x=ring["bulan"], y=ring["avg_tp"], marker_color=warna,
                                   hovertemplate="%{x}: %{y:.0f} detik<extra></extra>"))
            f1.add_hline(y=105, line_dash="dash", line_color="#d62828", annotation_text="Target 1:45")
            f1.update_layout(title="Rata-rata Time Pick / Toko per Bulan (detik)", height=320, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(f1, use_container_width=True)
        with k2:
            f2 = go.Figure(go.Bar(x=ring["bulan"], y=ring["avg_sl"], marker_color=warna,
                                   hovertemplate="%{x}: %{y:.2f}%<extra></extra>"))
            f2.add_hline(y=98, line_dash="dash", line_color="#d62828", annotation_text="Target >98%")
            f2.update_layout(title="Rata-rata Service Level per Bulan (%)", height=320, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(f2, use_container_width=True)

        k3, k4 = st.columns(2)
        with k3:
            f3 = go.Figure(go.Bar(x=ring["bulan"], y=ring["total_nkl"], marker_color=warna,
                                   hovertemplate="%{x}: Rp %{y:,.0f}<extra></extra>"))
            f3.update_layout(title="Total NKL per Bulan (Rp)", height=320, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(f3, use_container_width=True)
        with k4:
            f4 = go.Figure(go.Bar(x=ring["bulan"], y=ring["total_nbr"], marker_color=warna,
                                   hovertemplate="%{x}: Rp %{y:,.0f}<extra></extra>"))
            f4.update_layout(title="Total NBR / Barang Rusak per Bulan (Rp)", height=320, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(f4, use_container_width=True)
        st.caption("🟢 hijau = data asli (Agustus) · abu-abu = data contoh (bulan lain)")

    # ===================== MODE: DETAIL SATU BULAN =====================
    else:
        bulan_idx = opsi_bulan.index(pilih_bulan)  # index di opsi_bulan == nomor bulan (opsi[0] sudah terpakai utk "semua bulan")
        asli = bulan_idx == BULAN_IDX_ASLI
        df_bulan = harian if asli else buat_bulan_contoh(bulan_idx)
        if asli:
            st.success("DATA ASLI dari Excel Monitoring DC Agustus 2026 (adm reporting).")
        else:
            st.warning(f"DATA CONTOH untuk {pilih_bulan} — belum ada file asli bulan ini, skala mengikuti pola Agustus.")

        daftar_tanggal = df_bulan["tanggal"].sort_values().dt.strftime("%d %b %Y").tolist()
        mode_tgl = st.radio("Tampilan", ["Semua Tanggal (rekap bulan ini)", "Per Tanggal"], horizontal=True, key=f"mode_{bulan_idx}")
        tgl_pilih = st.select_slider("Pilih tanggal", options=daftar_tanggal, value=daftar_tanggal[-1], key=f"tgl_{bulan_idx}") \
            if mode_tgl == "Per Tanggal" else None

        # --- rekap bulan ---
        if tgl_pilih is None:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Avg Time Pick / Toko", fmt(df_bulan["time_pick_detik"].mean()))
            c2.metric("Service Level rata-rata", f"{df_bulan['sl'].mean():.2f}%")
            c3.metric("NKL (Barang Hilang)", f"Rp {df_bulan['nkl'].sum():,.0f}")
            c4.metric("NBR (Barang Rusak)", f"Rp {df_bulan['nbr'].sum():,.0f}")

            st.subheader(f"Tren Harian — {pilih_bulan}")
            k1, k2 = st.columns(2)
            with k1:
                f1 = go.Figure(go.Scatter(x=df_bulan["tanggal"], y=df_bulan["time_pick_detik"], mode="lines+markers",
                                           line=dict(color="#3b6fe0", width=3), hovertemplate="%{x|%d %b}: %{y:.0f} detik<extra></extra>"))
                f1.add_hline(y=105, line_dash="dash", line_color="#d62828", annotation_text="Target 1:45")
                f1.update_layout(title="Avg Time Pick / Toko (detik)", height=300, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(f1, use_container_width=True)
            with k2:
                f2 = go.Figure(go.Scatter(x=df_bulan["tanggal"], y=df_bulan["sl"], mode="lines+markers",
                                           line=dict(color="#2e9e5b", width=3), hovertemplate="%{x|%d %b}: %{y:.2f}%<extra></extra>"))
                f2.add_hline(y=98, line_dash="dash", line_color="#d62828", annotation_text="Target >98%")
                f2.update_layout(title="Service Level Picking (%)", height=300, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(f2, use_container_width=True)

            k3, k4 = st.columns(2)
            with k3:
                if asli:
                    f3 = go.Figure(go.Bar(x=tren_rusak["tanggal"], y=tren_rusak["rusak_all"], marker_color="#c4201f",
                                           hovertemplate="%{x|%d %b}: Rp %{y:,.0f}<extra></extra>"))
                else:
                    f3 = go.Figure(go.Bar(x=df_bulan["tanggal"], y=df_bulan["nbr"], marker_color="#c4201f",
                                           hovertemplate="%{x|%d %b}: Rp %{y:,.0f}<extra></extra>"))
                f3.update_layout(title="Nilai Barang Rusak Harian (Rp)", height=300, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(f3, use_container_width=True)
            with k4:
                f4 = go.Figure(go.Scatter(x=df_bulan["tanggal"], y=df_bulan["nkl"], mode="lines+markers",
                                           line=dict(color="#f2b705", width=3), hovertemplate="%{x|%d %b}: Rp %{y:,.0f}<extra></extra>"))
                f4.add_hline(y=0, line_color="#8690a6")
                f4.update_layout(title="NKL Harian (Rp, minus = kehilangan)", height=300, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(f4, use_container_width=True)

            if asli:
                with st.expander("Catatan kualitas data (perlu dikonfirmasi ke adm reporting)"):
                    st.markdown(
                        "- **NKL per zona** bersumber dari sheet berjudul periode **Juli 2026**, sedangkan sheet lain berjudul Agustus 2026.\n"
                        "- **Zona '0'** pada data barang rusak per zona tidak match dengan daftar Zona 1-15.\n"
                        "- Istilah **NBR** diasumsikan = Nilai Barang Rusak, **PSP** = produktivitas pick & scan. Mohon dikoreksi jika keliru.\n"
                        "- Satu formula di sheet REKAP2 menghasilkan `#REF!` — tidak dipakai di dashboard ini."
                    )
                st.subheader("Performance per Zona (rata-rata bulan ini)")
                z1, z2 = st.columns(2)
                with z1:
                    sl_rank = sl_zona.groupby("zona")["sl_persen"].mean().sort_values()
                    f5 = go.Figure(go.Bar(x=sl_rank.values, y=sl_rank.index, orientation="h", marker_color="#2e9e5b",
                                           hovertemplate="%{y}: %{x:.2f}%<extra></extra>"))
                    f5.add_vline(x=98, line_dash="dash", line_color="#d62828")
                    f5.update_layout(title="Service Level per Zona (%) — terendah di atas", height=460, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(f5, use_container_width=True)
                with z2:
                    tp_rank = tp_zona.groupby("zona")["waktu_detik"].mean().sort_values(ascending=False)
                    f6 = go.Figure(go.Bar(x=tp_rank.values, y=tp_rank.index, orientation="h", marker_color="#3b6fe0",
                                           hovertemplate="%{y}: %{x:.0f} detik<extra></extra>"))
                    f6.update_layout(title="Rata-rata Waktu Pick per Zona (detik) — terlambat di atas", height=460, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(f6, use_container_width=True)

                z3, z4 = st.columns(2)
                with z3:
                    nz = nkl_zona.sort_values("nkl_total")
                    f7 = go.Figure(go.Bar(x=nz["nkl_total"], y="Zona " + nz["zona"].astype(str), orientation="h",
                                           marker_color=["#d62828" if v < 0 else "#2e9e5b" for v in nz["nkl_total"]],
                                           hovertemplate="%{y}: Rp %{x:,.0f}<extra></extra>"))
                    f7.update_layout(title="NKL per Zona (Rp) — periode Juli*", height=420, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(f7, use_container_width=True)
                    st.caption("*Lihat catatan kualitas data di atas: sheet sumber berjudul Juli 2026.")
                with z4:
                    rz = rusak_zona[rusak_zona["zona"] != "0"].sort_values("rusak_total")
                    f8 = go.Figure(go.Bar(x=rz["rusak_total"], y="Zona " + rz["zona"].astype(str), orientation="h", marker_color="#c4201f",
                                           hovertemplate="%{y}: Rp %{x:,.0f}<extra></extra>"))
                    f8.update_layout(title="Nilai Barang Rusak per Zona (Rp)", height=420, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(f8, use_container_width=True)
            else:
                st.caption("Detail per zona baru tersedia untuk Agustus 2026 (data asli). Bulan lain belum punya breakdown per zona.")

        # --- per tanggal ---
        else:
            tgl_ts = pd.to_datetime(tgl_pilih, format="%d %b %Y")
            b = df_bulan[df_bulan["tanggal"] == tgl_ts].iloc[0]
            st.caption(f"Menampilkan data **{tgl_pilih}** saja.")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Jumlah Toko", f"{int(b['toko'])}")
            c2.metric("Avg Time Pick", fmt(b["time_pick_detik"]))
            c3.metric("Service Level", f"{b['sl']:.2f}%")
            c4.metric("NKL Hari Ini", f"Rp {b['nkl']:,.0f}")
            c5.metric("NBR Hari Ini", f"Rp {b['nbr']:,.0f}")

            zona_aktif15 = [f"ZONA {i:02d}" for i in range(1, 16)]
            rng = np.random.default_rng(abs(hash((pilih_bulan, tgl_pilih))) % (2**32))
            if asli:
                sl_hari = sl_zona[sl_zona["tanggal"] == tgl_ts].dropna(subset=["sl_persen"]).sort_values("sl_persen")
                tp_hari = tp_zona[tp_zona["tanggal"] == tgl_ts].dropna(subset=["waktu_detik"]).sort_values("waktu_detik", ascending=False)
            else:
                sl_hari = pd.DataFrame({"zona": zona_aktif15, "sl_persen": np.clip(rng.normal(b["sl"], 1.2, 15), 85, 100)}).sort_values("sl_persen")
                tp_hari = pd.DataFrame({"zona": zona_aktif15, "waktu_detik": np.clip(rng.normal(b["time_pick_detik"], 20, 15), 100, 300)}).sort_values("waktu_detik", ascending=False)

            st.subheader(f"Performance per Zona — {tgl_pilih}")
            z1, z2 = st.columns(2)
            with z1:
                warna_sl = ["#d62828" if v < 98 else "#2e9e5b" for v in sl_hari["sl_persen"]]
                f9 = go.Figure(go.Bar(x=sl_hari["sl_persen"], y=sl_hari["zona"], orientation="h", marker_color=warna_sl,
                                       hovertemplate="%{y}: %{x:.2f}%<extra></extra>"))
                f9.add_vline(x=98, line_dash="dash", line_color="#8690a6")
                f9.update_layout(title="Service Level per Zona (%)", height=460, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(f9, use_container_width=True)
                if sl_hari.empty:
                    st.caption("Tidak ada data zona untuk tanggal ini (kemungkinan hari libur/toko tutup).")
            with z2:
                f10 = go.Figure(go.Bar(x=tp_hari["waktu_detik"], y=tp_hari["zona"], orientation="h", marker_color="#3b6fe0",
                                        hovertemplate="%{y}: %{x:.0f} detik<extra></extra>"))
                f10.update_layout(title="Waktu Pick per Zona (detik)", height=460, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(f10, use_container_width=True)

            st.warning(
                "DATA CONTOH: sebaran NKL dan barang rusak PER ZONA per hari di bawah ini masih perkiraan "
                "(dibagi rata secara acak dari total hari itu), karena master data yang ada baru rekap per bulan, "
                "belum per hari per zona." + (" Totalnya (kartu NKL/NBR di atas) tetap data asli." if asli else "")
            )
            bobot = rng.dirichlet(np.ones(15))
            contoh_nkl = pd.DataFrame({"zona": zona_aktif15, "nilai": b["nkl"] * bobot}).sort_values("nilai")
            bobot2 = rng.dirichlet(np.ones(15))
            contoh_nbr = pd.DataFrame({"zona": zona_aktif15, "nilai": b["nbr"] * bobot2}).sort_values("nilai")
            z3, z4 = st.columns(2)
            with z3:
                f11 = go.Figure(go.Bar(x=contoh_nkl["nilai"], y=contoh_nkl["zona"], orientation="h",
                                        marker_color=["#d62828" if v < 0 else "#2e9e5b" for v in contoh_nkl["nilai"]],
                                        hovertemplate="%{y}: Rp %{x:,.0f}<extra></extra>"))
                f11.update_layout(title="NKL per Zona (contoh sebaran)", height=420, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(f11, use_container_width=True)
            with z4:
                f12 = go.Figure(go.Bar(x=contoh_nbr["nilai"], y=contoh_nbr["zona"], orientation="h", marker_color="#c4201f",
                                        hovertemplate="%{y}: Rp %{x:,.0f}<extra></extra>"))
                f12.update_layout(title="Barang Rusak per Zona (contoh sebaran)", height=420, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(f12, use_container_width=True)
