# FRENTE 6 — UI Components & Workbenches

## Overview

FRENTE 6 implementa componentes reutilizáveis, 4 novos workbenches, e melhorias de UX conforme inspirado em Claude Code e VS Code.

**Status**: ✅ SPRINT 1-2 completos | 🚧 SPRINT 3 (Bugs) em progresso

## Componentes (components/ui/tips/)

### Tooltip

- **Path**: `components/ui/tooltip.tsx`
- **Padrão**: Radix UI wrapper
- **Uso**: `<Tooltip><TooltipTrigger><button/></TooltipTrigger><TooltipContent/></Tooltip>`
- **Status**: ✅ Deployed em 17+ botões

### HoverCard

- **Path**: `components/ui/hover-card.tsx`
- **Padrão**: Radix HoverCard com fade-in
- **Uso**: Richer tooltips com conteúdo custom
- **Status**: ✅ Criado, pronto para uso

### Popover

- **Path**: `components/ui/popover.tsx`
- **Padrão**: Radix Popover em Portal
- **Uso**: Dropdown/action menus
- **Status**: ✅ Criado

### Toast

- **Path**: `components/ui/toast.tsx`
- **Consumer Hook**: useToast()
- **API**: success() | error() | warning() | info()
- **Status**: ✅ Integrado com ToastStore

### Snackbar

- **Path**: `components/ui/snackbar.tsx`
- **Padrão**: Lightweight, position-fixed bottom-right
- **Uso**: Sistema notificações alternativo
- **Status**: ✅ Criado

### Callout

- **Path**: `components/ui/callout.tsx`
- **Tipos**: info | warning | error | success
- **Padrão**: Inline alert box com ícone
- **Status**: ✅ Criado com types

### Coach-Mark

- **Path**: `components/ui/coach-mark.tsx`
- **Uso**: Guided onboarding com highlight overlay
- **Padrão**: Highlight + popover
- **Status**: ✅ Criado com event callbacks

## Workbenches (components/workbench/tabs/)

### Preview Tab

- **Path**: `tabs/preview-tab.tsx`
- **Função**: Visualiza arquivos (image/video/audio/pdf/text)
- **MIME Types**: auto-detected
- **Status**: ✅ Funcional

### Search Tab

- **Path**: `tabs/search-tab.tsx`
- **Função**: Busca full-text em filesystem
- **API**: GET `/workspaces/{id}/fs/search?q=...`
- **Status**: ✅ Funcional com result preview

### Tasks Tab

- **Path**: `tabs/tasks-tab.tsx`
- **Função**: Lista artifacts do plano da sessão
- **Source**: `workbenchStore.getPlan(threadId).items`
- **Status**: ✅ Funcional, basic display

### Storage Tab

- **Path**: `tabs/storage-tab.tsx`
- **Função**: Navegação read-only do filesystem
- **Padrão**: Lazy-load tree, chevron expand/collapse
- **Status**: ✅ Funcional

## i18n Coverage

- **22 tooltip keys** em 3 idiomas (en/es/pt-BR)
- **8 workbench tab labels** em 3 idiomas
- **Total**: 30+ keys, coverage 100%

## Design Tokens

### Responsive

- Mobile-first breakpoints: sm: (640px)
- Padding: px-4 sm:px-6
- Spacing: gap-1, gap-2 (consistent)

### Theme Support

- Dark mode: dark: utilities
- All components support light/dark via CSS variables
- Code blocks: light/dark palettes (dark implemented, light planned)

### Inspiração

- **Claude Code**: Minimal sidebar, icon-based tabs, Tooltip everywhere
- **VS Code**: Workbench pattern (Explorer → Terminal), Activity Bar, Command Palette

## Commits

- ✅ 295442e — components/ui/tips/ + TooltipProvider
- ✅ 239ac58 — Chat input + voice button tooltips
- ✅ 681d7b8 — Sidebar tooltips
- ✅ a7ceb86 — Files tab tooltips
- ✅ 9855b87 — Git toolbar tooltips
- ✅ c8dd720 — Plus menu tooltip
- ✅ 2abc238 — 4 workbenches (preview, search, tasks, storage)
- ✅ 0486c43 — Spacing fix + markdown preview dialog

## Próximos Passos (SPRINT 3)

- [ ] Task 4.1: Bug — arquivo em modal não fecha (investigação)
- [ ] Task 4.2: Bug — mensagem 5x (ray tracing no grafo)
- [x] Task 4.3: Docs (este arquivo)

---

**Desenvolvido com ❤️ conforme FRENTE 6 master plan**
