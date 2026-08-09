#!/usr/bin/env bash
set -e
pip install -r requirements.txt
if ! command -v libreoffice >/dev/null 2>&1 && ! command -v soffice >/dev/null 2>&1; then
  echo "LibreOffice není v systémovém obrazu. Pro přesné DOCX→PDF náhledy musí být LibreOffice dostupný v runtime."
fi
