# <img src="public/vectora.svg" width="32" height="32"> Vectora Chat

Vectora Chat is a modern web interface for the **Vectora Agent**. It's built with Next.js and Tailwind CSS, providing a visual and intuitive way to interact with your AI assistant, browse RAG knowledge, and inspect the LangGraph topology.

## Installation

Vectora Chat should be installed on the same host where your Vectora agent is located.

```bash
pnpm install -g vectora-chat
```

## Usage

Simply run the following command. It will automatically start the Vectora agent backend (via `vectora-agent` PyPI package) and the Next.js frontend:

```bash
vectora-chat
```

By default, the chat will be available at `http://localhost:3000`.

## Key Features

- **Visual RAG**: Inspect your knowledge base collections and ingest documents with immediate feedback.
- **Live Graph**: See the orchestrator's reasoning in real-time with an interactive graph visualization.
- **Dark Mode**: Support for light and dark themes.
- **Thread History**: Easily switch between previous conversations.
- **Type Safe**: Fully typed end-to-end for better reliability.
