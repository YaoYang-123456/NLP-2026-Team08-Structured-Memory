"""Embed the licensed Adobe map only for missing GB1/Identity-H ToUnicode maps."""
import argparse
import json
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject


def embed(source, destination):
    if destination.exists():
        raise ValueError("Choose a new output PDF; never overwrite the source")
    reader = PdfReader(source)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    mapping = (Path(__file__).parent / "Adobe-GB1-UCS2").read_bytes()
    stream = DecodedStreamObject()
    stream.set_data(mapping)
    reference = writer._add_object(stream)
    changed = []
    seen = set()
    for page in writer.pages:
        for fontref in page["/Resources"].get("/Font", {}).values():
            font = fontref.get_object()
            identity = id(font)
            if identity in seen:
                continue
            seen.add(identity)
            if font.get("/Subtype") != "/Type0" or "/ToUnicode" in font:
                continue
            descendants = font.get("/DescendantFonts", [])
            if not descendants:
                continue
            system = descendants[0].get_object().get("/CIDSystemInfo", {})
            if font.get("/Encoding") != "/Identity-H" or system.get("/Registry") != "Adobe" or system.get("/Ordering") != "GB1":
                raise ValueError("Missing ToUnicode has an unsupported encoding; do not guess")
            font[NameObject("/ToUnicode")] = reference
            changed.append(str(font["/BaseFont"]))
    with destination.open("xb") as output:
        writer.write(output)
    return {"pages": len(writer.pages), "embedded_maps": changed,
            "glyphs_or_layout_changed": False, "source_preserved": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(embed(args.source, args.destination), ensure_ascii=False))
