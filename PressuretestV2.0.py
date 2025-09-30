# app.py — Pressure Test Report (UI NL/EN, PDF altijd EN)
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

T = {
    "nl": {
        "title":"Druktest rapport","language":"Taal","project_info":"Projectgegevens",
        "project_name":"Projectnaam","manufacturer":"Fabrikant","work_order":"Werkorder / Inkooporder",
        "drawing":"Tekening","part_line":"Onderdeelnaam / Lijnsectie",
        "requirements":"Test requirements","pt":"Testdruk (Pt)","pt_unit":"Eenheid","notes":"Opmerkingen",
        "timing":"Timing druktest","start_dt":"Start datum & tijd","end_dt":"Eind datum & tijd","plus1h":"+1 uur","duration":"Testduur",
        "equip":"Registratie testapparatuur","compartments":"Compartiment / sectie","num_comp":"Aantal compartimenten",
        "date":"Datum","start_time":"Start tijd","start_pressure":"Start druk","end_time":"Eindtijd","end_pressure":"Eind druk",
        "result":"Resultaat","remarks":"Opmerking","pass":"PASS","fail":"FAIL",
        "photos":"Foto's druktest (verplicht)","start_photo":"Foto begin","end_photo":"Foto eind","timestamp":"Tijd",
        "signature":"Handtekening","draw_signature":"Teken handtekening","sign_name":"Naam","sign_company":"Bedrijf","sign_date":"Datum ondertekening",
        "actions":"Acties","gen_pdf":"Genereer PDF","dl_pdf":"Download PDF","reset":"Formulier leegmaken",
        "success_pdf":"PDF is gegenereerd.","need_photos":"Vul zowel Foto begin als Foto eind in.",
        "end_before_start":"Eindtijd ligt vóór starttijd. Pas dit aan.",
        "need_all":"Vul alle verplichte velden in (bovenaan, compartimenten, foto's en handtekening).",
        "unit_bar_g":"bar(g)","unit_psi_g":"PSI(g)"
    },
    "en": {
        "title":"Pressure test report","language":"Language","project_info":"Project information",
        "project_name":"Project name","manufacturer":"Manufacturer","work_order":"Work order / Purchase order",
        "drawing":"Drawing","part_line":"Part name / Line section",
        "requirements":"Test requirements","pt":"Test pressure (Pt)","pt_unit":"Unit","notes":"Remarks",
        "timing":"Pressure test timing","start_dt":"Start date & time","end_dt":"End date & time","plus1h":"+1 hour","duration":"Test duration",
        "equip":"Registration test equipment","compartments":"Compartment / section","num_comp":"Number of compartments",
        "date":"Date","start_time":"Start time","start_pressure":"Start pressure","end_time":"End time","end_pressure":"End pressure",
        "result":"Result","remarks":"Remarks","pass":"PASS","fail":"FAIL",
        "photos":"Pressure test photos (required)","start_photo":"Start photo","end_photo":"End photo","timestamp":"Time",
        "signature":"Signature","draw_signature":"Draw signature","sign_name":"Name","sign_company":"Company","sign_date":"Signature date",
        "actions":"Actions","gen_pdf":"Generate PDF","dl_pdf":"Download PDF","reset":"Clear form",
        "success_pdf":"PDF generated.","need_photos":"Please provide both Start and End photos.",
        "end_before_start":"End time is before start time. Please adjust.",
        "need_all":"Please complete all required fields (top section, compartments, photos and signature).",
        "unit_bar_g":"bar(g)","unit_psi_g":"PSI(g)"
    }
}

