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
sidebar.title,Sessions,Sesiones,Sessões
sidebar.search_placeholder,Search sessions...,Buscar sesiones...,Buscar sessões...
sidebar.clear_search,Clear search,Limpiar búsqueda,Limpar busca
sidebar.group.today,Today,Hoy,Hoje
sidebar.group.yesterday,Yesterday,Ayer,Ontem
sidebar.group.last_7_days,Previous 7 Days,Últimos 7 días,Últimos 7 dias
sidebar.group.older,Older,Anteriores,Mais antigo
sidebar.new_conversation,New conversation,Nueva conversación,Nova conversa
sidebar.no_conversations,No conversations yet,Aún no hay conversaciones,Nenhuma conversa ainda
sidebar.no_conversations_hint,Start chatting to see your sessions here!,¡Empieza a chatear para ver tus sesiones!,Comece a conversar para ver suas sessões aqui!
sidebar.no_results,No results found,No se encontraron resultados,Nenhum resultado encontrado
sidebar.no_results_hint,Try a different search term,Intenta con otro término,Tente outro termo de busca
sidebar.documentation,Documentation,Documentación,Documentação
sidebar.documentation_caption,GitHub · Vectora,GitHub · Vectora,GitHub · Vectora
sidebar.feedback,Feedback,Comentarios,Feedback
sidebar.report_issue,Report an issue,Reportar problema,Reportar problema
sidebar.open,Open sessions,Abrir sesiones,Abrir sessões
sidebar.folders,Folders,Carpetas,Pastas
sidebar.folders_empty,No folders yet. Ask the admin to add one.,Aún no hay carpetas. Pide al admin que agregue una.,Nenhuma pasta ainda. Peça ao admin para adicionar uma.
sidebar.group.other_conversations,Other conversations,Otras conversaciones,Outras conversas
sidebar.workspace_collapse,Collapse folder,Contraer carpeta,Recolher pasta
sidebar.workspace_expand,Expand folder,Expandir carpeta,Expandir pasta
sidebar.workspace_thread_count,{n} sessions,{n} sesiones,{n} sessões
# =============================================================================
# Feedback e estado assíncrono (SX-UX-1) — ErrorBanner, toasts de operação
# =============================================================================
error_banner.title,Something went wrong,Algo salió mal,Algo deu errado
error_banner.retry,Retry,Reintentar,Tentar novamente
error_banner.retrying,Retrying…,Reintentando…,Tentando novamente…
workspaces.error.hydrate,Couldn't load your workspaces.,No se pudieron cargar tus carpetas de trabajo.,Não foi possível carregar seus workspaces.
workspaces.error.create,Couldn't create the workspace.,No se pudo crear la carpeta de trabajo.,Não foi possível criar o workspace.
workspaces.error.trust,Couldn't trust this folder.,No se pudo confiar en esta carpeta.,Não foi possível confiar nesta pasta.
workspaces.error.git_init,Couldn't initialize the git repository.,No se pudo inicializar el repositorio git.,Não foi possível inicializar o repositório git.
threads.error.list,Couldn't load your conversations.,No se pudieron cargar tus conversaciones.,Não foi possível carregar suas conversas.
threads.error.rename,Couldn't save the new title.,No se pudo guardar el nuevo título.,Não foi possível salvar o novo título.
threads.error.delete,Couldn't delete the conversation.,No se pudo eliminar la conversación.,Não foi possível excluir a conversa.
# =============================================================================
# Resiliência de rede (SX-UX-2) — banner de status, reconexão SSE
# =============================================================================
network.offline_banner,No connection. Some actions are disabled until the network returns.,Sin conexión. Algunas acciones están deshabilitadas hasta que vuelva la red.,Sem conexão. Algumas ações estão desabilitadas até o retorno da rede.
network.reconnecting_banner,Reconnecting to the server…,Reconectando con el servidor…,Reconectando ao servidor…
network.sse_reconnected,Connection restored,Conexión restablecida,Conexão restabelecida
network.disabled_offline,Unavailable while offline,No disponible sin conexión,Indisponível sem conexão
chat.stream_interrupted,The previous response may have been interrupted (tab closed or reloaded mid-stream).,La respuesta anterior puede haberse interrumpido (la pestaña se cerró o recargó durante la transmisión).,A resposta anterior pode ter sido interrompida (aba fechada ou recarregada durante a geração).
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
# =============================================================================
# Envs tab
# =============================================================================
envs.title,Environment variables,Variables de entorno,Variáveis de ambiente
envs.subtitle,API keys and custom environment variables. They override the default values only for your requests.,Claves de API y variables de entorno personalizadas. Sobrescriben los valores predeterminados solo para tus solicitudes.,Chaves de API e variáveis de ambiente personalizadas. Substituem os valores padrão apenas para suas requisições.
envs.add,Add variable,Añadir variable,Adicionar variável
envs.empty,No variables configured yet,Aún no hay variables configuradas,Nenhuma variável configurada ainda
envs.key_label,Key,Clave,Chave
envs.value_label,Value,Valor,Valor
envs.key_placeholder,"e.g.: OPENAI_API_KEY","ej: OPENAI_API_KEY","ex: OPENAI_API_KEY"
envs.value_placeholder,Enter the value,Ingresa el valor,Digite o valor
envs.save,Save,Guardar,Salvar
envs.cancel,Cancel,Cancelar,Cancelar
envs.delete,Delete,Eliminar,Deletar
envs.add_title,Add environment variable,Añadir variable de entorno,Adicionar variável de ambiente
envs.add_desc,The value is stored encrypted and never returned to the browser.,El valor se almacena cifrado y nunca se devuelve al navegador.,O valor é armazenado criptografado e nunca retorna ao navegador.
envs.error_load,Error loading variables,Error al cargar variables,Erro ao carregar variáveis
envs.error_save,Error saving,Error al guardar,Erro ao salvar
envs.error_delete,Error deleting,Error al eliminar,Erro ao deletar
# =============================================================================
# Memory tab
# =============================================================================
memory.empty_title,No memories saved,Sin memorias guardadas,Nenhuma memória salva
memory.count_one,{n} memory,{n} memoria,{n} memória
memory.count_many,{n} memories,{n} memorias,{n} memórias
memory.subtitle,What Vectora learned about you in these conversations,Lo que Vectora aprendió sobre ti en estas conversaciones,O que o Vectora aprendeu sobre você nessas conversas
memory.add,Add,Añadir,Adicionar
memory.clear_all,Clear all,Limpiar todo,Limpar tudo
memory.edit,Edit,Editar,Editar
memory.save,Save,Guardar,Salvar
memory.cancel,Cancel,Cancelar,Cancelar
memory.delete,Delete,Eliminar,Deletar
memory.empty_hint,Vectora hasn't saved any memories about you yet,Vectora aún no guardó memorias sobre ti,O Vectora ainda não salvou memórias sobre você
memory.empty_hint2,Throughout conversations the agent saves relevant information to personalize future responses.,A lo largo de las conversaciones el agente guarda información relevante para personalizar futuras respuestas.,Ao longo das conversas o agente salva informações relevantes para personalizar futuras respostas.
memory.clear_title,Clear all memories?,¿Limpiar todas las memorias?,Limpar todas as memórias?
memory.clear_desc,This action is irreversible. Vectora won't remember anything it learned about you in previous conversations.,Esta acción es irreversible. Vectora no recordará nada de lo que aprendió sobre ti en conversaciones anteriores.,Esta ação é irreversível. O Vectora não se lembrará de nada que aprendeu sobre você nas conversas anteriores.
memory.add_title,Add memory,Añadir memoria,Adicionar memória
memory.add_desc,Create a memory manually for Vectora to use in future conversations.,Crea una memoria manualmente para que Vectora la use en futuras conversaciones.,Crie uma memória manualmente para que o Vectora a use nas próximas conversas.
memory.add_key_label,Optional label (advanced),Etiqueta opcional (avanzado),Rótulo opcional (avançado)
memory.add_key_placeholder,"e.g.: profession, preferences","ej: profesión, preferencias","ex: profissão, preferências"
memory.add_content_label,What should Vectora remember?,¿Qué debe recordar Vectora?,O que o Vectora deve lembrar?
memory.add_content_placeholder,"e.g.: I prefer concise answers; I work with TypeScript; my timezone is America/Sao_Paulo","ej: Prefiero respuestas concisas; trabajo con TypeScript; mi zona horaria es America/Sao_Paulo","ex: Prefiro respostas concisas; trabalho com TypeScript; meu fuso horário é America/Sao_Paulo"
memory.error_load,Error loading memories,Error al cargar memorias,Erro ao carregar memórias
memory.error_save,Error saving,Error al guardar,Erro ao salvar
memory.error_delete,Error deleting,Error al eliminar,Erro ao deletar
memory.error_clear,Error clearing memories,Error al limpiar memorias,Erro ao limpar memórias
memory.error_create,Error creating memory,Error al crear memoria,Erro ao criar memória
# =============================================================================
# Workspace selector + trust (Q6)
# =============================================================================
workspace.add_folder,Add folder…,Añadir carpeta…,Adicionar pasta…
workspace.no_workspaces,No folders yet,Aún no hay carpetas,Nenhuma pasta ainda
workspace.trusted,Trusted,Confiable,Confiável
workspace.untrusted,Read-only,Solo lectura,Somente leitura
workspace.select_title,Workspace,Espacio de trabajo,Workspace
workspace.trust_title,Trust this folder?,¿Confiar en esta carpeta?,Confiar nesta pasta?
workspace.trust_desc,"Vectora can only read, write and run commands inside trusted folders. Outside this folder nothing is accessible.","Vectora solo puede leer, escribir y ejecutar comandos dentro de carpetas confiables. Fuera de esta carpeta nada es accesible.","O Vectora só pode ler, escrever e rodar comandos dentro de pastas confiáveis. Fora dela nada é acessível."
workspace.browse_title,Choose a folder,Elige una carpeta,Escolha uma pasta
workspace.browse_up,Up one level,Subir un nivel,Subir um nível
workspace.browse_drives,View drives,Ver discos,Ver discos
workspace.path_placeholder,Type a path and press Enter…,Escribe una ruta y pulsa Enter…,Digite um caminho e pressione Enter…
workspace.go,Go,Ir,Ir
workspace.browse_empty,No subfolders here,No hay subcarpetas aquí,Nenhuma subpasta aqui
workspace.git_init_label,Initialize git repository if needed,Inicializar repositorio git si es necesario,Inicializar repositório git se necessário
workspace.git_not_repo,This folder is not a git repository.,Esta carpeta no es un repositorio git.,Esta pasta não é um repositório git.
workspace.trust_confirm,I trust this folder,Confío en esta carpeta,Confio nesta pasta
workspace.ingest_title,Index folder in RAG,Indexar carpeta en RAG,Indexar pasta no RAG
workspace.ingest_desc,Pick the folder you want the agent to ingest into the knowledge base.,Elige la carpeta que el agente debe indexar en la base de conocimiento.,Escolha a pasta que o agente deve indexar na base de conhecimento.
workspace.ingest_confirm,Index this folder,Indexar esta carpeta,Indexar esta pasta
workspace.tab_local,Local,Local,Local
workspace.transport.ssh,SSH,SSH,SSH
workspace.transport.codespace,Codespace,Codespace,Codespace
license.dismiss,Dismiss,Cerrar,Fechar
license.banner.unconfigured,VECTORA_TOKEN not configured. Add yours in Settings → Administration → Configuration to unlock chat.,VECTORA_TOKEN no configurado. Agrégalo en Configuración → Administración → Configuración para usar el chat.,VECTORA_TOKEN não configurado. Adicione o seu em Configurações → Administração → Configurações.
license.banner.configure,Configure,Configurar,Configurar
license.banner.expired,License expired. Renew to keep using Vectora.,Licencia vencida. Renueva para seguir usando Vectora.,Licença expirada. Renove para continuar usando o Vectora.
license.banner.renew,Renew,Renovar,Renovar
license.banner.past_due,Payment is past due. Update your billing to avoid interruption.,El pago está pendiente. Actualiza tu facturación para evitar interrupciones.,Pagamento em atraso. Regularize para evitar interrupção.
license.banner.manage,Manage,Administrar,Gerenciar
license.banner.trial_ending,Trial expires in {n} day(s). Subscribe to keep access.,La prueba vence en {n} día(s). Suscríbete para mantener el acceso.,Trial expira em {n} dia(s). Assine para manter o acesso.
license.banner.subscribe,Subscribe,Suscribirse,Assinar
update.banner.ready,New version downloaded — restart to apply.,Nueva versión descargada — reinicia para aplicar.,Nova versão baixada — reinicie para aplicar.
update.banner.ready_with_version,Vectora {v} ready — restart to apply.,Vectora {v} listo — reinicia para aplicar.,Vectora {v} pronto — reinicie para aplicar.
update.banner.restart,Restart now,Reiniciar ahora,Reiniciar agora
skills.title,Skills,Skills,Skills
skills.description,Reusable capabilities loaded by the agent (SKILL.md format).,Capacidades reutilizables cargadas por el agente (formato SKILL.md).,Capacidades reutilizáveis carregadas pelo agente (formato SKILL.md).
skills.install_label,Install from git URL or local path,Instalar desde URL git o ruta local,Instalar de URL git ou caminho local
skills.install_placeholder,https://github.com/user/skill or /path/to/skill,https://github.com/user/skill o /ruta/a/skill,https://github.com/user/skill ou /caminho/da/skill
skills.loading,Loading skills…,Cargando skills…,Carregando skills…
skills.empty,No skills installed.,Sin skills instaladas.,Nenhuma skill instalada.
skills.verify,Verify,Verificar,Verificar
skills.verify_ok,SKILL.md valid,SKILL.md válido,SKILL.md válido
skills.confirm_remove,Remove this skill?,¿Quitar esta skill?,Remover esta skill?
skills.error_load,Failed to load skills.,Error al cargar skills.,Falha ao carregar skills.
skills.error_install,Failed to install skill.,Error al instalar skill.,Falha ao instalar skill.
skills.error_verify,Failed to verify.,Error al verificar.,Falha ao verificar.
workspace.ssh_host,Host,Host,Host
workspace.ssh_path,Remote path,Ruta remota,Caminho remoto
workspace.ssh_key,SSH key,Clave SSH,Chave SSH
workspace.ssh_key_placeholder,Choose a key…,Elige una clave…,Escolha uma chave…
workspace.ssh_key_none,No key (agent),Sin clave (agente),Sem chave (agente)
workspace.ssh_test,Test connection,Probar conexión,Testar conexão
workspace.ssh_ok,Connected,Conectado,Conectado
workspace.ssh_confirm,Add SSH workspace,Agregar workspace SSH,Adicionar workspace SSH
workspace.codespaces_loading,Loading codespaces…,Cargando codespaces…,Carregando codespaces…
workspace.codespaces_unavailable,GitHub CLI not authenticated.,GitHub CLI no autenticado.,GitHub CLI não autenticado.
workspace.codespaces_empty,No codespaces found.,No se encontraron codespaces.,Nenhum codespace encontrado.
workspace.cancel,Cancel,Cancelar,Cancelar
new_chat.dialog_title,New conversation,Nueva conversación,Nova conversa
new_chat.dialog_desc,Choose which workspace this conversation will work in.,Elige en qué espacio de trabajo va a operar esta conversación.,Escolha em qual workspace esta conversa vai trabalhar.
new_chat.create_new,Create a workspace for this conversation,Crear un espacio de trabajo para esta conversación,Criar um workspace para esta conversa
new_chat.create_new_desc,A dedicated folder will be created at ~/Documents/vectora/<conversation-id>.,Se creará una carpeta dedicada en ~/Documents/vectora/<id-de-conversación>.,Uma pasta dedicada será criada em ~/Documents/vectora/<id-da-conversa>.
new_chat.existing_label,Existing workspaces,Espacios de trabajo existentes,Workspaces existentes
new_chat.cancel,Cancel,Cancelar,Cancelar
new_chat.confirm,Start conversation,Iniciar conversación,Iniciar conversa
workspace.select_here,Use this folder,Usar esta carpeta,Usar esta pasta
# =============================================================================
# Auth onboarding (Q7)
# =============================================================================
auth.setup_title,Welcome to Vectora,Bienvenido a Vectora,Bem-vindo ao Vectora
auth.setup_subtitle,Create the first account — it becomes the administrator (root).,Crea la primera cuenta — se convierte en administrador (root).,Crie a primeira conta — ela se torna o administrador (root).
auth.signin_title,Sign in,Iniciar sesión,Entrar
auth.no_public_signup,Public signup is disabled. Ask an administrator for an invite.,El registro público está deshabilitado. Pide una invitación a un administrador.,Cadastro público desabilitado. Peça um convite a um administrador.
auth.email,Email,Correo electrónico,E-mail
auth.email_ph,you@company.com,tu@empresa.com,voce@empresa.com
auth.password,Password,Contraseña,Senha
auth.show_password,Show password,Mostrar contraseña,Mostrar senha
auth.hide_password,Hide password,Ocultar contraseña,Ocultar senha
auth.email_invalid,Invalid email.,Correo inválido.,E-mail inválido.
auth.conn_error,Connection error. Check that the server is running.,Error de conexión. Verifica que el servidor esté activo.,Erro de conexão. Verifique se o servidor está rodando.
auth.signin.tagline,Sign in to your account to continue,Entra en tu cuenta para continuar,Entre na sua conta para continuar
auth.signin.password_ph,Your password,Tu contraseña,Sua senha
auth.signin.submit,Sign in,Entrar,Entrar
auth.signin.submitting,Signing in...,Entrando...,Entrando...
auth.signin.password_required,Enter your password.,Ingresa la contraseña.,Informe a senha.
auth.signin.invalid_credentials,Invalid credentials.,Credenciales inválidas.,Credenciais inválidas.
auth.signin.invalid_data,Invalid data.,Datos inválidos.,Dados inválidos.
auth.signup.invite_title,Create account,Crear cuenta,Criar conta
auth.signup.invite_role,Invite for role:,Invitación para rol:,Convite para função:
auth.signup.first_access,First access,Primer acceso,Primeiro acesso
auth.signup.root_hint,The first user created becomes {root} automatically.,El primer usuario creado se vuelve {root} automáticamente.,O primeiro usuário criado vira {root} automaticamente.
auth.signup.name,Name,Nombre,Nome
auth.signup.name_ph,How should Vectora call you?,¿Cómo debe llamarte Vectora?,Como o Vectora deve te chamar?
auth.signup.password_ph,Minimum {n} characters,Mínimo {n} caracteres,Mínimo de {n} caracteres
auth.signup.confirm,Confirm password,Confirmar contraseña,Confirmar senha
auth.signup.confirm_ph,Repeat the password,Repite la contraseña,Repita a senha
auth.signup.show_confirm,Show confirmation,Mostrar confirmación,Mostrar confirmação
auth.signup.hide_confirm,Hide confirmation,Ocultar confirmación,Ocultar confirmação
auth.signup.submit,Create account,Crear cuenta,Criar conta
auth.signup.submitting,Creating account...,Creando cuenta...,Criando conta...
auth.signup.have_account,Already have an account?,¿Ya tienes cuenta?,Já tem conta?
auth.signup.signin_link,Sign in,Entrar,Entrar
# =============================================================================
# Renovação de sessão (UX-21) — aviso de expiração do access token
# =============================================================================
auth.session.expiring_title,Your session is about to expire,Tu sesión está por expirar,Sua sessão está prestes a expirar
auth.session.expiring_desc,Renew now to avoid being signed out.,Renueva ahora para evitar que se cierre tu sesión.,Renove agora para evitar ser desconectado.
auth.session.renew_action,Renew,Renovar,Renovar
auth.session.renewed,Session renewed,Sesión renovada,Sessão renovada
auth.session.renew_failed,Could not renew the session. Please sign in again soon.,No se pudo renovar la sesión. Inicia sesión de nuevo pronto.,Não foi possível renovar a sessão. Faça login novamente em breve.
auth.signup.create_error,Error creating account.,Error al crear la cuenta.,Erro ao criar conta.
auth.signup.name_required,Enter your name.,Ingresa tu nombre.,Informe seu nome.
auth.signup.name_too_long,Name too long (max {n} characters).,Nombre muy largo (máx. {n} caracteres).,Nome muito longo (máx. {n} caracteres).
auth.signup.password_min,Password must be at least {n} characters.,La contraseña debe tener al menos {n} caracteres.,Senha deve ter no mínimo {n} caracteres.
auth.signup.passwords_mismatch,Passwords do not match.,Las contraseñas no coinciden.,As senhas não conferem.
# =============================================================================
# Invites (Q8)
# =============================================================================
invite.title,Invite user,Invitar usuario,Convidar usuário
invite.role_label,Role,Función,Função
invite.email_label,Email (optional),Email (opcional),Email (opcional)
invite.ttl_label,Valid for (hours),Válido por (horas),Válido por (horas)
invite.create,Generate invite,Generar invitación,Gerar convite
invite.copy,Copy link,Copiar enlace,Copiar link
invite.copied,Copied!,¡Copiado!,Copiado!
invite.pending,Pending invites,Invitaciones pendientes,Convites pendentes
invite.revoke,Revoke,Revocar,Revogar
invite.none,No pending invites,Sin invitaciones pendientes,Nenhum convite pendente
invite.expires,Expires,Expira,Expira
invite.context,Invite for role: {role},Invitación para función: {role},Convite para função: {role}
invite.invalid,Invalid or expired invite.,Invitación inválida o expirada.,Convite inválido ou expirado.
invite.error_create,Error generating invite,Error al generar invitación,Erro ao gerar convite

