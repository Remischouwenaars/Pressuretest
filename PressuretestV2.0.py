# PressuretestV3.1.py
import os, hashlib
from io import BytesIO
from datetime import datetime, date, time, timedelta

import streamlit as st
from PIL import Image as PILImage, ExifTags
from streamlit_drawable_canvas import st_canvas

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage

# ======================
# TRANSLATIONS
# ======================
T = {
    "nl": {
        "title":"Druktest rapport","language":"Taal","project_info":"Projectgegevens",
        "project_name":"Projectnaam","manufacturer":"Fabrikant","work_order":"Werkorder / Inkooporder",
        "drawing":"Tekening","revision":"Revisie","part_line":"Onderdeelnaam / Lijnsectie",
        "requirements":"Test requirements","pt":"Testdruk (Pt)","pt_unit":"Eenheid","notes":"Opmerkingen",

        # Per compartiment timing (geen overall timing meer)
        "comp_duration":"Testduur compartiment",

        "equip":"Registratie testapparatuur","compartments":"Compartiment / sectie","num_comp":"Aantal compartimenten",
        "date":"Datum","start_time":"Start tijd","start_pressure":"Start druk","end_time":"Eindtijd","end_pressure":"Eind druk",
        "result":"Resultaat","remarks":"Opmerking","pass":"PASS","fail":"FAIL",

        "photos":"Foto's per compartiment","start_photo":"Foto begin","end_photo":"Foto eind","timestamp":"Tijd",
        "exif_missing":"EXIF ontbreekt – timestamp = uploadmoment",
        "use_camera":"Gebruik camera voor","slot_start":"Start","slot_end":"Eind",
        "selected_target":"Camera doel","selected_none":"(geen)",

        "signature":"Handtekening","draw_signature":"Teken handtekening","sign_name":"Naam","sign_company":"Bedrijf","sign_date":"Datum ondertekening",

        "actions":"Acties","gen_pdf":"Genereer PDF","dl_pdf":"Download PDF","reset":"Formulier leegmaken",
        "success_pdf":"PDF is gegenereerd.","need_all":"Vul alle verplichte velden in.",

        "unit_bar_g":"bar(g)","unit_psi_g":"PSI(g)"
    },
    "en": {
        "title":"Pressure test report","language":"Language","project_info":"Project information",
        "project_name":"Project name","manufacturer":"Manufacturer","work_order":"Work order / Purchase order",
        "drawing":"Drawing","revision":"Revision","part_line":"Part name / Line section",
        "requirements":"Test requirements","pt":"Test pressure (Pt)","pt_unit":"Unit","notes":"Remarks",

        "comp_duration":"Compartment test duration",

        "equip":"Registration test equipment","compartments":"Compartment / section","num_comp":"Number of compartments",
        "date":"Date","start_time":"Start time","start_pressure":"Start pressure","end_time":"End time","end_pressure":"End pressure",
        "result":"Result","remarks":"Remarks","pass":"PASS","fail":"FAIL",

        "photos":"Photos per compartment","start_photo":"Start photo","end_photo":"End photo","timestamp":"Time",
        "exif_missing":"EXIF missing – timestamp = upload moment",
        "use_camera":"Use camera for","slot_start":"Start","slot_end":"End",
        "selected_target":"Camera target","selected_none":"(none)",

        "signature":"Signature","draw_signature":"Draw signature","sign_name":"Name","sign_company":"Company","sign_date":"Signature date",

        "actions":"Actions","gen_pdf":"Generate PDF","dl_pdf":"Download PDF","reset":"Clear form",
        "success_pdf":"PDF generated.","need_all":"Please complete all required fields.",

        "unit_bar_g":"bar(g)","unit_psi_g":"PSI(g)"
    }
}

# ======================
# HELPERS
# ======================
PSI_PER_BAR = 14.5037738
def bar_to_psi(v): return None if v is None else v * PSI_PER_BAR
def psi_to_bar(v): return None if v is None else v / PSI_PER_BAR
def fmt_duration(td, lang):
    # td is a timedelta
    total_min = int(round(td.total_seconds() / 60.0))
    h, m = divmod(total_min, 60)
    return f"{h} uur {m} min" if lang=="nl" else f"{h} h {m} min"

