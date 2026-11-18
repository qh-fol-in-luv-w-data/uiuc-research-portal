import { proxy } from "@/lib/server/proxy";

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(request: Request, { params }: Ctx) {
  return proxy(request, `/api/${(await params).path.join("/")}`);
}

export async function POST(request: Request, { params }: Ctx) {
  return proxy(request, `/api/${(await params).path.join("/")}`);
}
