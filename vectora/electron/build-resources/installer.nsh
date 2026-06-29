; Customizações do instalador NSIS.
;
; ManifestDPIAware true: marca o stub como DPI-aware — sem isso o Windows
; escala a janela em telas HiDPI e o texto fica borrado.

!macro customHeader
  ManifestDPIAware true
!macroend

!macro customInstall
!macroend

!macro customUnInstall
!macroend