# Administração — painel próprio (P4), separado do SettingsDialog
admin.dialog_title,Administration,Administración,Administração
admin.dialog_desc,Server administration — users, tools, safe folders, system and configuration.,Administración del servidor — usuarios, herramientas, carpetas seguras, sistema y configuración.,Administração do servidor — usuários, ferramentas, pastas seguras, sistema e configuração.
admin.loading,Loading…,Cargando…,Carregando…
admin.menu_label,Administration,Administración,Administração
# =============================================================================
# Permission modes (R2)
# =============================================================================
permission.title,Permission mode,Modo de permisos,Modo de permissão
permission.mode.ask,Ask permissions,Solicitar permisos,Solicitar permissões
permission.mode.accept_edits,Accept edits,Aceptar ediciones,Aceitar edições
permission.mode.plan,Plan mode,Modo de planificación,Modo de planejamento
permission.mode.auto,Auto mode,Modo automático,Modo automático
permission.mode.bypass,Bypass permissions,Ignorar permisos,Ignorar permissões
permission.desc.ask,Confirm every destructive action,Confirmar cada acción destructiva,Confirma toda ação destrutiva
permission.desc.accept_edits,Auto-approve file writes; confirm terminal,Auto-aprueba escrituras; confirma terminal,Auto-aprova escrita de arquivos; confirma terminal
permission.desc.plan,Propose only — never run destructive tools,Solo propone — nunca ejecuta acciones destructivas,Apenas propõe — não executa ações destrutivas
permission.desc.auto,Auto-approve inside the trusted folder,Auto-aprueba dentro de la carpeta confiable,Auto-aprova dentro da pasta confiável
permission.desc.bypass,Full auto — no confirmations,Totalmente automático — sin confirmaciones,Full-auto — sem confirmações
# =============================================================================
# Reasoning effort (R4)
# =============================================================================
effort.title,Effort,Esfuerzo,Esforço
effort.low,Low,Baja,Baixa
effort.medium,Medium,Media,Média
effort.high,High,Alta,Alto
effort.max,Max,Máx,Max
effort.fast_mode,Fast mode,Modo rápido,Modo rápido
effort.fast_mode_desc,Disable reasoning for minimum latency,Desactiva el razonamiento para mínima latencia,Desliga o raciocínio para latência mínima
# =============================================================================
# Command bar (R1)
# =============================================================================
commandbar.local,Local,Local,Local
commandbar.local_tip,Running on this machine,Ejecutando en esta máquina,Executando nesta máquina
commandbar.no_branch,no branch,sin rama,sem branch
commandbar.worktree,Worktree,Worktree,Worktree
# =============================================================================
# Context meter (R5)
# =============================================================================
meter.context_window,Context window,Ventana de contexto,Janela de contexto
meter.plan_usage,Plan usage,Uso del plan,Uso do plano
meter.requests,requests,solicitudes,requisições
meter.resets_in,resets in,reinicia en,reseta em
# =============================================================================
# Plus menu (R3)
# =============================================================================
plus.add_files,Add files or photos,Añadir archivos o fotos,Adicionar arquivos ou fotos
plus.add_folder,Add folder,Añadir carpeta,Adicionar pasta
plus.ingest_folder,Index folder in RAG,Indexar carpeta en RAG,Indexar pasta no RAG
plus.ingest_prompt,"Index this folder in RAG: {path}","Indexa esta carpeta en RAG: {path}","Indexe esta pasta no RAG: {path}"
plus.slash_commands,Slash commands,Comandos de barra,Comandos de barra
plus.connectors,Connectors,Conectores,Conectores
plus.plugins,Add plugins…,Añadir plugins…,Adicionar plugins…
# =============================================================================
# Slash commands (Bloco H)
# =============================================================================
slash.title,Commands,Comandos,Comandos
slash.help,Show available commands,Mostrar comandos disponíveis,Mostrar comandos disponíveis
slash.clear,Start a new chat,Iniciar un nuevo chat,Iniciar um novo chat
slash.model,Switch the model for this chat,Cambiar el modelo de este chat,Trocar o modelo deste chat
slash.unknown,Unknown command,Comando desconocido,Comando desconhecido
slash.model_usage,"Usage: /model <name>. Available: {models}","Uso: /model <nombre>. Disponibles: {models}","Uso: /model <nome>. Disponíveis: {models}"
slash.model_changed,Model changed to {model},Modelo cambiado a {model},Modelo alterado para {model}
slash.model_not_found,Model "{name}" not found,Modelo "{name}" no encontrado,Modelo "{name}" não encontrado
slash.help_intro,Available commands:,Comandos disponibles:,Comandos disponíveis:
# =============================================================================
# Plugins (MCP) — Bloco S
# =============================================================================
plugins.title,MCP Plugins,Plugins MCP,Plugins MCP
plugins.subtitle,Connect external MCP servers; their tools become available in chat.,Conecta servidores MCP externos; sus herramientas quedan disponibles en el chat.,Conecte servidores MCP externos; as ferramentas deles ficam disponíveis no chat.
plugins.empty,No plugins configured,Sin plugins configurados,Nenhum plugin configurado
plugins.add,Add plugin,Añadir plugin,Adicionar plugin
plugins.name,Name,Nombre,Nome
plugins.transport,Transport,Transporte,Transporte
plugins.command,Command,Comando,Comando
plugins.args,"Arguments (one per line)","Argumentos (uno por línea)","Argumentos (um por linha)"
plugins.url,URL,URL,URL
plugins.save,Save,Guardar,Salvar
plugins.cancel,Cancel,Cancelar,Cancelar
plugins.remove,Remove,Eliminar,Remover
plugins.verify,Verify,Verificar,Verificar
plugins.verifying,Verifying…,Verificando…,Verificando…
plugins.verify_ok,Connected · {n} tools,Conectado · {n} herramientas,Conectado · {n} ferramentas
plugins.verify_fail,Connection failed,Falló la conexión,Falha na conexão
plugins.error_save,Error saving plugin,Error al guardar plugin,Erro ao salvar plugin
plugins.error_load,Error loading plugins,Error al cargar plugins,Erro ao carregar plugins
# =============================================================================
# Tool policy (S5)
# =============================================================================
toolpolicy.title,Tool access,Acceso a herramientas,Acesso às ferramentas
toolpolicy.subtitle,Toggle which built-in tools the agent can use on your behalf.,Activa qué herramientas integradas el agente puede usar por ti.,Liga/desliga quais ferramentas integradas o agente pode usar em seu nome.
toolpolicy.enabled,Enabled,Activada,Ativada
toolpolicy.disabled,Disabled,Desactivada,Desativada
toolpolicy.save,Save changes,Guardar cambios,Salvar alterações
toolpolicy.saved,Saved,Guardado,Salvo
toolpolicy.error_load,Error loading tools,Error al cargar herramientas,Erro ao carregar ferramentas
toolpolicy.error_save,Error saving,Error al guardar,Erro ao salvar
# =============================================================================
# Embedded terminal (Bloco T)
# =============================================================================
terminal.title,Terminal,Terminal,Terminal
terminal.toggle,Toggle terminal,Mostrar/ocultar terminal,Mostrar/ocultar terminal
terminal.new,New terminal,Nuevo terminal,Novo terminal
terminal.close,Close terminal,Cerrar terminal,Fechar terminal
terminal.tab_default,shell,shell,shell
terminal.no_workspace,No active workspace.,Sin espacio de trabajo activo.,Sem workspace ativo.
terminal.untrusted_title,Workspace not trusted,Espacio no confiable,Workspace não confiável
terminal.untrusted_hint,The terminal only opens in folders you marked as trusted.,La terminal solo abre en carpetas marcadas como confiables.,O terminal só abre em pastas marcadas como confiáveis.
terminal.no_sandbox_warning,Shell sem sandbox: tem o mesmo poder de um terminal local na pasta confiada.,Shell sin sandbox: tiene el mismo poder que un terminal local en la carpeta confiable.,Shell sem sandbox: tem o mesmo poder de um terminal local na pasta confiada.
terminal.conn_error,connection error,error de conexión,erro de conexão
terminal.ended,ended,finalizado,encerrado
# Workbench (Bloco T cont.)
workbench.toggle,Toggle workbench,Mostrar/ocultar workbench,Mostrar/ocultar workbench
workbench.close,Close,Cerrar,Fechar
workbench.tab.terminal,Terminal,Terminal,Terminal
workbench.tab.files,Files,Archivos,Arquivos
workbench.tab.diff,Diff,Diff,Diff
workbench.tab.plan,Plan,Plan,Plano
workbench.files.filter,Filter files…,Filtrar archivos…,Filtrar arquivos…
workbench.files.no_workspace,No active workspace.,Sin espacio de trabajo activo.,Sem workspace ativo.
workbench.files.binary,"Binary file ({size} bytes) — preview not shown.","Archivo binario ({size} bytes) — vista previa no disponible.","Arquivo binário ({size} bytes) — preview indisponível."
workbench.files.truncated,File truncated for preview.,Archivo truncado para vista previa.,Arquivo truncado para preview.
workbench.diff.no_workspace,No active workspace.,Sin espacio de trabajo activo.,Sem workspace ativo.
workbench.diff.not_git,This folder is not a git repository.,Esta carpeta no es un repositorio git.,Esta pasta não é um repositório git.
workbench.diff.clean,No pending changes.,Sin cambios pendientes.,Sem mudanças pendentes.
workbench.diff.summary,"{n} modified files","{n} archivos modificados","{n} arquivos modificados"
workbench.plan.empty,No plans yet — ask Vectora to draft one.,Sin planes — pídele uno a Vectora.,Sem planos — peça um ao Vectora.
workbench.plan.ask_cta,Ask Vectora for a plan,Pedir un plan a Vectora,Pedir um plano ao Vectora
workbench.plan.ask_prompt,"Crie um plano de implementação para…","Crea un plan de implementación para…","Crie um plano de implementação para…"
workbench.files.pin,Pin to top,Fijar arriba,Fixar no topo
workbench.files.unpin,Unpin,Desfijar,Desafixar
workbench.files.pinned,Pinned,Fijados,Fixados
workbench.files.new_file,New file,Nuevo archivo,Novo arquivo
workbench.files.new_folder,New folder,Nueva carpeta,Nova pasta
workbench.files.refresh,Refresh,Actualizar,Atualizar
workbench.files.delete,Delete,Eliminar,Excluir
workbench.files.add_context,Add to context,Agregar al contexto,Adicionar ao contexto
workbench.files.creating_file,File name…,Nombre del archivo…,Nome do arquivo…
workbench.files.creating_folder,Folder name…,Nombre de la carpeta…,Nome da pasta…
workbench.files.collapse,Collapse all,Colapsar todo,Recolher tudo
at.title,Workspace files,Archivos del workspace,Arquivos do workspace
workbench.diff.clean_hint,"Run ""git log"" to inspect recent commits.","Ejecuta ""git log"" para ver commits recientes.","Rode ""git log"" para inspecionar commits recentes."
workbench.diff.group_staged,Staged,Preparados,Staged
workbench.diff.group_unstaged,Modified / Untracked,Modificados / Sin seguimiento,Modificados / Não rastreados
workbench.diff.files_badge,"{n} files","{n} archivos","{n} arquivos"
workbench.tab.pending,Pending updates,Actualizaciones pendientes,Atualizações pendentes
`;

export default CSV;
