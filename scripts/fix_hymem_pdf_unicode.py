"""Embed the GB1 Unicode map needed by HyMEM PDF previews without external CMaps."""

import argparse
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject


CMAP_PATH = Path(__file__).resolve().parents[1] / "reports/homework/resources/Adobe-GB1-UCS2"


def embed_unicode_map(source: Path, destination: Path) -> int:
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output must differ; keep the original compiled PDF.")
    writer = PdfWriter(clone_from=source)
    cmap_ref = None
    updated = 0
    for page in writer.pages:
        for font_ref in page["/Resources"].get("/Font", {}).values():
            font = font_ref.get_object()
            if font.get("/Subtype") != "/Type0" or "/ToUnicode" in font:
                continue
            descendant = font["/DescendantFonts"][0].get_object()
            info = descendant.get("/CIDSystemInfo", {})
            if (font.get("/Encoding") != "/Identity-H"
                    or info.get("/Registry") != "Adobe"
                    or info.get("/Ordering") != "GB1"):
                raise ValueError(f"Unsupported font without Unicode mapping: {font.get('/BaseFont')}")
            # Standard GB1 CIDs need an explicit map when a viewer has no external CMaps.
            if cmap_ref is None:
                stream = DecodedStreamObject()
                stream.set_data(CMAP_PATH.read_bytes())
                cmap_ref = writer._add_object(stream.flate_encode())
            font[NameObject("/ToUnicode")] = cmap_ref
            updated += 1
    writer.write(destination)
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    count = embed_unicode_map(args.source, args.destination)
    print(f"Embedded Unicode mapping for {count} fonts: {args.destination}")


if __name__ == "__main__":
    main()
