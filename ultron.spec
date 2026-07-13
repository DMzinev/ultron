# =============================================================================
# ultron.spec — PyInstaller build specification for Ultron Server
#
# Build command (run from the repo root):
#   pyinstaller ultron.spec
#
# Output:  dist/ultron-server.exe   (single-file, windowed, no console)
#
# Prerequisites:
#   pip install pyinstaller
#
# Notes:
# - This bundles the HTTP server (ultron/interfaces/server.py) as the entry
#   point. The tray launcher (launcher/tray_launcher.py) spawns this exe as
#   a subprocess and is packaged separately (it stays as a Python script).
# - hiddenimports covers both the top-level imports at lines 10–20 of
#   server.py AND the five lazily-imported modules inside handler methods
#   (lines 544, 561–563, 862) that PyInstaller cannot detect statically.
# - The ultron/.ultron/ data directory is included only if it exists at
#   build time; remove it from datas[] if the directory is absent.
# =============================================================================

import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# ---------------------------------------------------------------------------
# Paths (relative to repo root, where this spec lives)
# ---------------------------------------------------------------------------
ROOT     = os.path.dirname(os.path.abspath(SPEC))
WEB_SRC  = os.path.join(ROOT, "ultron", "interfaces", "web")
CFG_SRC  = os.path.join(ROOT, "ultron", ".ultron")

datas = [
    (WEB_SRC, os.path.join("ultron", "interfaces", "web")),
]

# Include stored config directory only if it already exists at build time
if os.path.isdir(CFG_SRC):
    datas.append((CFG_SRC, os.path.join("ultron", ".ultron")))

# ---------------------------------------------------------------------------
# Hidden imports — every ultron submodule imported in server.py
# (top-level static imports + inline lazy imports inside handler methods)
# ---------------------------------------------------------------------------
hidden = [
    # Top-level imports (server.py lines 10–20)
    "ultron.core.analyzer",
    "ultron.core.risk",
    "ultron.core.prompt",
    "ultron.core.classifier",
    "ultron.core.predict",
    "ultron.core.pledge",
    "ultron.core.fuzz",
    "ultron.core.logistic",
    "ultron.core.translate",
    "ultron.experimental.delta",
    "ultron.experimental.design_oracle",
    # Inline lazy imports (server.py lines 544, 561–563, 862)
    "ultron.experimental.reasoning",
    "ultron.experimental.impact_simulator",
    "ultron.experimental.contract_generator",
    "ultron.experimental.knowledge_graph",
    "ultron.core.meta_layer",
    # radon (transitive dependency used by core modules)
    "radon.complexity",
    "radon.metrics",
    "radon.raw",
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [os.path.join(ROOT, "ultron", "interfaces", "server.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ultron-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # windowed — no visible terminal on Windows
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