PSI_PER_BAR = 14.5037738
def bar_to_psi(v): return None if v is None else v * PSI_PER_BAR
def psi_to_bar(v): return None if v is None else v / PSI_PER_BAR
def fmt_duration(td, lang): 
    m = int(td.total_seconds()//60); h, m = divmod(m, 60)
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
    except Exception: return None
def pil_to_bytes(img): bio=BytesIO(); img.save(bio, format="PNG"); return bio.getvalue()
def bytes_to_pil(b): return None if not b else PILImage.open(BytesIO(b)).convert("RGB")
def md5(b): return None if not b else hashlib.md5(b).hexdigest()
def canvas_to_pil(canvas_image_data):
    if canvas_image_data is None: return None
    import numpy as np
    return PILImage.fromarray(canvas_image_data.astype("uint8")).convert("RGB")
def _pil_to_rlimage(pil_img, max_w_px=1050):
    w,h = pil_img.size; s = min(max_w_px/w, 1.0)
    if s<1: pil_img = pil_img.resize((int(w*s), int(h*s)))
    bio=BytesIO(); pil_img.save(bio, format="PNG"); bio.seek(0)
    return RLImage(bio, width=pil_img.size[0], height=pil_img.size[1])

def build_pdf_bytes(data, logo_path=None):
    L = "en"
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet(); story=[]
    if logo_path and os.path.exists(logo_path):
        story += [RLImage(logo_path, width=120, height=40), Spacer(1,6)]
    story += [Paragraph(f"<b>{T[L]['title']}</b>", styles["Title"]), Spacer(1,8)]

    meta = data["meta"]
    meta_rows = [
        [T[L]["project_name"], meta.get("project_name","")],
        [T[L]["manufacturer"], meta.get("manufacturer","")],
        [T[L]["work_order"], meta.get("work_order","")],
        [T[L]["drawing"], meta.get("drawing","")],
        [T[L]["part_line"], meta.get("part_line","")],
    ]
    tbl = Table(meta_rows, colWidths=[160,360]); tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.5,colors.black),("INNERGRID",(0,0),(-1,-1),0.25,colors.black),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BACKGROUND",(0,0),(-1,0),colors.whitesmoke),
    ]))
    story += [tbl, Spacer(1,8)]

    story += [Paragraph(f"<b>{T[L]['requirements']}</b>", styles["Heading3"]), Spacer(1,2)]
    req = data["requirements"]
    if req["pt_unit"]=="bar":
        pt_bar=req["pt_value"]; pt_psi=bar_to_psi(pt_bar) if pt_bar is not None else None
    else:
        pt_psi=req["pt_value"]; pt_bar=psi_to_bar(pt_psi) if pt_psi is not None else None
    req_rows = [
        [T[L]["pt"], f"{'' if pt_bar is None else f'{pt_bar:.2f}'} {T[L]['unit_bar_g']} / {'' if pt_psi is None else f'{pt_psi:.2f}'} {T[L]['unit_psi_g']}"],
        [T[L]["notes"], req.get("notes","")]
    ]
    tbl = Table(req_rows, colWidths=[200,320]); tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.5,colors.black),("INNERGRID",(0,0),(-1,-1),0.25,colors.black),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BACKGROUND",(0,0),(-1,0),colors.whitesmoke),
    ]))
    story += [tbl, Spacer(1,8)]

    story += [Paragraph(f"<b>{T[L]['equip']}</b>", styles["Heading3"]), Spacer(1,2)]
    comps = data["compartments"]; n=len(comps)
    header=[""]+[str(i+1) for i in range(n)]; table=[header]
    labels=[T[L]["date"],T[L]["start_time"],
            f"{T[L]['start_pressure']} ({T[L]['unit_bar_g']}/{T[L]['unit_psi_g']})",
            T[L]["end_time"],f"{T[L]['end_pressure']} ({T[L]['unit_bar_g']}/{T[L]['unit_psi_g']})",
            T[L]["result"],"Deviation (bar/h / PSI/h)",T[L]["remarks"]]
    def v(key): return [c.get(key,"") for c in comps]
    fp=lambda x: "" if x is None else f"{x:.2f}"
    table += [
        [labels[0]]+v("date_str"),
        [labels[1]]+v("start_time_str"),
        [labels[2]]+[f"{fp(c.get('start_bar'))}/{fp(c.get('start_psi'))}" for c in comps],
        [labels[3]]+v("end_time_str"),
        [labels[4]]+[f"{fp(c.get('end_bar'))}/{fp(c.get('end_psi'))}" for c in comps],
        [labels[5]]+v("result"),
        [labels[6]]+[f"{fp(c.get('dev_bar_h'))}/{fp(c.get('dev_psi_h'))}" for c in comps],
        [labels[7]]+v("remarks"),
    ]
    colW=[200]+[(320/n) for _ in range(n)]
    tbl = Table(table, colWidths=colW, repeatRows=1); tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.5,colors.black),("INNERGRID",(0,0),(-1,-1),0.25,colors.black),
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story += [tbl, Spacer(1,8)]

    story += [Paragraph(f"<b>{T[L]['photos']}</b>", styles["Heading3"]), Spacer(1,2)]
    story += [_pil_to_rlimage(data["photos"]["start_pil"]),
              Paragraph(f"{T[L]['start_photo']}: {data['timing']['start_str']}", styles["Normal"]),
              Spacer(1,6),
              _pil_to_rlimage(data["photos"]["end_pil"]),
              Paragraph(f"{T[L]['end_photo']}: {data['timing']['end_str']} — {T[L]['duration']}: {data['timing']['duration_str']}", styles["Normal"]),
              Spacer(1,8)]

    story += [Paragraph(f"<b>{T[L]['signature']}</b>", styles["Heading3"]), Spacer(1,2)]
    sig = data["signature"]
    if sig.get("image_pil"):
        story += [_pil_to_rlimage(sig["image_pil"], max_w_px=600), Spacer(1,4)]
    sig_rows=[[T[L]["sign_name"],sig.get("name","")],[T[L]["sign_company"],sig.get("company","")],[T[L]["sign_date"],sig.get("date_str","")]]
    tbl = Table(sig_rows, colWidths=[160,360]); tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.5,colors.black),("INNERGRID",(0,0),(-1,-1),0.25,colors.black),
        ("BACKGROUND",(0,0),(-1,0),colors.whitesmoke),
    ]))
    story += [tbl]
    doc.build(story); pdf=buf.getvalue(); buf.close(); return pdf

