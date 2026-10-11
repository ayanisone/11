from bn_dub import verify
from bn_dub.config import settings
from bn_dub.project import Project, Segment, Speaker


def test_project_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path)
    p = Project(name="t", source_path="x.mp4", duration=10.0)
    p.segments = [Segment(id=1, start=0.0, end=1.0, speaker="A", source_text="hi", target_text="হাই"),
                  Segment(id=2, start=2.0, end=3.0, speaker="B", source_text="yo")]
    p.speakers = [Speaker(id="A", voice_id="v1", voice_name="One")]
    p.save()
    q = Project.load("t")
    assert q.segments[0].target_text == "হাই"
    assert q.speakers[0].voice_id == "v1"
    assert q.next_start(q.segments[0]) == 2.0 and q.next_start(q.segments[1]) is None
    assert Project.list_names() == ["t"]
    assert q.speaker("C").id == "C" and len(q.speakers) == 2


def test_similarity_ignores_punctuation_and_case():
    assert verify.similarity("রোজ জল খান, ভালো থাকুন।", "রোজ জল খান ভালো থাকুন") == 1.0
    assert verify.similarity("Hello, World!", "hello world") == 1.0
    assert verify.similarity("one two three", "one two four") < 1.0
    assert verify.similarity("", "") == 1.0
