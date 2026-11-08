# Chooses the Python interpreter for ~/.md2pdf-venv. Sourced by install.sh.
#
# We can't just use whatever `python3` is: faster-whisper's PyAV dependency lags
# new Python releases (no 3.15 wheels as of 2026-11, and the source build fails),
# and Homebrew deletes old versions on upgrade, leaving a venv with a dangling
# interpreter. So we try known-good versions in order of preference.
# Override with e.g. MD2PDF_PYTHON_VERSIONS="3.12 3.13".

PYTHON_VERSIONS="${MD2PDF_PYTHON_VERSIONS:-3.13 3.12 3.14}"

find_venv_python() {  # prints path of first python3.X on PATH from PYTHON_VERSIONS
    local version
    for version in $PYTHON_VERSIONS; do
        command -v "python$version" && return 0
    done
    return 1
}
