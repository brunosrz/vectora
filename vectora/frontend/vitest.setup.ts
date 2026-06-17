/**
 * Setup global do vitest — estende `expect` com os matchers de DOM do
 * @testing-library/jest-dom (toBeInTheDocument, toBeEmptyDOMElement, etc.).
 *
 * Os matchers só são úteis em testes com `// @vitest-environment jsdom`, mas
 * importá-los aqui é inócuo nos testes em ambiente node.
 */

import "@testing-library/jest-dom/vitest";
