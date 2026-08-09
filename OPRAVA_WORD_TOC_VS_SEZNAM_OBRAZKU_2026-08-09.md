# Oprava Word: automatický obsah vs. seznam obrázků

Kontrola `word_toc` nově nerozpoznává pole Wordu `TOC \\c "Obrázek"` / `TOC \\a ...` jako běžný automatický obsah kapitol. Tato pole patří seznamům obrázků/tabulek a kontrolují se samostatně pomocí `word_list_figures`.

Ověřeno na souboru `test_student_2.docx`: `has_toc=False`, `has_list_of_figures=True`.
