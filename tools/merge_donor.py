"""Fill a real-handwriting font's missing codepoints from a donor font.
Real glyphs always win; donor only occupies codepoints the base font lacks.
Both fonts must share UPM/ascent/descent (true here -- both built by
build_font.py's build_ttf, which fixes those constants), so glyf outlines
copy over with no rescaling.

Usage: python tools/merge_donor.py --base build/0010Phoon.ttf \
    --donor build/donor-CYBBCJT/DonorCYBBCJT.ttf \
    --out build/0010Phoon_TEST_merged_donor_DO_NOT_DISTRIBUTE.ttf
"""
import argparse

from fontTools.ttLib import TTFont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--donor", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = TTFont(args.base)
    donor = TTFont(args.donor)

    base_cmap = base.getBestCmap()
    donor_cmap = donor.getBestCmap()
    base_cps = set(base_cmap)

    to_add = sorted(cp for cp in donor_cmap if cp not in base_cps)

    glyf_base = base["glyf"]
    glyf_donor = donor["glyf"]
    hmtx_base = base["hmtx"]
    hmtx_donor = donor["hmtx"]
    order = base.getGlyphOrder()

    added = 0
    for cp in to_add:
        gname = donor_cmap[cp]              # e.g. "uni4E01", already codepoint-named
        if gname in order:                  # already present under some other cp (shouldn't happen)
            continue
        glyf_base[gname] = glyf_donor[gname]   # auto-appends to glyf_base.glyphOrder,
        hmtx_base[gname] = hmtx_donor[gname]   # which IS `order` (same list object)
        for table in base["cmap"].tables:
            table.cmap[cp] = gname
        added += 1

    base.setGlyphOrder(order)
    base["maxp"].numGlyphs = len(order)

    base.save(args.out)
    print(f"base real glyphs: {len(base_cps)}  donor available: {len(donor_cmap)}  "
          f"added from donor: {added}  total after merge: {len(base_cps) + added}")


if __name__ == "__main__":
    main()
