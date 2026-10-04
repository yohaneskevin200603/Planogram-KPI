import os
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

try:
    import plotly.graph_objects as go
except ImportError:
    go = None

st.set_page_config(page_title="Monitoring Picking DPD", layout="wide")

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

tab4, tab6, tab5, tab1, tab2, tab3 = st.tabs(
    ["Monitoring Hari Ini", "Riwayat dan Tren", "Layout 3D", "Cari Item", "Lihat per LINE", "Ringkasan"]
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


def rangka_rak(x0, x1, ya, yb, h, level, n, n_stor):
    """Gambar n baris rak: tiang biru, balok merah (tingkat storage, bawah) dan balok hijau (tingkat display, atas)."""
    y0, y1 = min(ya, yb), max(ya, yb)
    sejajar_y = (x1 - x0) <= 40  # rak memanjang ke arah y kalau kotaknya sempit
    s0, s1, l0, l1 = (x0, x1, y0, y1) if sejajar_y else (y0, y1, x0, x1)
    w = min(1.2, (s1 - s0) / n * 0.6)
    pusat = [s0 + (i + 0.5) * (s1 - s0) / n for i in range(n)]
    tiang_l = np.linspace(l0, l1, max(2, int((l1 - l0) / 8) + 1))

    def xy(s, l):
        return (s, l) if sejajar_y else (l, s)

    merah = ([], [], [])
    hijau = ([], [], [])
    tx, ty, tz = [], [], []
    for c in pusat:
        for e in (c - w / 2, c + w / 2):
            for k in range(1, level + 1):  # tingkat 1 = paling bawah
                tujuan = merah if k <= n_stor else hijau
                for l in (l0, l1):
                    x, y = xy(e, l)
                    tujuan[0].append(x); tujuan[1].append(y); tujuan[2].append(h * k / level)
                for arah in tujuan:
                    arah.append(None)
            for l in tiang_l:
                x, y = xy(e, l)
                tx += [x, x, None]; ty += [y, y, None]; tz += [0, h, None]

    def garis(data, warna, lebar):
        return go.Scatter3d(x=data[0], y=data[1], z=data[2], mode="lines",
                            line=dict(color=warna, width=lebar), hoverinfo="skip", showlegend=False)

    return [garis(merah, "#d62828", 3), garis(hijau, "#00c853", 6), garis((tx, ty, tz), "#1f4fd8", 4)]


with tab5:
    if go is None:
        st.error("Library plotly belum terinstall. Di Terminal ketik: python -m pip install plotly, lalu jalankan ulang.")
        st.stop()
    st.caption("Putar dengan mouse (klik-tahan), zoom dengan scroll. Balok merah = tingkat storage: SHELF 1-2, khusus Zona 06 SHELF 1-3. Balok hijau = tingkat display (picking) di atasnya, sesuai isi file CSV. Jumlah baris rak diambil dari jumlah LINE di data. "
               "Posisi sudah disesuaikan dengan koreksi; ukuran Zona 12 dan 13 masih perkiraan.")
    mode = st.radio("Warna blok", ["Warna asli zona", "Status waktu picking (data contoh)"], horizontal=True)
    tinggi = display.groupby("ZONA")["SHELF"].max()
    dpd_all, _ = buat_data_contoh()
    rata_zona = dpd_all.groupby("ZONA")["DURASI"].mean()

    jml_line = display.groupby("ZONA")["LINE"].nunique()
    fig = go.Figure()
    for nama, daftar_kotak in DENAH.items():
        h = 9 * 12  # 9 tingkat rak
        n_stor = 9 if nama == "Rak kosong" else (3 if nama == "Zona 06" else 2)  # jumlah tingkat storage dari bawah
        info = f"{nama}: {JENIS_ZONA.get(nama, 'belum dipakai')}"
        warna = WARNA_ZONA.get(nama, "#555555")
        if mode.startswith("Status"):
            if nama in rata_zona:
                lewat = rata_zona[nama] > TARGET_DETIK
                warna = "#e63946" if lewat else "#2ecc71"
                info += f"<br>Rata-rata waktu {fmt(rata_zona[nama])} ({'LEWAT' if lewat else 'OK'} target)"
            else:
                warna = "#bbbbbb"
        label = nama[-2:] if nama.startswith("Zona") else "kosong"
        for xa, xb, ya, yb in daftar_kotak:
            # sumbu y dibalik supaya bagian atas gambar layout = bagian belakang di 3D
            X0, X1, Y0, Y1 = xa / 10, xb / 10, (1130 - ya) / 10, (1130 - yb) / 10
            n_rak = max(1, round(int(jml_line.get(nama, 4)) / len(daftar_kotak)))
            fig.add_trace(kotak_3d(X0, X1, Y0, Y1, h / 10, warna, info, 0.12))  # volume transparan (warna zona + hover)
            fig.add_trace(kotak_3d(X0, X1, Y0, Y1, 0.3, warna, info, 0.9))      # lantai berwarna
            for tr in rangka_rak(X0, X1, Y0, Y1, h / 10, 9, n_rak, n_stor):
                fig.add_trace(tr)
            # label ditaruh tepat di permukaan atas blok
            fig.add_trace(go.Scatter3d(
                x=[(xa + xb) / 20], y=[(2260 - ya - yb) / 20], z=[h / 10 + 0.3], mode="text",
                text=[label], textfont=dict(size=14, color="white"), hoverinfo="skip", showlegend=False,
            ))
    fig.update_layout(
        height=650, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
        scene=dict(aspectmode="data", xaxis_visible=False, yaxis_visible=False, zaxis_visible=False,
                   camera=dict(eye=dict(x=0.0, y=-1.4, z=1.1))),
    )
    st.plotly_chart(fig, use_container_width=True)


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