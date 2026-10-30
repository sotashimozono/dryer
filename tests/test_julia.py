from dryer.discover import iter_source_files, language_of
from dryer.extract import entries_in_source
from dryer.scan import find_duplicates


def forms(source: str, file: str = "a.jl"):
    entries, warning = entries_in_source("julia", source, file, file)
    assert warning is None
    return entries


def spans(source: str) -> list[tuple[int, int]]:
    return [(entry.start_line, entry.end_line) for entry in forms(source)]


def score(left: str, right: str) -> float:
    found = find_duplicates(forms(left, "a.jl") + forms(right, "b.jl"), threshold=0.0)
    assert len(found) == 1
    return found[0].score


def test_jl_files_are_julia_and_the_test_tree_is_skipped(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "test").mkdir()
    (tmp_path / "src" / "M.jl").write_text("f(x) = x\n", encoding="utf-8")
    (tmp_path / "test" / "runtests.jl").write_text("f(x) = x\n", encoding="utf-8")
    assert language_of("src/M.jl") == "julia"
    assert [path.name for path in iter_source_files([tmp_path])] == ["M.jl"]


def test_renamed_locals_match_in_the_long_form():
    left = "function alpha(xs)\n    ys = filter(isodd, xs)\n    map(inc, ys)\nend\n"
    right = "function beta(items)\n    kept = filter(isodd, items)\n    map(inc, kept)\nend\n"
    assert score(left, right) == 1.0


def test_renamed_locals_match_in_the_short_form():
    assert score("alpha(xs) = map(inc, xs)\n", "beta(items) = map(inc, items)\n") == 1.0


def test_a_different_operator_lowers_the_score():
    left = "function alpha(x)\n    y = x + 1\n    y > 2\nend\n"
    right = "function beta(x)\n    y = x * 1\n    y > 2\nend\n"
    assert score(left, right) < 1.0


def test_a_qualified_callee_keeps_its_name():
    assert score("alpha(xs) = Base.sum(xs)\n", "beta(xs) = Base.prod(xs)\n") < 1.0


def test_a_macro_name_is_part_of_the_structure():
    left = "function alpha(x)\n    @assert x > 0\n    x\nend\n"
    right = "function beta(x)\n    @show x > 0\n    x\nend\n"
    assert score(left, right) < 1.0


def test_a_do_block_body_is_part_of_the_call():
    left = "function alpha(xs)\n    map(xs) do v\n        v + 1\n    end\nend\n"
    right = "function beta(xs)\n    map(xs) do v\n        sqrt(v)\n    end\nend\n"
    assert score(left, right) < 1.0


def test_an_interpolated_string_is_not_a_plain_literal():
    assert score('alpha(xs) = "xs"\n', 'beta(xs) = "$(xs)"\n') < 1.0


def test_definitions_with_a_body_are_the_forms():
    source = """\
module M
function alpha(x)
    inner(y) = y + 1
    function inner2(z)
        z
    end
    inner(x)
end
beta(x)::Int = x + 1
gamma(x::T) where {T} = x
function delta end
macro m(ex)
    esc(ex)
end
struct S
    a::Int
end
const K = 3
end
"""
    assert spans(source) == [(2, 8), (9, 9), (10, 10), (12, 14)]
