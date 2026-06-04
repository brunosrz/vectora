/**
 * Augmentation de `react` para aceitar `<style jsx>` / `<style global>`
 * herdados de styled-jsx do Next.js. Os atributos são aceitos pelo
 * parser TSX mas inertes em runtime (sem CSS-in-JS no Vite).
 *
 * Componentes que dependem dessa estilização migrarão para classes
 * Tailwind ou CSS modules.
 */
import "react";

declare module "react" {
  interface StyleHTMLAttributes<T> {
    jsx?: boolean;
    global?: boolean;
  }
}