def exif_datetime(img: PILImage.Image):
    try:
        exif = img.getexif()
        if not exif: return None
        tags = {ExifTags.TAGS.get(k,k):v for k,v in exif.items()}
        s = tags.get("DateTimeOriginal") or tags.get("DateTime")
        if not s: return None
        s = s.replace(":", "-", 2)
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def bytes_to_pil(b): return None if not b else PILImage.open(BytesIO(b)).convert("RGB")
def canvas_to_pil(canvas_image_data):
    if canvas_image_data is None: return None
    import numpy as np
    return PILImage.fromarray(canvas_image_data.astype("uint8")).convert("RGB")

def _pil_to_rlimage(pil_img, max_w_px=420):
    """Scale PIL image to fit within max_w_px; keep aspect; return ReportLab RLImage."""
    w,h = pil_img.size
    scale = min(max_w_px / float(w), 1.0)
    if scale < 1.0:
        pil_img = pil_img.resize((int(w*scale), int(h*scale)))
    bio = BytesIO(); pil_img.save(bio, format="PNG"); bio.seek(0)
    # width/height are in pixels; ReportLab will map using dpi ~72; passing explicit width/height keeps pixel dims
    return RLImage(bio, width=pil_img.size[0], height=pil_img.size[1])

# ======================
# PDF BUILDER (always English)
# ======================
def build_pdf_bytes(data, logo_path=None):
    L = "en"
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30
    )
    styles = getSampleStyleSheet()
    story = []

    # Header
    if logo_path and os.path.exists(logo_path):
        story += [RLImage(logo_path, width=120, height=40), Spacer(1, 6)]
    story += [Paragraph(f"<b>{T[L]['title']}</b>", styles["Title"]), Spacer(1, 10)]

    # Meta
    meta = data["meta"]
    meta_rows = [
        [T[L]["project_name"], meta["project_name"]],
        [T[L]["manufacturer"], meta["manufacturer"]],
        [T[L]["work_order"], meta["work_order"]],
        [T[L]["drawing"], meta["drawing"]],
        [T[L]["revision"], meta["revision"]],
        [T[L]["part_line"], meta["part_line"]],
    ]
    meta_tbl = Table(meta_rows, colWidths=[160, 360])
    meta_tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.6,colors.black),
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.black),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BACKGROUND",(0,0),(-1,0),colors.whitesmoke),
    ]))
    story += [meta_tbl, Spacer(1, 10)]

    # Requirements
    req = data["requirements"]
    pt_bar = req["pt_value"] if req["pt_unit"]=="bar" else psi_to_bar(req["pt_value"])
    pt_psi = req["pt_value"] if req["pt_unit"]=="psi" else bar_to_psi(req["pt_value"])
    req_rows = [
        [T[L]["pt"], f"{pt_bar:.2f} {T[L]['unit_bar_g']} / {pt_psi:.2f} {T[L]['unit_psi_g']}"],
        [T[L]["notes"], req["notes"]],
    ]
    req_tbl = Table(req_rows, colWidths=[200, 320])
    req_tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.6,colors.black),
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.black),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BACKGROUND",(0,0),(-1,0),colors.whitesmoke),
    ]))
    story += [Paragraph("<b>Test requirements</b>", styles["Heading3"]), req_tbl, Spacer(1, 10)]

    # Registration table (pressures/results/remarks)
    comps = data["compartments"]
    n = len(comps)
    header = [""] + [str(i+1) for i in range(n)]
    table = [header]
    labels = ["Date","Start time","Start pressure (bar/PSI)","End time","End pressure (bar/PSI)","Result","Remarks"]
    def v(key): return [c.get(key,"") for c in comps]
    fp = lambda x: "" if x is None else f"{x:.2f}"
    table += [
        [labels[0]] + v("date_str"),
        [labels[1]] + v("start_time_str"),
        [labels[2]] + [f"{fp(c.get('start_bar'))}/{fp(c.get('start_psi'))}" for c in comps],
        [labels[3]] + v("end_time_str"),
        [labels[4]] + [f"{fp(c.get('end_bar'))}/{fp(c.get('end_psi'))}" for c in comps],
        [labels[5]] + v("result"),
        [labels[6]] + v("remarks"),
    ]
    colW = [200] + [(320/n) for _ in range(n)]
    tbl = Table(table, colWidths=colW, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.6,colors.black),
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.black),
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story += [Paragraph("<b>Registration test equipment</b>", styles["Heading3"]), tbl, Spacer(1, 10)]

    # Photos per compartment: Start (caption) then End (caption + duration)
    story += [Paragraph("<b>Photos per compartment</b>", styles["Heading3"]), Spacer(1, 6)]
    for i, c in enumerate(comps):
        story += [Paragraph(f"<b>Compartment {i+1}</b>", styles["Heading4"])]
        for tp in ["start","end"]:
            photo = c["photos"].get(tp)
            if not photo: 
                continue
            story += [
                _pil_to_rlimage(photo["img"], max_w_px=420),
                Paragraph(
                    f"{tp.capitalize()} time: {photo['ts'].strftime('%Y-%m-%d %H:%M')}"
                    + (f" – {T[L]['exif_missing']}" if photo.get("no_exif") else ""),
                    styles["Normal"]
                ),
                Spacer(1, 6)
            ]
            if tp == "end":
                # Show compartment test duration in bold, if start ts exists
                start_ph = c["photos"].get("start")
                if start_ph:
                    dur = photo["ts"] - start_ph["ts"]
                    dur_txt = fmt_duration(dur, "en")
                    story += [Paragraph(f"<b>{T[L]['comp_duration']}: {dur_txt}</b>", styles["Normal"]), Spacer(1, 10)]

    # Signature
    sig = data["signature"]
    story += [Paragraph("<b>Signature</b>", styles["Heading3"])]
    if sig.get("image_pil"):
        story += [_pil_to_rlimage(sig["image_pil"], max_w_px=600), Spacer(1, 6)]
    sig_rows = [["Name", sig["name"]], ["Company", sig["company"]], ["Date", sig["date_str"]]]
    sig_tbl = Table(sig_rows, colWidths=[160, 360])
    sig_tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.6,colors.black),
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.black),
    ]))
    story += [sig_tbl]

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf

