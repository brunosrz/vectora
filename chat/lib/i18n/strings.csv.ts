/**
 * Vectora Chat — Translation strings
 *
 * Formato CSV: key,en,es,pt
 * Para adicionar um idioma: adicione uma coluna aqui E atualize o tipo Lang
 * em chat/lib/stores/settings-store.ts.
 *
 * Regras de edição:
 *  - Valores com vírgula ou aspas devem estar entre aspas duplas: "valor, com vírgula"
 *  - Aspas dentro de valores: duplique-as: "diga ""isso"""
 *  - Interpolação: {varName}  ex: "há {n} min" → t('key', { n: 5 })
 *  - Linhas iniciando com # são comentários (ignoradas pelo parser)
 */

const CSV = `\
key,en,es,pt
# =============================================================================
# Layout / Navegação
# =============================================================================
header.new_chat,New Chat,Nuevo Chat,Novo Chat
sidebar.title,Threads,Conversaciones,Conversas
sidebar.search_placeholder,Search threads...,Buscar conversaciones...,Buscar conversas...
sidebar.clear_search,Clear search,Limpiar búsqueda,Limpar busca
sidebar.group.today,Today,Hoy,Hoje
sidebar.group.yesterday,Yesterday,Ayer,Ontem
sidebar.group.last_7_days,Previous 7 Days,Últimos 7 días,Últimos 7 dias
sidebar.group.older,Older,Anteriores,Mais antigo
sidebar.new_conversation,New conversation,Nueva conversación,Nova conversa
sidebar.no_conversations,No conversations yet,Aún no hay conversaciones,Nenhuma conversa ainda
sidebar.no_conversations_hint,Start chatting to see your threads here!,¡Empieza a chatear para ver tus conversaciones!,Comece a conversar para ver suas threads aqui!
sidebar.no_results,No results found,No se encontraron resultados,Nenhum resultado encontrado
sidebar.no_results_hint,Try a different search term,Intenta con otro término,Tente outro termo de busca
sidebar.documentation,Documentation,Documentación,Documentação
sidebar.documentation_caption,GitHub · Vectora,GitHub · Vectora,GitHub · Vectora
sidebar.feedback,Feedback,Comentarios,Feedback
sidebar.report_issue,Report an issue,Reportar problema,Reportar problema
# =============================================================================
# Relative time (sidebar)
# =============================================================================
time.just_now,Just now,Ahora mismo,Agora mesmo
time.minutes_ago,{n} min ago,hace {n} min,há {n} min
time.hour_ago,1 hour ago,hace 1 hora,há 1 hora
time.hours_ago,{n} hours ago,hace {n} horas,há {n} horas
time.yesterday,Yesterday,Ayer,Ontem
time.days_ago,{n} days ago,hace {n} días,há {n} dias
time.week_ago,1 week ago,hace 1 semana,há 1 semana
time.weeks_ago,{n} weeks ago,hace {n} semanas,há {n} semanas
time.month_ago,1 month ago,hace 1 mes,há 1 mês
time.months_ago,{n} months ago,hace {n} meses,há {n} meses
# =============================================================================
# Welcome screen
# =============================================================================
welcome.title,What can I help with?,¿En qué puedo ayudarte?,O que posso fazer por você?
welcome.drop_files,Drop files here,Suelta archivos aquí,Solte arquivos aqui
# =============================================================================
# Chat input
# =============================================================================
input.placeholder,Ask me anything...,Pregúntame lo que quieras...,Pergunte-me qualquer coisa...
input.initializing,Initializing...,Iniciando...,Iniciando...
input.loading_placeholder,Type your next message...,Escribe tu siguiente mensaje...,Digite sua próxima mensagem...
input.drop_files,Drop files here,Suelta archivos aquí,Solte arquivos aqui
input.attach_files,"Attach files (images, code, logs)","Adjuntar archivos (imágenes, código, registros)","Anexar arquivos (imagens, código, logs)"
input.stop,Stop,Detener,Parar
input.stopping,Stopping...,Deteniendo...,Parando...
input.stop_generating,Stop generating,Detener generación,Parar geração
input.send_hint,to send,para enviar,para enviar
input.new_line_hint,new line,nueva línea,nova linha
input.queued,Queued,En cola,Na fila
# =============================================================================
# Mensagens
# =============================================================================
message.copy,Copy,Copiar,Copiar
message.copied,Copied,Copiado,Copiado
message.regenerate,Regenerate,Regenerar,Regenerar
message.good,Good,Bueno,Bom
message.bad,Bad,Malo,Ruim
message.feedback,Feedback,Comentarios,Feedback
message.retry,Try again,Intentar de nuevo,Tentar novamente
message.feedback_placeholder,Add feedback about this response...,Añade comentarios sobre esta respuesta...,Adicione feedback sobre esta resposta...
message.feedback_hint,Select thumbs up or down before submitting,Selecciona arriba o abajo antes de enviar,Selecione positivo ou negativo antes de enviar
message.thinking,Reasoning,Razonamiento,Raciocínio
message.copy_code,Copy code to clipboard,Copiar código al portapapeles,Copiar código para área de transferência
message.agent_steps,Agent steps,Pasos del agente,Passos do agente
message.running,Running...,Ejecutando...,Executando...
message.complete,Complete,Completo,Completo
message.waiting_output,Waiting for output...,Esperando salida...,Aguardando saída...
message.click_edit,Click to edit and rerun from here,Clic para editar y volver a ejecutar,Clique para editar e reexecutar a partir daqui
message.subagent_outputs,Subagent Outputs ({n}),Salidas del subagente ({n}),Saídas do subagente ({n})
# =============================================================================
# Thinking action types
# =============================================================================
thinking.direct,Direct response,Respuesta directa,Resposta direta
thinking.delegate,Delegating to agent,Delegando al agente,Delegando para agente
thinking.web_search,Web search,Búsqueda web,Busca na web
thinking.docs,Document search,Consulta de documentos,Consulta de documentos
thinking.coding,Writing code,Escribiendo código,Escrevendo código
# =============================================================================
# Tool calls / Scroll
# =============================================================================
tool.executing,executing…,ejecutando…,executando…
scroll.back_to_bottom,Back to bottom,Volver al final,Voltar ao fim
# =============================================================================
# Chat settings (agent-settings.tsx)
# =============================================================================
settings.chat.tooltip,Chat settings,Configuración del chat,Configurações do chat
settings.chat.title,Chat Settings,Configuración del chat,Configurações do Chat
settings.chat.description,"Customizes the behavior of this chat session.","Personaliza el comportamiento de esta sesión de chat.","Personaliza o comportamento desta sessão de chat."
settings.chat.model,Model,Modelo,Modelo
settings.chat.model_placeholder,Select model,Seleccionar modelo,Selecionar modelo
settings.chat.verbosity,Response verbosity,Verbosidad de las respuestas,Verbosidade das respostas
settings.chat.verbosity.concise,Concise,Concisa,Concisa
settings.chat.verbosity.normal,Normal,Normal,Normal
settings.chat.verbosity.detailed,Detailed,Detallada,Detalhada
settings.chat.tools_section,Tools,Herramientas,Ferramentas
settings.chat.show_tool_calls,Show tool calls in chat,Mostrar llamadas de herramientas,Mostrar tool calls no chat
settings.chat.show_tool_calls_hint,Shows tool calls during the response.,Muestra las llamadas de herramientas durante la respuesta.,Exibe as chamadas de ferramentas durante a resposta.
settings.chat.confirm_destructive,Confirm destructive actions,Confirmar acciones destructivas,Confirmar ações destrutivas
settings.chat.confirm_destructive_hint,"Asks for confirmation before running irreversible tools (file write, terminal, etc).","Pide confirmación antes de ejecutar herramientas irreversibles (escritura de archivo, terminal, etc).","Pede confirmação antes de executar ferramentas irreversíveis (escrita de arquivo, terminal, etc)."
settings.chat.keyboard_shortcuts,View keyboard shortcuts,Ver atajos de teclado,Ver atalhos de teclado
# =============================================================================
# Settings dialog
# =============================================================================
settings.dialog.title,Settings,Ajustes,Configurações
settings.tab.account,Account,Cuenta,Conta
settings.tab.preferences,Preferences,Preferencias,Preferências
settings.tab.memory,Memory,Memoria,Memória
settings.tab.integrations,Integrations,Integraciones,Integrações
settings.tab.envs,Envs,Envs,Envs
settings.tab.admin,Administration,Administración,Administração
# =============================================================================
# Account tab
# =============================================================================
account.no_user,No authenticated user.,Ningún usuario autenticado.,Nenhum usuário autenticado.
account.security,Security,Seguridad,Segurança
account.change_password,Change password,Cambiar contraseña,Alterar senha
account.coming_soon,Coming soon,Próximamente,Em breve
account.role.root,Root,Root,Root
account.role.admin,Admin,Admin,Admin
account.role.member,Member,Miembro,Membro
account.role.viewer,Viewer,Visualizador,Visualizador
# =============================================================================
# Preferences tab
# =============================================================================
prefs.theme,Interface theme,Tema de interfaz,Tema da interface
prefs.theme.system,"System (automatic)","Sistema (automático)","Sistema (automático)"
prefs.theme.light,Light,Claro,Claro
prefs.theme.dark,Dark,Oscuro,Escuro
prefs.history_limit,History limit,Límite de historial,Limite do histórico
prefs.history_limit_unit,messages,mensajes,mensagens
prefs.history_limit_help,"Maximum number of messages displayed per thread (default: 50).","Número máximo de mensajes por conversación (predeterminado: 50).","Número máximo de mensagens exibidas por thread (padrão: 50)."
prefs.custom_prompt,Custom instruction,Instrucción personalizada,Instrução personalizada
prefs.custom_prompt_placeholder,"E.g.: Always respond in bullet points. Be concise.","Ej: Responde siempre con viñetas. Sé conciso.","Ex: Responda sempre em bullet points. Seja conciso."
prefs.custom_prompt_help,"Text prefixed to the agent's system prompt in all conversations. Leave blank to use default behavior.","Texto prefijado al prompt del sistema. Déjelo en blanco para usar el comportamiento predeterminado.","Texto prefixado ao system prompt do agente. Deixe em branco para usar o comportamento padrão."
prefs.language,Language,Idioma,Idioma
prefs.language.en,English,English,English
prefs.language.es,Español,Español,Español
prefs.language.pt,Português,Português,Português
# =============================================================================
# HITL panel
# =============================================================================
hitl.title,Action requires approval,La acción requiere aprobación,Ação requer aprovação
hitl.show_args,Show arguments,Ver argumentos,Ver argumentos
hitl.hide_args,Hide,Ocultar,Ocultar
hitl.edit_instruction,"Edit the arguments in JSON before running:","Edita los argumentos en JSON antes de ejecutar:","Edite os argumentos em JSON antes de executar:"
hitl.json_error,"Invalid JSON — check the syntax before submitting.","JSON no válido — verifique la sintaxis antes de enviar.","JSON inválido — verifique a sintaxe antes de enviar."
hitl.approve,Approve,Aprobar,Aprovar
hitl.edit,Edit,Editar,Editar
hitl.reject,Reject,Rechazar,Rejeitar
hitl.submit_edited,Run edited,Ejecutar editado,Executar editado
hitl.cancel_edit,Cancel edit,Cancelar edición,Cancelar edição
# =============================================================================
# User menu
# =============================================================================
user.menu_label,User menu,Menú de usuario,Menu do usuário
user.settings,Settings,Ajustes,Configurações
user.admin,Administration,Administración,Administração
user.logout,Sign out,Cerrar sesión,Sair
# =============================================================================
# Keyboard shortcuts / Auth
# =============================================================================
shortcuts.title,Keyboard Shortcuts,Atajos de teclado,Atalhos de teclado
auth.loading,Loading...,Cargando...,Carregando...
# =============================================================================
# Voice input
# =============================================================================
voice.stop_listening,Stop listening,Dejar de escuchar,Parar de escutar
voice.start_listening,Voice input,Entrada de voz,Entrada de voz
`;

export default CSV;