st.set_page_config(page_title="Druktest rapport", page_icon="🧪", layout="centered")
st.markdown("""
<style>
  .stApp { background-color: #F18500; }
  .block-container { background: #ffffff; padding: 2rem; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
</style>
""", unsafe_allow_html=True)

# state
if "comp_count" not in st.session_state: st.session_state.comp_count=1
if "rows" not in st.session_state: st.session_state.rows=[{} for _ in range(st.session_state.comp_count)]
if "g_start_date" not in st.session_state: st.session_state.g_start_date=date.today()
if "g_start_time" not in st.session_state: st.session_state.g_start_time=time(9,0)
if "g_end_date" not in st.session_state: st.session_state.g_end_date=date.today()
if "g_end_time" not in st.session_state: st.session_state.g_end_time=time(10,0)
for k in ["start_photo_bytes","end_photo_bytes","start_photo_hash","end_photo_hash"]:
    if k not in st.session_state: st.session_state[k]=None

lang = st.sidebar.selectbox("Language / Taal", ["nl","en"], index=0); _=T[lang]
st.title(_["title"])

# ---- Photos (zetten timestamps) ----
st.markdown(f"### {_['photos']}")
c1,c2 = st.columns(2)
start_photo = bytes_to_pil(st.session_state.start_photo_bytes)
end_photo   = bytes_to_pil(st.session_state.end_photo_bytes)

