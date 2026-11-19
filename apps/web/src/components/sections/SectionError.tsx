import { getI18n } from "@/i18n/server";

export async function SectionError({ what }: { what: string }) {
  const { t } = await getI18n();
  return (
    <div role="status" className="rounded-xl border border-line bg-surface p-6 text-muted">
      {t.errors.section(what)}{" "}
      <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-sm">make up</code> {t.errors.reload}
    </div>
  );
}
