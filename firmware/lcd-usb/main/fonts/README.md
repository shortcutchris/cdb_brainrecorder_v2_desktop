# CDB text glyphs

Montserrat Regular, source https://github.com/JulietaUla/Montserrat/blob/master/fonts/ttf/Montserrat-Regular.ttf
retrieved 2026-10-21. SHA256: `3e8abe50c44c82e2242e97d1ec8c0d385c4890cdc50447bcdb8605c81a38cfb2`.
Original font retained here with its SIL Open Font License (OFL.txt).
Generated glyph subsets are named cdb_text_20 / 24 / 32.

Generation in this directory, for each SIZE 20, 24, 32:

```sh
npx --yes lv_font_conv@1.5.3 --font Montserrat-Regular.ttf --range 0x20-0xFF --size SIZE --bpp 4 --format lvgl --no-compress --no-prefilter --lv-font-name cdb_text_SIZE -o cdb_text_SIZE.c
```

Includes German umlauts/ß and Latin-1. Characters outside this range (including
emoji) may use LVGL's missing-glyph placeholder; do not claim universal Unicode
rendering. Timer numbers use the built-in Montserrat 48 font. No font conversion
or network request happens on the display.
