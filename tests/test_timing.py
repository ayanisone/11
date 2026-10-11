from bn_dub import timing


def test_slot_borrows_gap_but_not_more_than_max():
    # 2s line, next line starts 0.5s later -> borrow 0.5 - pad
    assert abs(timing.slot_for(10.0, 12.0, 12.5, pad=0.1) - 2.4) < 1e-9
    # huge gap: capped at max_borrow
    assert abs(timing.slot_for(10.0, 12.0, 30.0, pad=0.1, max_borrow=1.5) - 3.5) < 1e-9
    # last line: gets max_borrow
    assert abs(timing.slot_for(10.0, 12.0, None, max_borrow=1.5) - 3.5) < 1e-9
    # overlapping next line: no negative borrow
    assert abs(timing.slot_for(10.0, 12.0, 11.0) - 2.0) < 1e-9


def test_plan_fit_ok_when_shorter():
    plan = timing.plan_fit(1.8, 2.0, max_stretch=1.15)
    assert plan.action == "ok" and plan.stretch == 1.0


def test_plan_fit_stretches_within_tolerance():
    plan = timing.plan_fit(2.2, 2.0, max_stretch=1.15)
    assert plan.action == "stretch"
    assert abs(plan.stretch - 1.1) < 1e-9


def test_plan_fit_asks_to_shorten_past_tolerance():
    plan = timing.plan_fit(3.0, 2.0, max_stretch=1.15, hard_stretch=1.35)
    assert plan.action == "shorten"
    # target length = 2.0 * 1.15 = 2.3s -> cut 23%
    assert plan.shorten_pct == 23


def test_plan_fit_slows_very_short_lines_only_a_little():
    plan = timing.plan_fit(0.8, 2.0, max_stretch=1.15)
    assert plan.action == "stretch"
    assert abs(plan.stretch - 1 / 1.15) < 1e-9  # never slower than the tolerance allows


def test_hard_fit_clamps():
    plan = timing.hard_fit(4.0, 2.0, hard_stretch=1.35)
    assert plan.action == "hard" and plan.stretch == 1.35
