import Logo from "#/components/shared/Logo";

/**
 * AuthLayout — casca centralizada das telas de autenticação (login, signup).
 *
 * Card estreito (`max-w-sm`) centrado na viewport, com logo e título padrão.
 * Fonte única do shell para login e signup ficarem idênticos.
 */

interface AuthLayoutProps {
  heading: string;
  subheading?: React.ReactNode;
  children: React.ReactNode;
}

export default function AuthLayout({
  heading,
  subheading,
  children,
}: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <Logo size="md" className="justify-center" />
          <h1 className="mt-4 text-2xl font-semibold text-foreground">
            {heading}
          </h1>
          {subheading}
        </div>
        {children}
      </div>
    </div>
  );
}
