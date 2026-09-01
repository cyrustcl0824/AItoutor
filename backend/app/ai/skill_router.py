from pathlib import Path

_repo_skills = Path(__file__).resolve().parents[3] / "skills"
_container_skills = Path("/app/skills")
SKILL_ROOT = _repo_skills if _repo_skills.is_dir() else _container_skills


def route_skills(mode: str, text: str) -> list[str]:
    lower = text.lower()
    english = "conversation"
    if mode == "vocabulary" or any(word in lower for word in ["word", "vocabulary", "单词"]):
        english = "vocabulary"
    elif any(word in lower for word in ["grammar", "句型", "语法"]):
        english = "grammar"
    elif mode == "lesson":
        english = "pep-sync"
    skills = ["common/socratic-tutor", f"english/{english}"]
    if mode == "lesson":
        skills.append("vendor/hermes/primary-english-pep-textbook-sync")
    if mode == "review":
        skills.append("vendor/hermes/agent-mistake-review")
    return skills


def load_skills(names: list[str]) -> str:
    chunks = []
    for name in names:
        path = (SKILL_ROOT / name / "SKILL.md").resolve()
        if SKILL_ROOT.resolve() not in path.parents:
            continue
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(chunks)
