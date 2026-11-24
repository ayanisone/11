# Project notes for Claude

- Educational science songs for kids, made with ElevenLabs Music v2.5. The user is a sound engineer and writes in Hinglish; explain with audio analogies, keep it tight.
- **Genres per language are fixed: read `GENRES_BY_LANGUAGE.md` before any new generation** and generate every listed genre for the theory's language, male + female take each.
- Workflow: theory → lyrics → fact QC → user approval → generate → full audio QC (`qc_kit/run_all.sh`) → up to 2 prompt-only retries per failed take → deliver to `music/<theory>_<lang>/` with PASS/REVIEW in the file name.
- Never commit `qc_kit/.env`; the Sarvam key is proxy-injected.
