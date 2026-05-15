import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

type ProxyContext = {
  params: Promise<{
    path?: string[];
  }>;
};

export async function GET(request: NextRequest, context: ProxyContext) {
  return proxyToBackend(request, context);
}

export async function POST(request: NextRequest, context: ProxyContext) {
  return proxyToBackend(request, context);
}

export async function DELETE(request: NextRequest, context: ProxyContext) {
  return proxyToBackend(request, context);
}

export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      Allow: "GET, POST, DELETE, OPTIONS",
    },
  });
}

async function proxyToBackend(request: NextRequest, context: ProxyContext) {
  const { path = [] } = await context.params;
  const response = await fetch(buildBackendUrl(path, request.nextUrl.search), {
    method: request.method,
    headers: forwardedHeaders(request),
    body: canHaveBody(request.method) ? await request.arrayBuffer() : undefined,
    cache: "no-store",
  });

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders(response),
  });
}

function buildBackendUrl(path: string[], search: string) {
  const normalizedPath = path.map((segment) => encodeURIComponent(segment)).join("/");
  return `${backendBaseUrl()}/${normalizedPath}${search}`;
}

function backendBaseUrl() {
  return (
    process.env.API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    DEFAULT_BACKEND_URL
  ).replace(/\/+$/, "");
}

function forwardedHeaders(request: NextRequest) {
  const headers = new Headers();
  for (const name of ["accept", "content-type", "x-admin-token"]) {
    const value = request.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }
  return headers;
}

function responseHeaders(response: Response) {
  const headers = new Headers();
  const contentType = response.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  headers.set("cache-control", "no-store");
  return headers;
}

function canHaveBody(method: string) {
  return !["GET", "HEAD"].includes(method.toUpperCase());
}
