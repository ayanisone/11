# Song lyric QC summary

Verdict uses only items that more than half of the engine runs agree on. Minority items are listed separately: confirm them with slice_check.py before dismissing them.

| Song | Verdict | Lyric coverage (vocal runs) | Vocal onset | Agreed items | Minority items |
|---|---|---|---|---|---|
| newton_laws_pop_SHORT_english_v2-5 | **PASS** | 100%-100% | 0.28 s | - | REVIEW inflection / sound-alike: lyric 'at' heard 'to' @7.5s (1/4) |
| pythagoras_bollywood_hindi_v2-5_take3 | **FAIL** | 100%-100% | 8.9 s | FAIL new word inserted: lyric '' heard 'स्थित' @16.0s (3/4) | FAIL new word inserted: lyric '' heard 'है' (1/4) |
| pythagoras_rap_hindi_v2-5_take2 | **FAIL** | 95%-97% | 10.5 s | FAIL omission (protected): lyric 'a' heard '' @29.3s (4/4)<br>REVIEW single word dropped: lyric 'के' heard '' @18.0s (4/4)<br>REVIEW inflection / sound-alike: lyric 'और' heard 'o' @24.0s (3/4) | - |
| pythagoras_rock_hindi_v2-5_take3 | **REVIEW** | 100%-100% | 5.9 s | REVIEW reorder (section sung elsewhere): lyric 'three four और five nine plus sixteen twenty five' heard '' @16.8s (4/4) | - |
