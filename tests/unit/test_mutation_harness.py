from tools.mutation_test import Mutation, apply_mutation


def test_compound_mutation_applies_both_declared_edits():
    mutation = Mutation(
        name="compound",
        why="test",
        old="first",
        new="FIRST",
        also=("second", "SECOND"),
    )
    assert apply_mutation("first and second", mutation) == "FIRST and SECOND"


def test_stale_primary_or_secondary_anchor_breaks_the_mutation():
    primary = Mutation(name="p", why="test", old="missing", new="x")
    secondary = Mutation(name="s", why="test", old="first", new="FIRST",
                         also=("missing", "x"))
    assert apply_mutation("first and second", primary) is None
    assert apply_mutation("first and second", secondary) is None
