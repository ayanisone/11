"""Step 6 (optional): one Word document of lyrics per song, named after the song file.

Usage:  python scripts/make_lyric_docs.py <project_dir>
Writes: <project>/lyric_docs/<stem> - lyrics.docx
"""
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_songs  # noqa: E402

LANG = {"hi": "Hindi", "en": "English", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam",
        "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati", "pa": "Punjabi", "or": "Odia"}

project = Path(sys.argv[1])
out_dir = project / "lyric_docs"
out_dir.mkdir(exist_ok=True)
for row in read_songs(project):
    d = Document()
    st = d.styles["Normal"]
    st.font.name = "Arial"
    st.font.size = Pt(12)
    d.add_heading(" — ".join(x for x in (row.get("title"), row.get("style")) if x) or row["stem"], level=1)
    meta = d.add_paragraph()
    for k, v in (("Song file", row["song_file"]), ("Language", LANG.get(row["language"], row["language"])),
                 ("Style", row.get("style", "")), ("Model", row.get("model", ""))):
        if v:
            meta.add_run(f"{k}: ").bold = True
            meta.add_run(v + "\n")
    for line in (project / row["lyrics_file"]).read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if line.strip().startswith("["):
            p = d.add_paragraph()
            r = p.add_run(line.strip())
            r.bold = True
            r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(2)
        else:
            d.add_paragraph(line.strip()).paragraph_format.space_after = Pt(0)
    out = out_dir / f"{row['stem']} - lyrics.docx"
    d.save(out)
    print(out)
