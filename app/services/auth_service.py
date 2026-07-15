import axios from "axios";
import api from "./api";

export type UserRole = "patient" | "doctor" | "admin";
export type WorkShift = "morning" | "afternoon" | "both";

export interface RegisterPayload {
  name: string;
  phone: string;
  email?: string;
  password: string;
  role?: "patient" | "doctor";
  specialty?: string;
  city?: string;
  work_shift?: WorkShift;
  work_days?: string[];
  schedule_start_date?: string;
  morning_start?: string;
  morning_end?: string;
  afternoon_start?: string;
  afternoon_end?: string;
}

export interface LoginPayload {
  phone: string;
  password: string;
}

export interface AuthUser {
  id: number;
  name: string;
  phone: string;
  email?: string | null;
  role: UserRole;
  is_active?: boolean;
  specialty?: string | null;
  city?: string | null;
  work_shift?: WorkShift | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

const ACCESS_TOKEN_KEY = "access_token";
const ROLE_KEY = "role";

function setAccessToken(token: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function removeAccessToken() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

function setRole(role: UserRole) {
  localStorage.setItem(ROLE_KEY, role);
}

export function getRole(): UserRole | null {
  const role = localStorage.getItem(ROLE_KEY);

  if (role === "patient" || role === "doctor" || role === "admin") {
    return role;
  }

  return null;
}

function removeRole() {
  localStorage.removeItem(ROLE_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getAccessToken());
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) {
    return fallback;
  }

  const detail = error.response?.data?.detail;
  const message = error.response?.data?.message;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const firstItem = detail[0];
    if (
      firstItem &&
      typeof firstItem === "object" &&
      "msg" in firstItem &&
      typeof firstItem.msg === "string" &&
      firstItem.msg.trim()
    ) {
      return firstItem.msg;
    }
  }

  if (typeof message === "string" && message.trim()) {
    return message;
  }

  if (error.response?.status === 401) {
    return "شماره موبایل یا رمز عبور اشتباه است.";
  }

  if (error.response?.status === 422) {
    return "اطلاعات واردشده صحیح نیست.";
  }

  return fallback;
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  try {
    const normalizedPayload = {
      name: payload.name.trim(),
      phone: payload.phone.trim(),
      password: payload.password.trim(),
      email: payload.email?.trim() || null,
      role: payload.role ?? "patient",

      specialty: payload.specialty?.trim() || null,
      city: payload.city?.trim() || null,
      work_shift: payload.work_shift ?? null,
      work_days: payload.work_days?.length ? payload.work_days : null,
      schedule_start_date: payload.schedule_start_date?.trim() || null,
      morning_start: payload.morning_start?.trim() || null,
      morning_end: payload.morning_end?.trim() || null,
      afternoon_start: payload.afternoon_start?.trim() || null,
      afternoon_end: payload.afternoon_end?.trim() || null,
    };

    const response = await api.post<AuthResponse>("/auth/register", normalizedPayload);
    const data = response.data;

    if (data.access_token) {
      setAccessToken(data.access_token);
    }

    if (data.user?.role) {
      setRole(data.user.role);
    }

    window.dispatchEvent(new Event("auth-change"));
    return data;
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, "خطا در ثبت‌نام"));
  }
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>("/auth/login", {
      phone: payload.phone.trim(),
      password: payload.password.trim(),
    });

    const data = response.data;

    if (data.access_token) {
      setAccessToken(data.access_token);
    }

    if (data.user?.role) {
      setRole(data.user.role);
    }

    window.dispatchEvent(new Event("auth-change"));
    return data;
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, "خطا در ورود"));
  }
}

export async function getMe(): Promise<AuthUser> {
  const response = await api.get<AuthUser>("/auth/me");
  return response.data;
}

export function logout() {
  removeAccessToken();
  removeRole();
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("token");
  window.dispatchEvent(new Event("auth-change"));
}
