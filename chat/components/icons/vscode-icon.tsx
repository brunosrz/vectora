/** Ícone oficial do VS Code (simplificado), usado no botão "Abrir no VS Code". */
export function VscodeIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M17.5 2.5L8 10.5 4 7.3 2 8.4v7.2l2 1.1 4-3.2 9.5 8 3.5-1.7V4.2L17.5 2.5z"
        fill="#1F9CF0"
        fillOpacity="0.15"
      />
      <path
        d="M17.5 2.5L8 10.5 4 7.3 2 8.4v7.2l2 1.1 4-3.2 9.5 8 3.5-1.7V4.2L17.5 2.5zM8 13.7l-3.4 2.7L3 15.6V8.4l1.6-.8L8 10.3v3.4zM18 17.6l-8.7-7.3L18 3v14.6z"
        fill="#0065A9"
      />
    </svg>
  );
}
