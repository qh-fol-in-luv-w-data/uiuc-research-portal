import { proxy } from "@/lib/server/proxy";

export async function GET(request: Request) {
  return proxy(request, "/health");
}