with c1:
    st.markdown(f"**{_['start_photo']}**")
    cam = st.camera_input("", key="cam_start")
    up  = st.file_uploader("", type=["png","jpg","jpeg"], key="up_start")
    if cam is not None:
        b=cam.getvalue(); h=md5(b)
        if h and h!=st.session_state.start_photo_hash:
            st.session_state.start_photo_bytes=b; st.session_state.start_photo_hash=h
            now=datetime.now().replace(second=0,microsecond=0)
            st.session_state.g_start_date, st.session_state.g_start_time = now.date(), now.time()
            start_photo = bytes_to_pil(b)
    if up is not None:
        b=up.getvalue(); h=md5(b)
        if h and h!=st.session_state.start_photo_hash:
            st.session_state.start_photo_bytes=b; st.session_state.start_photo_hash=h
            img=bytes_to_pil(b); dt=exif_datetime(img)
            if dt: st.session_state.g_start_date, st.session_state.g_start_time = dt.date(), dt.time().replace(second=0,microsecond=0)
            else:
                now=datetime.now().replace(second=0,microsecond=0)
                st.session_state.g_start_date, st.session_state.g_start_time = now.date(), now.time()
            start_photo=img
    if start_photo:
        st.image(start_photo, caption=f"{_['timestamp']}: {st.session_state.g_start_date} {st.session_state.g_start_time.strftime('%H:%M')}", use_container_width=True)

with c2:
    st.markdown(f"**{_['end_photo']}**")
    cam = st.camera_input("", key="cam_end")
    up  = st.file_uploader("", type=["png","jpg","jpeg"], key="up_end")
    if cam is not None:
        b=cam.getvalue(); h=md5(b)
        if h and h!=st.session_state.end_photo_hash:
            st.session_state.end_photo_bytes=b; st.session_state.end_photo_hash=h
            now=datetime.now().replace(second=0,microsecond=0)
            st.session_state.g_end_date, st.session_state.g_end_time = now.date(), now.time()
            end_photo = bytes_to_pil(b)
    if up is not None:
        b=up.getvalue(); h=md5(b)
        if h and h!=st.session_state.end_photo_hash:
            st.session_state.end_photo_bytes=b; st.session_state.end_photo_hash=h
            img=bytes_to_pil(b); dt=exif_datetime(img)
            if dt: st.session_state.g_end_date, st.session_state.g_end_time = dt.date(), dt.time().replace(second=0,microsecond=0)
            else:
                now=datetime.now().replace(second=0,microsecond=0)
                st.session_state.g_end_date, st.session_state.g_end_time = now.date(), now.time()
            end_photo=img
    if end_photo:
        st.image(end_photo, caption=f"{_['timestamp']}: {st.session_state.g_end_date} {st.session_state.g_end_time.strftime('%H:%M')}", use_container_width=True)

# ---- Meta ----
st.subheader(_["project_info"])
m1,m2 = st.columns(2)
project_name = m1.text_input(_["project_name"], "")
manufacturer = m2.text_input(_["manufacturer"], "")
work_order = st.text_input(_["work_order"], "")
drawing = st.text_input(_["drawing"], "")
part_line = st.text_input(_["part_line"], "")

# ---- Timing ----
st.markdown(f"### {_['timing']}")
t1,t2,t3 = st.columns([1.2,1.2,0.5])
sd = t1.date_input(_["start_dt"], value=st.session_state.g_start_date, key="g_start_date")
stt = t1.time_input("", value=st.session_state.g_start_time, key="g_start_time")
default_end = (datetime.combine(sd, stt) + timedelta(hours=1)).replace(second=0, microsecond=0)
ed = t2.date_input(_["end_dt"], value=st.session_state.g_end_date or default_end.date(), key="g_end_date")
et = t2.time_input("", value=st.session_state.g_end_time or default_end.time(), key="g_end_time")
if t3.button(_["plus1h"]):
    new_end=(datetime.combine(sd,stt)+timedelta(hours=1)).replace(second=0,microsecond=0)
    st.session_state.g_end_date, st.session_state.g_end_time = new_end.date(), new_end.time()
