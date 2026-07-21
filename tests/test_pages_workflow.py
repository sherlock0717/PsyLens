# -*- coding: utf-8 -*-
"""Pages 发布 workflow 校验：项目说明直接写入 docs/files 并做发布前检查。"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"


def test_pages_workflow_outputs_brief_into_docs_files():
    text = PAGES_WORKFLOW.read_text(encoding="utf-8")
    # DOCX 直接生成到 docs/files，随 docs 目录一起部署
    assert "docs/files/PsyLens_project_brief.docx" in text
    # 不再只生成到 artifacts 临时目录
    assert "--output artifacts/PsyLens_project_brief.docx" not in text


def test_pages_workflow_checks_brief_before_upload():
    text = PAGES_WORKFLOW.read_text(encoding="utf-8")
    # 上传前校验 DOCX 存在且体积达标
    assert "st_size > 10000" in text
    assert "upload-pages-artifact" in text
