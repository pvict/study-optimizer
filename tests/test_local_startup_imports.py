"""Abertura da página não deve preparar gráficos ou extração de PDFs."""
import subprocess
import sys


def test_initial_ui_does_not_load_unused_graphs_or_pdf_extractor():
    result = subprocess.run([sys.executable, '-c', '''
import sys
import osler.ui
unused = ['altair', 'pymupdf', 'osler.study_evolution_ui', 'osler.planning_ui']
assert not [name for name in unused if name in sys.modules], [name for name in unused if name in sys.modules]
'''], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