dt_start = datetime.combine(st.session_state.g_start_date, st.session_state.g_start_time)
dt_end   = datetime.combine(st.session_state.g_end_date,   st.session_state.g_end_time)
st.caption(f"{_['duration']}: {fmt_duration(dt_end - dt_start, lang)}")

# ---- Requirements ----
st.markdown(f"### {_['requirements']}")
r1,r2 = st.columns(2)
pt_value = r1.number_input(_["pt"], min_value=0.0, step=0.1, format="%.2f")
pt_unit_choice = r2.selectbox(_["pt_unit"], options=["bar","psi"], index=0,
                              format_func=lambda x: _["unit_bar_g"] if x=="bar" else _["unit_psi_g"])
notes = st.text_area(_["notes"], "")

# ---- Compartments ----
st.markdown(f"### {_['equip']}")
comp_count = st.selectbox(_["num_comp"], options=[1,2,3,4], index=st.session_state.comp_count-1)
if comp_count != st.session_state.comp_count:
    st.session_state.comp_count = comp_count
    st.session_state.rows = [{} for _ in range(comp_count)]

labels=[_["date"],_["start_time"],_["start_pressure"],_["end_time"],_["end_pressure"],_["result"],_["remarks"]]
comps=[]
for i in range(st.session_state.comp_count):
    with st.expander(f"{_['compartments']} {i+1}", expanded=True):
        cA,cB = st.columns(2)
        cd = cA.date_input(labels[0], value=date.today(), key=f"c{i}_date")
        cst = cA.time_input(labels[1], value=time(9,0), key=f"c{i}_startt")
        cet = cA.time_input(labels[3], value=time(10,0), key=f"c{i}_endt")
        csp = cB.number_input(labels[2]+f" ({_['unit_bar_g']})", min_value=0.0, step=0.1, format="%.2f", key=f"c{i}_spbar")
        cep = cB.number_input(labels[4]+f" ({_['unit_bar_g']})", min_value=0.0, step=0.1, format="%.2f", key=f"c{i}_epbar")
        sp_bar = float(csp) if csp is not None else None
        ep_bar = float(cep) if cep is not None else None
        sp_psi = bar_to_psi(sp_bar) if sp_bar is not None else None
        ep_psi = bar_to_psi(ep_bar) if ep_bar is not None else None
        res = st.radio(labels[5], options=["", _["pass"], _["fail"]], index=0, horizontal=True, key=f"c{i}_res")
        rem = st.text_input(labels[6], "", key=f"c{i}_rem")
        c_start = datetime.combine(cd, cst)
        c_end = datetime.combine(cd, cet) if cet>=cst else datetime.combine(cd+timedelta(days=1), cet)
        durh = max((c_end - c_start).total_seconds()/3600.0, 0.0)
        dev_bar_h = ((sp_bar - ep_bar)/durh) if (sp_bar is not None and ep_bar is not None and durh>0) else None
        dev_psi_h = bar_to_psi(dev_bar_h) if dev_bar_h is not None else None
        st.caption(f"ΔP/uur: bar/h {'' if dev_bar_h is None else f'{dev_bar_h:.2f}'} | PSI/h {'' if dev_psi_h is None else f'{dev_psi_h:.2f}'}")
        comps.append({
            "date":cd,"date_str":cd.strftime("%Y-%m-%d"),
            "start_time":cst,"start_time_str":cst.strftime("%H:%M"),
            "start_bar":sp_bar,"start_psi":sp_psi,
            "end_time":cet,"end_time_str":cet.strftime("%H:%M"),
            "end_bar":ep_bar,"end_psi":ep_psi,
            "result":res,"remarks":rem,
            "dev_bar_h":dev_bar_h,"dev_psi_h":dev_psi_h
        })

