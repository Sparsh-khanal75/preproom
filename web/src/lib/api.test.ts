import { ApiError, api } from "./api";

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(status === 204 ? null : JSON.stringify(body), { status })));
}

afterEach(() => vi.unstubAllGlobals());

it("returns parsed JSON and sends JSON bodies", async () => {
  mockFetch(200, { ok: true });
  await expect(api("/x", { method: "POST", json: { a: 1 } })).resolves.toEqual({ ok: true });
  const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]!;
  expect(url).toBe("/api/x");
  expect(init.headers["Content-Type"]).toBe("application/json");
  expect(init.body).toBe('{"a":1}');
});

it("turns FastAPI errors into readable messages", async () => {
  mockFetch(422, { detail: [{ loc: ["body", "password"], msg: "String should have at least 10 characters" }] });
  await expect(api("/auth/register")).rejects.toThrow("password: String should have at least 10 characters");
  mockFetch(422, { detail: { message: "Complete your profile first", missing: ["University"] } });
  const err = (await api("/sessions").catch((e: unknown) => e)) as ApiError;
  expect(err).toBeInstanceOf(ApiError);
  expect(err.message).toBe("Complete your profile first");
  expect(err.status).toBe(422);
});

it("handles empty 204 responses", async () => {
  mockFetch(204, null);
  await expect(api("/auth/logout", { method: "POST" })).resolves.toBeUndefined();
});
