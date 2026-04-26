import { describe, it, expect, vi, beforeEach } from "vitest";
import { ApiError } from "@/lib/api/client";

describe("ApiError", () => {
  it("has correct status code", () => {
    const err = new ApiError(404, "Not found");
    expect(err.status).toBe(404);
  });

  it("has correct message", () => {
    const err = new ApiError(500, "Server error");
    expect(err.message).toBe("Server error");
  });

  it("has name ApiError", () => {
    const err = new ApiError(400, "Bad request");
    expect(err.name).toBe("ApiError");
  });

  it("is an instance of Error", () => {
    const err = new ApiError(400, "Bad request");
    expect(err).toBeInstanceOf(Error);
  });

  it("stores data when provided", () => {
    const data = { detail: "Validation failed" };
    const err = new ApiError(422, "Validation error", data);
    expect(err.data).toEqual(data);
  });
});
