import { api } from "./client";
import type { JobTitle, TokenResponse, User } from "./types";

export interface RegisterPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  job_title: JobTitle;
}

/**
 * The backend uses OAuth2PasswordRequestForm, so the credentials go as a form
 * and the *email* travels in the `username` field (app/auth/routes.py).
 */
export function login(email: string, password: string): Promise<TokenResponse> {
  return api.postForm<TokenResponse>("/auth/login", { username: email, password });
}

export function register(payload: RegisterPayload): Promise<User> {
  return api.post<User>("/auth/register", payload);
}

export function getMe(): Promise<User> {
  return api.get<User>("/users/me");
}
