from ann_app.fetch import Candidate
from ann_app.render import render_markdown, update_readme_link


def test_render_markdown_lists_headlines_in_order():
    selections = {
        "WSJ": [
            Candidate(outlet="WSJ", title="Story A", link="https://wsj.com/a"),
            Candidate(outlet="WSJ", title="Story B", link="https://wsj.com/b"),
        ],
        "NYT": [],
        "NBC": [],
        "AP": [],
    }
    markdown = render_markdown(selections, fetch_errors={})

    assert "## WSJ" in markdown
    assert "1. [Story A](https://wsj.com/a)" in markdown
    assert "2. [Story B](https://wsj.com/b)" in markdown
    assert markdown.index("Story A") < markdown.index("Story B")


def test_render_markdown_notes_fetch_errors():
    selections = {"WSJ": [], "NYT": [], "NBC": [], "AP": []}
    markdown = render_markdown(selections, fetch_errors={"AP": "timeout"})

    assert "## Note" in markdown
    assert "AP" in markdown
    assert "timeout" in markdown


def test_render_markdown_notes_short_outlet():
    selections = {
        "WSJ": [Candidate(outlet="WSJ", title="Only one", link="https://wsj.com/a")],
        "NYT": [],
        "NBC": [],
        "AP": [],
    }
    markdown = render_markdown(selections, fetch_errors={})

    assert "only 1 usable headline" in markdown


def test_update_readme_link(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# All the News You Need\n\n[Go to Today's Headlines.](headlines-2026-07-01.md)\n\nBody text.\n"
    )

    update_readme_link(str(readme), "headlines-2026-07-02.md")

    content = readme.read_text()
    assert "[Go to Today's Headlines.](headlines-2026-07-02.md)" in content
    assert "headlines-2026-07-01.md" not in content
    assert "Body text." in content
