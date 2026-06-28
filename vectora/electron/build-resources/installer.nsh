; Customizações do instalador NSIS.
;
; ManifestDPIAware true: marca o stub como DPI-aware — sem isso o Windows
; escala a janela em telas HiDPI e o texto fica borrado.
;
; PATH: adiciona $INSTDIR\resources\vectora-core ao PATH do usuário para que
; o comando `vectora` fique disponível no shell após a instalação,
; igual ao `code` do VS Code e ao `node` do Node.js.

!macro customHeader
  ManifestDPIAware true
!macroend

!macro customInstall
  ; Adiciona resources\vectora-core ao PATH do usuário (HKCU, sem admin).
  EnVar::AddValue "PATH" "$INSTDIR\resources\vectora-core"
  Pop $0
!macroend

!macro customUnInstall
  ; Remove do PATH na desinstalação.
  EnVar::DeleteValue "PATH" "$INSTDIR\resources\vectora-core"
  Pop $0
!macroend
