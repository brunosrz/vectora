; Customizações do instalador NSIS (electron-builder lê este arquivo via
; directories.buildResources + nsis.include).
;
; ManifestDPIAware true marca o stub do instalador como DPI-aware. Sem isso o
; Windows escala o bitmap da janela em telas HiDPI e o texto fica borrado.
; Precisa ser declarado no header (antes das seções) — daí o hook customHeader.
!macro customHeader
  ManifestDPIAware true
!macroend
