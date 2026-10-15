# Minimal makefile for Sphinx documentation (set PYTHONPATH/EYESWEB_CORE_PATH as in the top of conf.py).
SPHINXOPTS  ?= -W --keep-going
SPHINXBUILD ?= python -m sphinx
SOURCEDIR   = .
BUILDDIR    = _build

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