# ---- Signature ----
st.markdown(f"### {_['signature']}")
sg1,sg2 = st.columns([2,1])
with sg1:
    st.write(_["draw_signature"])
    canv = st_canvas(fill_color="rgba(0,0,0,0)", stroke_width=2, stroke_color="#000",
                     background_color="#FFF", update_streamlit=True, height=170,
                     drawing_mode="freedraw", key="sig_canvas")
    sig_img = canvas_to_pil(canv.image_data) if canv is not None else None
with sg2:
    sign_name = st.text_input(_["sign_name"], "")
    sign_company = st.text_input(_["sign_company"], "")
    sign_date = st.date_input(_["sign_date"], value=date.today())

# ---- Actions ----
st.markdown(f"### {_['actions']}")
b1,b2 = st.columns(2)
gen = b1.button(_["gen_pdf"], type="primary")
reset = b2.button(_["reset"])
if reset:
    for k in ["comp_count","rows","g_start_date","g_start_time","g_end_date","g_end_time",
              "start_photo_bytes","end_photo_bytes","start_photo_hash","end_photo_hash"]:
        st.session_state.pop(k, None)
    st.experimental_rerun()

def _meta_ok(): return all([project_name.strip(), manufacturer.strip(), work_order.strip(), drawing.strip(), part_line.strip()])
def _req_ok():  return pt_value is not None and pt_value>=0.0 and pt_unit_choice in ("bar","psi")
def _comps_ok():
    for c in comps:
        if (c["date"] is None or c["start_time"] is None or c["end_time"] is None or
            c["start_bar"] is None or c["end_bar"] is None or c["result"] not in (_["pass"], _["fail"])):
            return False
    return True
def _sig_ok(): return bool(sign_name.strip()) and bool(sign_company.strip()) and bool(sign_date) and sig_img is not None

pdf_bytes=None
if gen:
    start_photo = bytes_to_pil(st.session_state.start_photo_bytes)
    end_photo   = bytes_to_pil(st.session_state.end_photo_bytes)
    miss=[]
    if not (start_photo and end_photo): miss.append(_["photos"])
    if not _meta_ok(): miss.append(_["project_info"])
    if not _req_ok(): miss.append(_["requirements"])
    if not _comps_ok(): miss.append(_["equip"])
    if not _sig_ok(): miss.append(_["signature"])
    if dt_end < dt_start:
        st.error(_["end_before_start"])
    elif miss:
        st.error(_["need_all"]); st.info("Ontbreekt / Missing: " + ", ".join(miss))
    else:
        timing={
            "start_dt":dt_start,"end_dt":dt_end,
            "start_str":dt_start.strftime("%Y-%m-%d %H:%M"),
            "end_str":dt_end.strftime("%Y-%m-%d %H:%M"),
            "duration":dt_end-dt_start,
            "duration_str":fmt_duration(dt_end-dt_start, lang)
        }
        req={"pt_value":float(pt_value),"pt_unit":"bar" if pt_unit_choice=="bar" else "psi","notes":notes}
        meta={"project_name":project_name,"manufacturer":manufacturer,"work_order":work_order,"drawing":drawing,"part_line":part_line}
        signature={"name":sign_name,"company":sign_company,"date":sign_date,"date_str":sign_date.strftime("%Y-%m-%d"),"image_pil":sig_img}
        photos={"start_pil":start_photo,"end_pil":end_photo}
        pdf_data={"meta":meta,"requirements":req,"timing":timing,"compartments":comps,"photos":photos,"signature":signature}
        logo_path = os.path.join("assets","logo.png") if os.path.exists(os.path.join("assets","logo.png")) else None
        pdf_bytes = build_pdf_bytes(pdf_data, logo_path=logo_path); st.success(_["success_pdf"])

if pdf_bytes:
    fname=f"{datetime.now().strftime('%Y-%m-%d')}_{(project_name or 'Project').replace(' ','_')}_Report.pdf"
    st.download_button(_["dl_pdf"], data=pdf_bytes, file_name=fname, mime="application/pdf")
