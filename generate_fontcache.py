#!/usr/bin/env python
"""
Use fontconfig to generate a Matplotlib (TrueType/OpenType) font cache::

    $ ./generate_fontcache.py print  # print entries of generated font cache
    $ ./generate_fontcache.py write  # write updated font cache to disk
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import json
from pathlib import Path
import re
import subprocess

import matplotlib as mpl
from matplotlib import font_manager as fm
import numpy as np


def generate_entries():
    fc_format = r"--format=%{file}\n%{family}\n%{slant}\n%{weight}\n%{width}\n"
    vendored_fonts_dir = Path(mpl.get_data_path(), "fonts/ttf")
    vendored_fonts = [*map(str, vendored_fonts_dir.glob("*.ttf"))]
    vendored_fonts = subprocess.check_output(
        ["fc-query", fc_format] + vendored_fonts, universal_newlines=True)
    system_fonts = subprocess.check_output(
        ["fc-list", fc_format], universal_newlines=True)
    entries = []
    lines = vendored_fonts.splitlines() + system_fonts.splitlines()
    while lines:
        fc_file, fc_family, fc_slant, fc_weight, fc_width, *lines = lines
        file = fc_file
        families = fc_family.split(",")
        if re.match("\A\[.*\]\Z", fc_weight):  # Variable weight, unsupported.
            print(f"Skipping {fc_file} (unsupported variable weight)")
            continue
        style = {"0": "normal", "100": "italic", "110": "oblique"}[fc_slant]
        # See FcWeightToOpenType.
        # Note that 215 ("EXTRABLACK") does not appear in the docs, but in the
        # header...
        fc_weights = [0, 40, 50, 55, 75, 80, 100, 180, 200, 205, 210, 215]
        css_weights = [
            100, 200, 300, 350, 380, 400, 500, 600, 700, 800, 900, 1000]
        weight = int(np.interp(float(fc_weight), fc_weights, css_weights) + .5)
        # The old version from pango_fc_weight_to_pango was:
        # weight = (
        #     100 if fc_weight <= 20
        #     else 200 if fc_weight <= 45
        #     else 300 if fc_weight <= 62
        #     else 380 if fc_weight <= 77
        #     else 400 if fc_weight <= 90
        #     else 500 if fc_weight <= 140
        #     else 600 if fc_weight <= 190
        #     else 700 if fc_weight <= 202
        #     else 800 if fc_weight <= 207
        #     else 900 if fc_weight <= 212
        #     else 1000)
        stretch = {
            "50": "ultra-condensed",
            "63": "extra-condensed",
            "75": "condensed",
            "87": "semi-condensed",
            "100": "normal",
            "113": "semi-expanded",
            "125": "expanded",
            "150": "extra-expanded",
            "200": "ultra-expanded",
        }[fc_width]
        variant = "normal"  # Small caps not supported.
        size = "scalable"
        entries.extend(
            fm.FontEntry(file, family, style, variant, weight, stretch, size)
            for family in families)
    entries.sort(key=lambda entry: entry.fname)
    return entries


def main():
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["print", "write"])
    args = parser.parse_args()
    entries = generate_entries()
    if args.action == "print":
        for entry in entries:
            print(entry)
    elif args.action == "write":
        fm.fontManager.ttflist = entries
        with open(fm._fmcache, "w") as file:
            json.dump(fm.fontManager, file,
                      cls=fm.JSONEncoder, indent=2, sort_keys=True)
        print("Font cache written to {}".format(fm._fmcache))


if __name__ == "__main__":
    main()
