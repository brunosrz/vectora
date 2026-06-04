/**
 * Shim para `next/image` — substitui por uma tag `<img>` nativa.
 *
 * Em ambiente Vite/SPA não temos a otimização automática do Next.js,
 * mas os assets de marca do Vectora são pequenos e já vêm otimizados
 * (PNGs multi-res, SVGs vetoriais). A perda é desprezível.
 *
 * Mapeado via `resolve.alias` no `vite.config.ts`.
 */

import type { ImgHTMLAttributes } from "react";

interface NextImageProps extends Omit<
  ImgHTMLAttributes<HTMLImageElement>,
  "src" | "alt" | "width" | "height"
> {
  src: string | { src: string; width?: number; height?: number };
  alt: string;
  width?: number | string;
  height?: number | string;
  priority?: boolean;
  unoptimized?: boolean;
  fill?: boolean;
  quality?: number;
  placeholder?: "blur" | "empty";
  blurDataURL?: string;
  sizes?: string;
  loader?: unknown;
}

export default function Image({
  src,
  alt,
  width,
  height,
  priority,
  fill,
  quality: _quality,
  placeholder: _placeholder,
  blurDataURL: _blurDataURL,
  unoptimized: _unoptimized,
  loader: _loader,
  sizes,
  style,
  ...rest
}: NextImageProps) {
  const resolvedSrc = typeof src === "string" ? src : src.src;
  const fillStyle = fill
    ? {
        position: "absolute" as const,
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "cover" as const,
        ...style,
      }
    : style;
  return (
    <img
      src={resolvedSrc}
      alt={alt}
      width={fill ? undefined : width}
      height={fill ? undefined : height}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
      sizes={sizes}
      style={fillStyle}
      {...rest}
    />
  );
}