# ======================
# STREAMLIT APP
# ======================
st.set_page_config(page_title="Druktest rapport", page_icon="🧪", layout="centered")

# Branding (optioneel, eenvoudig)
st.markdown("""
<style>
  .stApp { background-color: #F18500; }
  .block-container { background: #ffffff; padding: 2rem; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
</style>
""", unsafe_allow_html=True)

# State init
if "comp_count" not in st.session_state: st.session_state.comp_count = 1
if "comp_data" not in st.session_state: st.session_state.comp_data = [{"photos":{"start":None,"end":None}} for _ in range(st.session_state.comp_count)]
# Single camera target: {"idx": int, "slot": "start"|"end"} or None
if "camera_target" not in st.session_state: st.session_state.camera_target = None

# Language
lang = st.sidebar.selectbox("Language / Taal", ["nl","en"], index=0)
_ = T[lang]
st.title(_["title"])

# META
st.subheader(_["project_info"])
m1,m2 = st.columns(2)
project_name = m1.text_input(_["project_name"], "")
manufacturer = m2.text_input(_["manufacturer"], "")
work_order = st.text_input(_["work_order"], "")
drawing = st.text_input(_["drawing"], "")
revision = st.text_input(_["revision"], "")
part_line = st.text_input(_["part_line"], "")

# REQUIREMENTS
st.markdown(f"### {_['requirements']}")
r1,r2 = st.columns(2)
pt_value = r1.number_input(_["pt"], min_value=0.0, step=0.1, format="%.2f")
pt_unit_choice = r2.selectbox(_["pt_unit"], ["bar","psi"], index=0, format_func=lambda x: _["unit_bar_g"] if x=="bar" else _["unit_psi_g"])
notes = st.text_area(_["notes"], "")

