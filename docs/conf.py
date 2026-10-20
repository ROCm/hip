# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import re
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from rocm_docs import ROCmDocs

version_numbers = []
version_file = open("../VERSION", "r")
lines = version_file.readlines()
for line in lines:
    if line[0] == '#':
        continue
    version_numbers.append(line.strip())
version_number = ".".join(version_numbers)
left_nav_title = f"HIP {version_number} Documentation"

# for PDF output on Read the Docs
project = "HIP Documentation"
author = "Advanced Micro Devices, Inc."
copyright = "Copyright (c) 2023 Advanced Micro Devices, Inc. All rights reserved."
version = version_number
release = version_number

external_toc_path = "./sphinx/_toc.yml"

docs_core = ROCmDocs(left_nav_title)
docs_core.run_doxygen(doxygen_root="doxygen", doxygen_path="doxygen/xml")


def _fix_empty_sectiondef_kind(xml_dir: Path) -> None:
    """Give friend/related group sections a kind breathe will accept.

    Doxygen cannot assign a section kind to friend and related members that are
    pulled into a group, so it writes `<sectiondef kind="">`. breathe 4.x
    ignored the empty value; breathe 5.x validates it against DoxSectionKind and
    aborts the whole build with

        ParserError: group___cooperative_g.xml:279:
            "" is not one of the allowed enumeration values

    `friend` is a valid DoxSectionKind and is what these members are, so rewrite
    the attribute before breathe reads the file. Checked against doxygen 1.9.8
    (what Read the Docs installs), 1.12.0 and 1.14.0 - all three emit the empty
    kind, so this is not fixed by moving to a newer doxygen. HIDE_FRIEND_COMPOUNDS
    does not help either, as the same section also holds related functions.

    Remove once breathe tolerates the value doxygen actually emits.
    """
    scanned = patched = 0
    for xml_file in sorted(xml_dir.glob("*.xml")):
        scanned += 1
        text = xml_file.read_text(encoding="utf-8")
        if '<sectiondef kind="">' not in text:
            continue
        xml_file.write_text(
            text.replace('<sectiondef kind="">', '<sectiondef kind="friend">'),
            encoding="utf-8",
        )
        patched += 1
    # Always report, including zero. A silent no-op here looks exactly like a
    # working fix until breathe fails much later in the build.
    print(
        f"conf.py: gave a kind to empty <sectiondef> in {patched} of {scanned} "
        f"doxygen XML file(s) in {xml_dir}"
    )


def setup(app):
    """Patch the doxygen XML after it is written and before breathe reads it.

    This cannot be a plain call at the bottom of conf.py: rocm_docs.doxygen runs
    doxygen from a config-inited handler (priority 400), so while conf.py is
    executing the XML directory does not exist yet and there is nothing to
    patch. builder-inited runs after every config-inited handler and before
    source reading, which is when breathe parses the files.

    The paths come from breathe_projects, which rocm_docs.doxygen populates in
    that same config-inited handler, so this patches exactly the directories
    breathe is going to read.
    """

    def _patch_doxygen_xml(app_) -> None:
        for xml_dir in app_.config.breathe_projects.values():
            _fix_empty_sectiondef_kind(Path(xml_dir))

    app.connect("builder-inited", _patch_doxygen_xml)


docs_core.enable_api_reference()
docs_core.setup()

external_projects_current_project = "hip"

# Generate llms.txt and llms-full.txt (requires the rocm-docs-core[llms] extra).
rocm_docs_generate_llms = True

for sphinx_var in ROCmDocs.SPHINX_VARS:
    globals()[sphinx_var] = getattr(docs_core, sphinx_var)

# Enable the per-page Markdown download button.
html_theme_options.update({
    "repository_url": "https://github.com/ROCm/rocm-systems",
    "path_to_docs": "projects/hip/docs",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_download_button": True,
})

# Add the _extensions directory to Python's search path
sys.path.append(str(Path(__file__).parent / 'extension'))

extensions += ["sphinxcontrib.doxylink", "custom_directive"]

cpp_id_attributes = ["__global__", "__device__", "__host__", "__forceinline__", "static"]
cpp_paren_attributes = ["__declspec"]

suppress_warnings = ["etoc.toctree"]

numfig = False

html_static_path = ["sphinx/static/css"]
html_css_files = ["rocm_custom.css"]

exclude_patterns = [
    "./doxygen/mainpage.md",
    "./understand/glossary.md",
    './how-to/debugging_env.rst',
    "./reference/env_variables"
]
