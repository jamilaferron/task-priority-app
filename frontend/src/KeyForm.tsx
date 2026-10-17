import { useState } from "react";

export default function KeyForm({ onSubmit }: { onSubmit: (key: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <main className="board key-form">
      <h1>Task board</h1>
      <p className="muted">Enter the API key from your server's .env file. This device will remember it.</p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim()) onSubmit(value.trim());
        }}
      >
        <input type="password" value={value} onChange={(e) => setValue(e.target.value)} placeholder="API key" autoFocus />
        <button className="btn btn-done" type="submit">
          Connect
        </button>
      </form>
    </main>
  );
}
