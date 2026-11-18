export function SectionError({ what }: { what: string }) {
  return (
    <div role="status" className="rounded-xl border border-line bg-surface p-6 text-muted">
      {what} could not be loaded because the data service did not respond. Start the API with{" "}
      <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-sm">make up</code> and reload.
    </div>
  );
}
