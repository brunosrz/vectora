/** Tipos de autenticação — espelham os schemas Python do Bloco C. */

export type Role = "root" | "admin" | "member" | "viewer";

export interface AuthUser {
  id: string;
  email: string;
  role: Role;
  /** Nome de exibição do usuário (UTF-8 livre, espaços permitidos). */
  name?: string;
  created_at: string;
  last_login_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
}

export interface SignupPayload {
  email: string;
  password: string;
  name?: string;
}

export interface SigninPayload {
  email: string;
  password: string;
}

export const ROLE_LABELS: Record<Role, string> = {
  root: "Root",
  admin: "Admin",
  member: "Member",
  viewer: "Viewer",
};

export const ROLE_COLORS: Record<Role, string> = {
  root: "text-yellow-400",
  admin: "text-blue-400",
  member: "text-green-400",
  viewer: "text-muted-foreground",
};
