"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { ApiError, api, type User } from "./api";

export function useMe() {
  return useQuery<User | null>({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api<User>("/auth/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: 60_000,
  });
}

/** Redirects to /login when signed out (and optionally when the role is not allowed). */
export function useRequireUser(roles?: User["role"][]) {
  const me = useMe();
  const router = useRouter();
  useEffect(() => {
    if (me.isSuccess && !me.data) router.replace(`/login?next=${encodeURIComponent(location.pathname)}`);
    if (me.data && roles && !roles.includes(me.data.role)) router.replace("/dashboard");
  }, [me.isSuccess, me.data, roles, router]);
  return me;
}
