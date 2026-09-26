"""Pull per-character ink masks out of donor.pdf.

CYBBCJT (and any font like it that refuses embedding) turns out to render
through PowerPoint's PDF export as: an INVISIBLE (opacity 0) text run in a
substitute font, for search/copy -- plus a separate per-character raster
image (an SMask alpha stencil) carrying the actual visible ink. A handful of
characters CYBBCJT doesn't have fall back to a normal VISIBLE vector run in
whatever font Windows substituted; those have no paired image and must be
skipped, or the donor silently inherits generic system-font shapes mislabeled
as CYBBCJT.

Match text-run bbox to image bbox (same cell, near-identical rectangle) to
recover which character each ink image belongs to -- no cmap/GID tricks
needed, no OCR, no manifest cross-referencing required either.
"""
import argparse
import os

import fitz


def bbox_close(a, b, tol=1.0):
    return all(abs(a[i] - b[i]) <= tol for i in range(4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    doc = fitz.open(args.pdf)

    saved, skipped_fallback, skipped_dup = 0, 0, 0
    seen_cp = set()

    for pno in range(len(doc)):
        page = doc[pno]
        d = page.get_text("rawdict")
        text_blocks = [b for b in d["blocks"] if b["type"] == 0]

        # (x0, smask_xref) per real image instance -- get_image_bbox is the
        # documented, reliable position lookup; rawdict's own 'number' field
        # on image blocks is NOT the xref (confirmed by inspection) and its
        # 'xref' from get_image_info() is unreliable (shared/wrong across
        # instances that share a byte-identical 2x2 base fill).
        images = []
        for im in page.get_images(full=True):
            xref, smask = im[0], im[1]
            if not smask:
                continue
            bbox = page.get_image_bbox(im)
            images.append((bbox.x0, bbox.y0, smask))

        chars = []
        for b in text_blocks:
            for line in b["lines"]:
                for span in line["spans"]:
                    for ch in span["chars"]:
                        chars.append((ch["c"], ch["bbox"]))

        for cp_char, cbbox in chars:
            cx0, cy0 = cbbox[0], cbbox[1]
            smask_xref = None
            for ix0, iy0, ism in images:
                if abs(ix0 - cx0) <= 0.5 and abs(iy0 - cy0) <= 15.0:
                    smask_xref = ism
                    break
            if smask_xref is None:
                skipped_fallback += 1
                continue
            cp = ord(cp_char)
            if cp in seen_cp:
                skipped_dup += 1
                continue
            seen_cp.add(cp)
            info = doc.extract_image(smask_xref)
            fn = os.path.join(args.out_dir, f"uni{cp:04X}.png")
            with open(fn, "wb") as fh:
                fh.write(info["image"])
            saved += 1

    print(f"saved: {saved}  skipped_fallback(no CYBBCJT glyph): "
          f"{skipped_fallback}  skipped_dup: {skipped_dup}")


if __name__ == "__main__":
    main()
