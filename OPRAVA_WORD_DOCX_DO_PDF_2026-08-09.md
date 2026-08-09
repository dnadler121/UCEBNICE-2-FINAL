# Word náhled: DOCX → PDF → iframe

- Učitelský DOCX i studentův DOCX se pro náhled převádí přes LibreOffice/soffice přímo na PDF.
- PDF se zobrazuje inline v existujícím okně na stránce; nic se nestahuje.
- Odstraněn Python/HTML fallback, který měnil rozložení, češtinu, obsah a bibliografii.
- Hodnocení a kontroly souboru zůstávají beze změny.
- Server musí mít LibreOffice/soffice v PATH.