# COMPARTMENTS (counts)
st.markdown(f"### {_['equip']}")
comp_count = st.selectbox(_["num_comp"], [1,2,3,4], index=st.session_state.comp_count-1)
if comp_count != st.session_state.comp_count:
    st.session_state.comp_count = comp_count
    st.session_state.comp_data = [{"photos":{"start":None,"end":None}} for _ in range(comp_count)]

# Per compartment inputs (pressures/times/results) + photos
labels = [_["date"],_["start_time"],_["start_pressure"],_["end_time"],_["end_pressure"],_["result"],_["remarks"]]
comps = []
for i in range(st.session_state.comp_count):
    with st.expander(f"{_['compartments']} {i+1}", expanded=True):
        cA,cB = st.columns(2)
        cd = cA.date_input(labels[0], value=date.today(), key=f"c{i}_date")
        cst = cA.time_input(labels[1], value=time(9,0), key=f"c{i}_st")
        cet = cA.time_input(labels[3], value=time(10,0), key=f"c{i}_et")
        csp = cB.number_input(labels[2] + f" ({_['unit_bar_g']})", min_value=0.0, step=0.1, format="%.2f", key=f"c{i}_sp")
        cep = cB.number_input(labels[4] + f" ({_['unit_bar_g']})", min_value=0.0, step=0.1, format="%.2f", key=f"c{i}_ep")
        res = st.radio(labels[5], options=["", _["pass"], _["fail"]], index=0, horizontal=True, key=f"c{i}_res")
        rem = st.text_input(labels[6], "", key=f"c{i}_rem")

        # --- Photos per slot (Start / End) ---
        for slot in ["start","end"]:
            st.markdown(f"**{_['compartments']} {i+1} – {_[slot+'_photo']}**")

            # Buttons: choose this slot for the single camera, or upload file
            bcol1, bcol2 = st.columns([1,1])
            with bcol1:
                if st.button(f"{_['use_camera']} ({_['slot_start'] if slot=='start' else _['slot_end']})", key=f"c{i}_{slot}_usecam"):
                    st.session_state.camera_target = {"idx": i, "slot": slot}
            with bcol2:
                up = st.file_uploader("", type=["png","jpg","jpeg"], key=f"c{i}_{slot}_up")
                if up is not None:
                    img = bytes_to_pil(up.getvalue())
                    dt = exif_datetime(img)
                    if dt:
                        ts = dt; no_exif = False
                    else:
                        ts = datetime.now().replace(second=0, microsecond=0)
                        no_exif = True
                        st.warning(_["exif_missing"])
                    st.session_state.comp_data[i]["photos"][slot] = {"img": img, "ts": ts, "no_exif": no_exif}

            # Single preview (with timestamp)
            photo = st.session_state.comp_data[i]["photos"][slot]
            if photo:
                st.image(
                    photo["img"],
                    caption=f"{_['timestamp']}: {photo['ts'].strftime('%Y-%m-%d %H:%M')}" + ("  ⚠" if photo.get("no_exif") else ""),
                    use_container_width=True
                )

        # Append comp data
        comps.append({
            "date": cd, "date_str": cd.strftime("%Y-%m-%d"),
            "start_time": cst, "start_time_str": cst.strftime("%H:%M"),
            "end_time": cet, "end_time_str": cet.strftime("%H:%M"),
            "start_bar": float(csp) if csp is not None else None, "start_psi": bar_to_psi(float(csp) if csp is not None else None),
            "end_bar": float(cep) if cep is not None else None, "end_psi": bar_to_psi(float(cep) if cep is not None else None),
            "result": res, "remarks": rem,
            "photos": st.session_state.comp_data[i]["photos"]
        })

