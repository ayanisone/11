# QC findings: গতি (Motion), Bengali, 95 s: 4 styles × male + female

Lyric sheet `lyrics/motion_bn_lyrics_95s_v1.txt`. First Bengali run: Scribe `bn`, Sarvam `bn-IN`.
Judged by transcript read, the Bengali key-phrase list and 10-engine slice checks. Retries: `qc/motion_bn_retry1`, `qc/motion_bn_retry2`.

**Spelling notes (not singing errors):** "ত্বরণ" is spoken "তোরোন" in Bengali, so STT writes "তরণ / তরন"; "সমত্বরণ" comes out "সমত্তরণ / সমুত্তরণ". The same letter য় can come in two Unicode forms. The key-phrase list now accepts all of these.

Credits: 14 × 2,217 (8 batch + 3 retry 1 + 3 retry 2) = **31,033**.

| Style | Male | Female |
|---|---|---|
| Indie / acoustic folk | **PASS**, first try | **PASS**, first try |
| Rabindra-inspired fusion | **REVIEW: listen at 1:30**: every line right, but the file ends after the first line of the final chorus ("গতির বর্ণনা: বেগ ও ত্বরণ" is in the opening chorus only). "সরলরৈখিক" heard as "সরল ও রৈখিক" in 4/10 listens | **PASS**, first try |
| Bangla rock | 3 tries. Try 1: "বাঁধ" → "পাত" (10/10). Try 2: "রক্ত" dropped, "সমত্বরণ" → "সমৎপরণ" (10/10). Try 3: **PASS** | 3 tries. Try 1: "গতি" in V1 line 1 lost ("ইতি", 10/10). Try 2: "বাঁধ" → "পাতিয়ে", made-up words after the bridge (10/10). Try 3: **PASS (minor)**: "জল নেমে যায়" drops "যায়" |
| R&B / soul | **PASS (minor)**, first try ("ধমনী ও" sung joined as "ধমনীয়") | 3 tries. Try 1: "ত্বরণ" → "তরঙ্গ" (wave), "মহাবিশ্ব" → "মহাদেশ", extra line, V2 garbled. Try 2: "ধমনী" garbled, "সমত্বরণ" → "সমৎপরণ". Try 3: **PASS (minor)**: "রক্ত, রক্ত" echoed once |

**Summary:** 8 of 8 usable: 7 PASS + 1 REVIEW. Folk was perfect first try for both voices; rock and the R&B woman needed all 3 tries.

**Prompt lesson:** asking for "a clear ত্ব" in "সমত্বরণ" made two takes sing "সমৎপরণ". Giving the natural spoken sound instead ("শমোত্তোরোন", "তোরোন") fixed it in all three final takes. For Bengali, describe how a word *sounds*, not how it is *spelled*.
