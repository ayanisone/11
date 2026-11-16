# Song lyric QC summary

Verdict uses only items that more than half of the engine runs agree on. Minority items are listed separately: confirm them with slice_check.py before dismissing them.

| Song | Verdict | Lyric coverage (vocal runs) | Vocal onset | Agreed items | Minority items |
|---|---|---|---|---|---|
| waves_reggaeton_male_r1 | **PASS** | 100%-100% | 5.06 s | - | FAIL new word inserted: lyric '' heard 'ambi' (1/4)<br>FAIL new word inserted: lyric '' heard 'jul' (1/4)<br>FAIL omission (protected): lyric 'amplitude' heard '' (1/4) |
| waves_jazz_female_r1 | **PASS** | 100%-100% | 7.26 s | - | REVIEW inflection / sound-alike: lyric 'the' heard 'a' @30.0s (1/4)<br>FAIL omission (protected): lyric 'c' heard '' (1/4) |
| waves_punk_female_r1 | **FAIL** | 99%-100% | 6.2 s | FAIL omission (protected): lyric 'wavelength' heard '' @184.6s (4/4) | FAIL protected term changed: lyric 'c' heard 'v' @82.7s (1/4)<br>FAIL new word inserted: lyric '' heard 'indeed' @129.0s (1/4)<br>FAIL new word inserted: lyric '' heard 'sea' @129.2s (2/4)<br>REVIEW inflection / sound-alike: lyric 'an' heard 'and' (1/4) |
| waves_kpop_male_r1 | **FAIL** | 98%-100% | 8.16 s | FAIL omission (protected): lyric 'waves' heard '' @200.4s (4/4) | FAIL protected term changed: lyric 'c' heard 'cc' (1/4)<br>FAIL omission (protected): lyric 'c' heard '' (1/4)<br>REVIEW inflection / sound-alike: lyric 'or' heard 'on' (1/4) |
