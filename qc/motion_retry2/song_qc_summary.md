# Song lyric QC summary

Verdict uses only items that more than half of the engine runs agree on. Minority items are listed separately: confirm them with slice_check.py before dismissing them.

| Song | Verdict | Lyric coverage (vocal runs) | Vocal onset | Agreed items | Minority items |
|---|---|---|---|---|---|
| motion_reggaeton_male_r2 | **PASS** | 99%-100% | 10.84 s | - | REVIEW single word dropped: lyric 'and' heard '' (1/4) |
| motion_jazz_female_r2 | **PASS** | 99%-100% | 0.06 s | - | REVIEW inflection / sound-alike: lyric 'common' heard 'come' (1/4)<br>REVIEW inflection / sound-alike: lyric 'to' heard 'and' (1/4) |
| motion_acappella_female_r2 | **PASS** | 95%-96% | 4.38 s | - | FAIL omission (protected): lyric 'and out of or lungs blood flows' heard '' @27.2s (2/4)<br>REVIEW inflection / sound-alike: lyric 'in' heard 'an' @27.2s (2/4)<br>FAIL omission (protected): lyric 'and out of or lungs blood flows in' heard '' @27.4s (1/4)<br>FAIL omission: lyric 'and out of' heard '' (1/4)<br>FAIL omission (protected): lyric 'lungs blood flows in' heard '' (1/4) |
