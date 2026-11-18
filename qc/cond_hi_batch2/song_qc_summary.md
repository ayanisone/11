# Song lyric QC summary

Verdict uses only items that more than half of the engine runs agree on. Minority items are listed separately: confirm them with slice_check.py before dismissing them.

| Song | Verdict | Lyric coverage (vocal runs) | Vocal onset | Agreed items | Minority items |
|---|---|---|---|---|---|
| cond_hi_indie_male | **FAIL** | 96%-96% | 0.32 s | FAIL new word inserted: lyric '' heard 'रोधी' @9.8s (4/4)<br>FAIL omission (protected): lyric 'अधिकांश पदार्थ' heard '' @91.4s (4/4)<br>REVIEW single word dropped: lyric 'उच्च' heard '' @11.6s (4/4)<br>REVIEW sound-alike on protected term: lyric 'इलेक्ट्रॉन' heard 'electron' @30.6s (4/4) | FAIL protected term changed: lyric 'दो' heard 'two' (1/4) |
| cond_hi_indie_female | **REVIEW** | 99%-99% | 2.96 s | REVIEW sound-alike on protected term: lyric 'इलेक्ट्रॉन' heard 'electron' @24.5s (4/4) | FAIL new word inserted: lyric '' heard 'रोधी' @9.4s (1/4) |
| cond_hi_pop_male | **FAIL** | 94%-96% | 0.28 s | FAIL omission (protected): lyric 'चालक' heard '' @39.4s (4/4)<br>FAIL omission (protected): lyric 'कुछ अन्य ऐसा नहीं करते' heard '' @40.2s (3/4)<br>FAIL new word inserted: lyric '' heard 'और' @77.1s (4/4)<br>REVIEW sound-alike on protected term: lyric 'इलेक्ट्रॉन' heard 'electron' @30.3s (4/4) | FAIL omission (protected): lyric 'अन्य ऐसा नहीं करते' heard '' @40.7s (1/4)<br>FAIL new word inserted: lyric '' heard 'ते' @86.5s (2/4)<br>FAIL new word inserted: lyric '' heard 'ক' @33.4s (1/4)<br>FAIL new word inserted: lyric '' heard 'ত' @33.4s (1/4)<br>FAIL protected term changed: lyric 'दो' heard 'two' (1/4)<br>FAIL new word inserted: lyric '' heard 'रोधी' (1/4) |
| cond_hi_pop_female | **PASS** | 99%-100% | 4.059 s | - | FAIL protected term changed: lyric 'दो' heard 'two' (1/4)<br>REVIEW sound-alike on protected term: lyric 'इलेक्ट्रॉन' heard 'electron' (1/4) |