# --- SINGLE CAMERA (one stream only) ---
st.divider()
cam_hdr = st.columns([1,2,2])
cam_hdr[0].write(f"🎥 {_[ 'use_camera' ]}")
target = st.session_state.camera_target
cam_hdr[1].write(f"{_['selected_target']}: " + (f"{_['compartments']} {target['idx']+1} – {_[ 'slot_start' if target and target.get('slot')=='start' else 'slot_end' ]}" if target else _['selected_none']))

# Only show camera if a target is selected
if target:
    cam = st.camera_input("")
    if cam is not None:
        img = bytes_to_pil(cam.getvalue())
        ts = datetime.now().replace(second=0, microsecond=0)
        st.session_state.comp_data[target["idx"]]["photos"][target["slot"]] = {"img": img, "ts": ts, "no_exif": False}
        st.session_state.camera_target = None
        st.success("Photo captured and assigned.")

# SIGNATURE
st.markdown(f"### {_['signature']}")
sg1, sg2 = st.columns([2,1])
with sg1:
    st.write(_["draw_signature"])
    canv = st_canvas(
        fill_color="rgba(0,0,0,0)", stroke_width=2, stroke_color="#000000",
        background_color="#FFFFFF", update_streamlit=True, height=170,
        drawing_mode="freedraw", key="sig_canvas"
    )
    sig_img = canvas_to_pil(canv.image_data) if canv is not None else None
with sg2:
    sign_name = st.text_input(_["sign_name"], "")
    sign_company = st.text_input(_["sign_company"], "")
    sign_date = st.date_input(_["sign_date"], value=date.today())

# ACTIONS
st.markdown(f"### {_['actions']}")
b1,b2 = st.columns(2)
gen = b1.button(_["gen_pdf"], type="primary")
reset = b2.button(_["reset"])
if reset:
    st.session_state.clear()
    st.experimental_rerun()

# VALIDATION & PDF
def _meta_ok():
    return all([project_name.strip(), manufacturer.strip(), work_order.strip(), drawing.strip(), revision.strip(), part_line.strip()])
def _req_ok():
    return pt_value is not None and pt_value > 0.0 and pt_unit_choice in ("bar","psi")
def _comps_ok():
    for i,c in enumerate(comps):
        # require pressures and result + both photos
        if (c["start_bar"] is None) or (c["end_bar"] is None) or (c["result"] not in (_["pass"], _["fail"])):
            return False
        if not (c["photos"].get("start") and c["photos"].get("end")):
            return False
    return True
def _sig_ok():
    return bool(sign_name.strip()) and bool(sign_company.strip()) and bool(sign_date) and (sig_img is not None)

pdf_bytes = None
if gen:
    missing = []
    if not _meta_ok(): missing.append(_["project_info"])
    if not _req_ok(): missing.append(_["requirements"])
    if not _comps_ok(): missing.append(_["equip"] + " / " + _["photos"])
    if not _sig_ok(): missing.append(_["signature"])

    if missing:
        st.error(_["need_all"])
        st.info("Missing: " + ", ".join(missing))
    else:
        meta = {"project_name":project_name,"manufacturer":manufacturer,"work_order":work_order,"drawing":drawing,"revision":revision,"part_line":part_line}
        req = {"pt_value":float(pt_value),"pt_unit":pt_unit_choice,"notes":notes}
        signature = {"name":sign_name,"company":sign_company,"date":sign_date,"date_str":sign_date.strftime("%Y-%m-%d"),"image_pil":sig_img}

        pdf_data = {"meta":meta,"requirements":req,"compartments":comps,"signature":signature}
        logo_path = os.path.join("assets","logo.png") if os.path.exists(os.path.join("assets","logo.png")) else None
        pdf_bytes = build_pdf_bytes(pdf_data, logo_path=logo_path)
        st.success(_["success_pdf"])

if pdf_bytes:
    fname = f"{datetime.now().strftime('%Y-%m-%d')}_{(project_name or 'Project').replace(' ','_')}_Report.pdf"
    st.download_button(_["dl_pdf"], data=pdf_bytes, file_name=fname, mime="application/pdf")
