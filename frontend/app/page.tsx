export default function Home() {
  return (
    <main style={{ display: "grid", gridTemplateColumns: "2fr 1fr", minHeight: "100vh" }}>
      <section style={{ padding: "24px", borderRight: "1px solid #ddd" }}>
        <h1>Report Pane</h1>
        <p>Generated report content will appear here.</p>
      </section>
      <aside style={{ padding: "24px" }}>
        <h2>Session / Chat</h2>
        <p>Conversation and report refinement controls.</p>
      </aside>
    </main>
  );
}
