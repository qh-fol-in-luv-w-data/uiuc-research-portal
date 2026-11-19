import { proxy, safeSegment } from "@/lib/server/proxy";

type Ctx = { params: Promise<{ path: string[] }> };

async function forward(request: Request, { params }: Ctx) {
  const { path } = await params;
  if (!path.every(safeSegment)) return Response.json({ error: "not_found", detail: "Not found." }, { status: 404 });
  return proxy(request, `/api/${path.map(encodeURIComponent).join("/")}`);
}

export const GET = forward;
export const POST = forward;
