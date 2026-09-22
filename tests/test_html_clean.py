"""Tests for Moodle HTML cleaning."""

from moodle_competency.html_clean import (
    combine_text,
    html_to_text,
)


def test_html_to_text_removes_markup() -> None:
    html = """
    <div>
        <h2>Database Design</h2>
        <p>Use <strong>normalization</strong> &amp; keys.</p>
        <script>hidden()</script>
    </div>
    """

    result = html_to_text(html)

    assert result == (
        "Database Design Use normalization & keys."
    )
    assert "hidden" not in result


def test_combine_text_ignores_duplicates() -> None:
    result = combine_text(
        "Course introduction",
        "Course introduction",
        "Main content",
    )

    assert result == (
        "Course introduction\n\nMain content"
    )
