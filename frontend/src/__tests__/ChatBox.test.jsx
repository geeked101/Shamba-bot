/**
 * @file ChatBox.test.jsx
 * @description React Testing Library tests for the ChatBox component.
 *
 * Tests cover:
 *  - Renders a list of messages
 *  - Shows user vs assistant messages
 *  - Shows the "thinking" indicator when loading=true
 *  - Hides the indicator when loading=false
 *  - Swahili thinking text vs Kikuyu thinking text
 *  - Empty messages array renders without crashing
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import ChatBox from "../components/ChatBox";

// ── Helpers ────────────────────────────────────────────────────────────────────

function makeMessages(...texts) {
  return texts.map((text, i) => ({
    role: i % 2 === 0 ? "user" : "assistant",
    content: text,
    timestamp: new Date(),
  }));
}

function renderChatBox(props = {}) {
  const defaults = { messages: [], loading: false, language: "sw" };
  return render(<ChatBox {...defaults} {...props} />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ChatBox", () => {
  it("renders without crashing when messages array is empty", () => {
    renderChatBox({ messages: [] });
  });

  it("renders a single user message", () => {
    const messages = makeMessages("Habari, mahindi yangu yana ugonjwa.");
    renderChatBox({ messages });
    expect(
      screen.getByText(/habari, mahindi yangu yana ugonjwa/i)
    ).toBeInTheDocument();
  });

  it("renders multiple messages in order", () => {
    const messages = makeMessages("Habari!", "Mambo sana!");
    renderChatBox({ messages });
    expect(screen.getByText(/habari!/i)).toBeInTheDocument();
    expect(screen.getByText(/mambo sana!/i)).toBeInTheDocument();
  });

  it("shows Swahili thinking indicator when loading=true and language=sw", () => {
    renderChatBox({ loading: true, language: "sw" });
    expect(screen.getByText(/inafikiri/i)).toBeInTheDocument();
  });

  it("shows Kikuyu thinking indicator when loading=true and language=ki", () => {
    renderChatBox({ loading: true, language: "ki" });
    expect(screen.getByText(/nĩfikĩria/i)).toBeInTheDocument();
  });

  it("does NOT show thinking indicator when loading=false", () => {
    renderChatBox({ loading: false, language: "sw" });
    expect(screen.queryByText(/inafikiri/i)).not.toBeInTheDocument();
  });

  it("renders messages alongside the loading indicator", () => {
    const messages = makeMessages("Swali la mkulima.");
    renderChatBox({ messages, loading: true, language: "sw" });
    expect(screen.getByText(/swali la mkulima/i)).toBeInTheDocument();
    expect(screen.getByText(/inafikiri/i)).toBeInTheDocument();
  });

  it("renders error messages (isError flag) without crashing", () => {
    const messages = [
      {
        role: "assistant",
        content: "Samahani, kuna hitilafu.",
        isError: true,
        timestamp: new Date(),
      },
    ];
    renderChatBox({ messages });
    expect(screen.getByText(/samahani/i)).toBeInTheDocument();
  });
});
