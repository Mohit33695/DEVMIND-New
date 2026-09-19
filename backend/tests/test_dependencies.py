"""
Unit and API integration tests for Repository Dependency Intelligence.
"""

import io
import os
import shutil
import zipfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.dependencies import DependencyType, ResolutionStatus
from app.services.dependency import CodeDependencyService
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService

client = TestClient(app)


def create_sample_zip(files_map: dict) -> bytes:
    """Helper utility to create a zip file buffer from a filename -> content dict."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_map.items():
            if isinstance(content, bytes):
                zf.writestr(filename, content)
            else:
                zf.writestr(filename, str(content))
    return buffer.getvalue()


def test_python_internal_import_resolution():
    """1. Python internal import resolution."""
    files = {
        "src/main.py": "from services import UserService\n",
        "src/services.py": "class UserService:\n    pass\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        main_deps = [d for d in res.dependencies if d.source_file == "src/main.py"]

        assert len(main_deps) == 1
        assert main_deps[0].target_file == "src/services.py"
        assert main_deps[0].dependency_type == DependencyType.INTERNAL
        assert main_deps[0].resolution_status == ResolutionStatus.RESOLVED
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_python_relative_import_resolution():
    """2. Python relative import resolution."""
    files = {
        "src/controllers/user.py": "from ..models import User\n",
        "src/models.py": "class User:\n    pass\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        user_deps = [d for d in res.dependencies if d.source_file == "src/controllers/user.py"]

        assert len(user_deps) == 1
        assert user_deps[0].target_file == "src/models.py"
        assert user_deps[0].dependency_type == DependencyType.INTERNAL
        assert user_deps[0].resolution_status == ResolutionStatus.RESOLVED
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_python_unresolved_relative_import():
    """3. Python unresolved relative import."""
    files = {
        "src/main.py": "from .missing import NonExistentClass\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        main_deps = [d for d in res.dependencies if d.source_file == "src/main.py"]

        assert len(main_deps) == 1
        assert main_deps[0].target_file is None
        assert main_deps[0].dependency_type == DependencyType.INTERNAL
        assert main_deps[0].resolution_status == ResolutionStatus.UNRESOLVED
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_js_relative_import():
    """4. JavaScript relative import."""
    files = {
        "src/app.js": "import { format } from './utils';\n",
        "src/utils.js": "export function format() {}\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        app_deps = [d for d in res.dependencies if d.source_file == "src/app.js"]

        assert len(app_deps) == 1
        assert app_deps[0].target_file == "src/utils.js"
        assert app_deps[0].dependency_type == DependencyType.INTERNAL
        assert app_deps[0].resolution_status == ResolutionStatus.RESOLVED
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_ts_relative_import():
    """5. TypeScript relative import."""
    files = {
        "src/views/Home.ts": "import { Button } from '../components/Button';\n",
        "src/components/Button.ts": "export class Button {}\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        home_deps = [d for d in res.dependencies if d.source_file == "src/views/Home.ts"]

        assert len(home_deps) == 1
        assert home_deps[0].target_file == "src/components/Button.ts"
        assert home_deps[0].dependency_type == DependencyType.INTERNAL
        assert home_deps[0].resolution_status == ResolutionStatus.RESOLVED
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_ts_alias_src_resolution():
    """6. TypeScript @/src alias."""
    files = {
        "src/pages/App.tsx": "import { Card } from '@/components/Card';\n",
        "src/components/Card.tsx": "export const Card = () => null;\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        app_deps = [d for d in res.dependencies if d.source_file == "src/pages/App.tsx"]

        assert len(app_deps) == 1
        assert app_deps[0].target_file == "src/components/Card.tsx"
        assert app_deps[0].dependency_type == DependencyType.INTERNAL
        assert app_deps[0].resolution_status == ResolutionStatus.RESOLVED
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_ts_js_extension_probing():
    """7. JS/TS extension probing (.ts, .tsx, .js, .jsx)."""
    files = {
        "src/index.ts": "import './helper';\n",
        "src/helper.tsx": "export const Helper = () => null;\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        index_deps = [d for d in res.dependencies if d.source_file == "src/index.ts"]

        assert len(index_deps) == 1
        assert index_deps[0].target_file == "src/helper.tsx"
        assert index_deps[0].dependency_type == DependencyType.INTERNAL
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_index_file_resolution():
    """8. index.ts/index.tsx/index.js/index.jsx resolution."""
    files = {
        "src/app.ts": "import { api } from './services';\n",
        "src/services/index.ts": "export const api = {};\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        app_deps = [d for d in res.dependencies if d.source_file == "src/app.ts"]

        assert len(app_deps) == 1
        assert app_deps[0].target_file == "src/services/index.ts"
        assert app_deps[0].dependency_type == DependencyType.INTERNAL
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_java_package_import_resolution():
    """9. Java package import resolution."""
    files = {
        "src/main/java/com/devmind/Main.java": "package com.devmind;\nimport com.devmind.services.UserService;\npublic class Main {}\n",
        "src/main/java/com/devmind/services/UserService.java": "package com.devmind.services;\npublic class UserService {}\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        main_deps = [d for d in res.dependencies if d.source_file == "src/main/java/com/devmind/Main.java"]

        assert len(main_deps) == 1
        assert main_deps[0].target_file == "src/main/java/com/devmind/services/UserService.java"
        assert main_deps[0].dependency_type == DependencyType.INTERNAL
        assert main_deps[0].resolution_status == ResolutionStatus.RESOLVED
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_go_stdlib_classification():
    """10. Go standard-library classification."""
    files = {
        "main.go": "package main\nimport \"fmt\"\nfunc main() {}\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        go_deps = [d for d in res.dependencies if d.source_file == "main.go"]

        assert len(go_deps) == 1
        assert go_deps[0].module_name == "fmt"
        assert go_deps[0].dependency_type == DependencyType.EXTERNAL
        assert go_deps[0].resolution_status == ResolutionStatus.EXTERNAL
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_go_internal_package_resolution():
    """11. Go internal package resolution."""
    files = {
        "cmd/main.go": "package main\nimport \"github.com/myorg/repo/pkg/user\"\nfunc main() {}\n",
        "pkg/user/user.go": "package user\ntype User struct{}\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        main_deps = [d for d in res.dependencies if d.source_file == "cmd/main.go"]

        assert len(main_deps) == 1
        assert main_deps[0].target_file == "pkg/user/user.go"
        assert main_deps[0].dependency_type == DependencyType.INTERNAL
        assert main_deps[0].resolution_status == ResolutionStatus.RESOLVED
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_external_dependency_classification():
    """12. External dependency classification."""
    files = {
        "src/main.py": "import os\nimport fastapi\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        ext_deps = [d for d in res.dependencies if d.dependency_type == DependencyType.EXTERNAL]

        assert len(ext_deps) == 2
        mod_names = {d.module_name for d in ext_deps}
        assert "os" in mod_names
        assert "fastapi" in mod_names
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_unknown_dependency_classification():
    """13. Unknown dependency classification."""
    files = {
        "src/main.py": "import custom_unresolvable_internal_pkg_foo_bar\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        unk_deps = [d for d in res.dependencies if d.source_file == "src/main.py"]

        assert len(unk_deps) == 1
        assert unk_deps[0].dependency_type == DependencyType.UNKNOWN
        assert unk_deps[0].resolution_status == ResolutionStatus.UNRESOLVED
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_circular_dependency_ab_ba():
    """14. Circular dependency A -> B -> A."""
    files = {
        "src/a.py": "from .b import B\n",
        "src/b.py": "from .a import A\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)

        assert res.has_circular_dependencies is True
        assert len(res.circular_dependency_cycles) == 1
        cycle = res.circular_dependency_cycles[0]
        assert cycle[0] == "src/a.py"
        assert cycle[1] == "src/b.py"
        assert cycle[2] == "src/a.py"
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_circular_dependency_abc_ca():
    """15. Circular dependency A -> B -> C -> A."""
    files = {
        "src/a.py": "from .b import B\n",
        "src/b.py": "from .c import C\n",
        "src/c.py": "from .a import A\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)

        assert res.has_circular_dependencies is True
        assert len(res.circular_dependency_cycles) == 1
        cycle = res.circular_dependency_cycles[0]
        assert cycle == ["src/a.py", "src/b.py", "src/c.py", "src/a.py"]
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_duplicate_imports_handling():
    """16. Duplicate imports handling."""
    files = {
        "src/app.ts": "import { a } from './utils';\nimport { b } from './utils';\n",
        "src/utils.ts": "export const a = 1;\nexport const b = 2;\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        app_deps = [d for d in res.dependencies if d.source_file == "src/app.ts"]

        # Duplicate line imports or distinct line imports should be preserved deterministically
        assert len(app_deps) >= 1
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_nonexistent_repository_404():
    """17. Nonexistent repository -> 404."""
    response = client.get("/api/repositories/nonexistent-repo-99999/dependencies")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_deterministic_dependency_ordering():
    """18. Deterministic dependency ordering."""
    files = {
        "z_file.py": "import os\n",
        "a_file.py": "import sys\nimport os\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        source_order = [d.source_file for d in res.dependencies]

        # a_file.py should precede z_file.py
        assert source_order[0] == "a_file.py"
        assert source_order[1] == "a_file.py"
        assert source_order[2] == "z_file.py"
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_deterministic_cycle_ordering():
    """19. Deterministic cycle ordering."""
    files = {
        "src/a.py": "from .b import B\n",
        "src/b.py": "from .a import A\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res1 = CodeDependencyService.analyze_repository_dependencies(repo_id)
        res2 = CodeDependencyService.analyze_repository_dependencies(repo_id)

        assert res1.circular_dependency_cycles == res2.circular_dependency_cycles
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_ignored_directories_excluded():
    """20. Ignored directories are excluded."""
    files = {
        "src/app.py": "import helper\n",
        "src/helper.py": "pass\n",
        "node_modules/package/index.js": "import other from './other';\n",
        "node_modules/package/other.js": "export default 1;\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeDependencyService.analyze_repository_dependencies(repo_id)
        all_sources = {d.source_file for d in res.dependencies}

        assert "src/app.py" in all_sources
        assert not any(s.startswith("node_modules") for s in all_sources)
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)
